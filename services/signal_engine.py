import random
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
from services.market_data import market_service

import random
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
from services.market_data import market_service

class SignalEngine:
    def __init__(self):
        self.min_confidence = 65.0 # Lowered from 70
        self.max_premium = 250.0   # Increased from 100

    def calculate_indicators(self, df):
        """Calculates MACD, BB, VWAP, RSI, EMA, ATR for the dataframe."""
        if df.empty: return df
        df.columns = [col.lower() for col in df.columns]
        
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["ema_9"] = ta.ema(df["close"], length=9)
        df["ema_21"] = ta.ema(df["close"], length=21)
        df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        
        macd = ta.macd(df["close"])
        if macd is not None and not macd.empty:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 2]
        else:
            df["macd"] = 0; df["macd_signal"] = 0
            
        bb = ta.bbands(df["close"])
        if bb is not None and not bb.empty:
            df["bb_lower"] = bb.iloc[:, 0]
            df["bb_upper"] = bb.iloc[:, 2]
        else:
            df["bb_lower"] = df["close"]; df["bb_upper"] = df["close"]
        
        return df

    def find_best_option(self, oc_records, spot_price, option_type):
        """Finds nearest ATM/ITM strike under ₹100 premium."""
        if not oc_records or 'data' not in oc_records or 'expiryDates' not in oc_records:
            return None

        # 1. Real Expiry Engine - get nearest active expiry
        nearest_expiry = oc_records['expiryDates'][0] 
        
        options = []
        for item in oc_records['data']:
            if item.get('expiryDate') == nearest_expiry:
                opt_data = item.get(option_type)
                if opt_data and opt_data.get('lastPrice', 0) > 0:
                    # Ensure strike price is available in the option object
                    opt_data['strikePrice'] = item.get('strikePrice')
                    options.append(opt_data)

        if not options: return None

        # 2. Smart Strike Selection
        # Filter for premium < max_premium. Liquidity check is secondary.
        valid_options = [opt for opt in options if opt['lastPrice'] <= self.max_premium]
        
        if not valid_options: return None

        # Sort by strike distance to spot to get nearest ATM/OTM
        valid_options.sort(key=lambda x: abs(x['strikePrice'] - spot_price))
        best_option = valid_options[0]

        return {
            "strike": best_option['strikePrice'],
            "premium": best_option['lastPrice'],
            "expiry": nearest_expiry,
            "oi": best_option.get('openInterest', 0),
            "volume": best_option.get('totalTradedVolume', 0)
        }

    async def analyze_single_market(self, index):
        """Analyzes a single market and returns setup if valid."""
        # 1. Real Market Spot
        live_data = await market_service.get_live_data(index)
        if not live_data or live_data.get("status") == "Market Closed": return None
        spot_price = live_data["price"]
        
        # 2. Indicators via Historical
        df = market_service.get_historical_data(index, period="2d", interval="5m")
        df = self.calculate_indicators(df)
        if df.empty or len(df) < 21: return None
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        rsi = latest["rsi"]
        ema9 = latest["ema_9"]
        ema21 = latest["ema_21"]
        vwap = latest["vwap"]
        macd_line = latest.get("macd", 0)
        macd_signal = latest.get("macd_signal", 0)
        atr = latest.get("atr", spot_price * 0.002) # Fallback ATR
        
        # Sideways Filter - Loosened criteria
        diff = abs(ema9 - ema21)
        threshold = spot_price * 0.0003 # Reduced from 0.0005
        is_sideways = (48 < rsi < 52) and (diff < threshold)
        
        print(f"DEBUG [{index}]: Price: {spot_price}, RSI: {rsi:.2f}, EMA9: {ema9:.2f}, EMA21: {ema21:.2f}, Diff: {diff:.2f}, Threshold: {threshold:.2f}")
        print(f"DEBUG [{index}]: MACD: {macd_line:.2f}, MACD_Signal: {macd_signal:.2f}, VWAP: {vwap}")

        if is_sideways: 
            print(f"DEBUG [{index}]: Market Sideways (RSI: {rsi:.2f}, Diff: {diff:.2f} < {threshold:.2f})")
            return {"status": "SIDEWAYS"}

        trend = None
        reasons = []
        confidence = 0.0

        # Bullish Conditions - Removed VWAP dependency as it's often nan for indices
        if ema9 > ema21 and rsi > 52 and macd_line > macd_signal:
            trend = "BUY CALL"
            confidence = min(95.0, 65.0 + ((rsi - 50) * 2))
            reasons = ["EMA bullish crossover", "RSI momentum positive (>52)", "MACD bullish crossover"]
            if not np.isnan(vwap) and spot_price > vwap:
                reasons.append("Price above VWAP (Bullish)")
                confidence += 5
                
        # Bearish Conditions
        elif ema9 < ema21 and rsi < 48 and macd_line < macd_signal:
            trend = "BUY PUT"
            confidence = min(95.0, 65.0 + ((50 - rsi) * 2))
            reasons = ["EMA bearish crossover", "RSI momentum negative (<48)", "MACD bearish crossover"]
            if not np.isnan(vwap) and spot_price < vwap:
                reasons.append("Price below VWAP (Bearish)")
                confidence += 5

        if not trend:
            print(f"DEBUG [{index}]: No trend detected. RSI: {rsi:.2f}, Spot: {spot_price}, VWAP: {vwap:.2f}, MACD: {macd_line:.2f} > {macd_signal:.2f}")
            return None
            
        if confidence < self.min_confidence:
            print(f"DEBUG [{index}]: Low confidence: {confidence:.2f} < {self.min_confidence}")
            return None

        oc_records = market_service.get_live_option_chain(index)
        if not oc_records:
            print(f"DEBUG [{index}]: No option chain data received")
            return None # Skip if no option data

        option_type = "CE" if "CALL" in trend else "PE"
        best_opt = self.find_best_option(oc_records, spot_price, option_type)
        
        if not best_opt:
            print(f"DEBUG [{index}]: No suitable {option_type} option found under ₹{self.max_premium}")
            return None # No option under 100 found

        premium = best_opt['premium']
        
        # 4. Dynamic Entry Engine (ATR mapped to premium volatility)
        risk_per_lot = premium * 0.15 # 15% Stop loss
        reward_per_lot = premium * 0.30 # 30% Target 1 (1:2 RR)
        
        entry_min = max(0.5, premium - 2.0)
        entry_max = premium + 2.0
        sl = max(0.5, premium - risk_per_lot)
        t1 = premium + reward_per_lot
        t2 = premium + (reward_per_lot * 1.8)

        reasons.append(f"Premium under ₹{self.max_premium} constraint (₹{premium})")
        if best_opt['volume'] > 5000: reasons.append("High option liquidity")

        return {
            "market": index,
            "market_state": "TRENDING (BULLISH)" if "CALL" in trend else "TRENDING (BEARISH)",
            "symbol": f"{index} {best_opt['expiry']} {best_opt['strike']} {option_type}",
            "type": trend,
            "spot_price": spot_price,
            "live_premium": premium,
            "entry_min": round(entry_min, 1),
            "entry_max": round(entry_max, 1),
            "entry_price": round(premium, 1), # Legacy field
            "stop_loss": round(sl, 1),
            "target_1": round(t1, 1),
            "target_2": round(t2, 1),
            "confidence": round(confidence, 1),
            "expiry": best_opt['expiry'],
            "reasons": reasons,
            "timestamp": datetime.now()
        }

    async def scan_markets(self):
        """Scans all supported markets and returns the single highest confidence setup."""
        markets = ["NIFTY 50", "BANKNIFTY", "SENSEX"]
        valid_setups = []
        sideways_count = 0

        for market in markets:
            setup = await self.analyze_single_market(market)
            if setup:
                if setup.get("status") == "SIDEWAYS":
                    sideways_count += 1
                else:
                    valid_setups.append(setup)

        if not valid_setups:
            if sideways_count == len(markets):
                return {"status": "SIDEWAYS"}
            return None

        # Sort by confidence and return the best one
        valid_setups.sort(key=lambda x: x['confidence'], reverse=True)
        return valid_setups[0]

    # Keeping old method name for backward compatibility with tests/websocket, but mapping to scan
    async def generate_signal(self, index="NIFTY 50"):
        # For legacy compatibility, if specific index requested, just run that
        return await self.analyze_single_market(index)

signal_engine = SignalEngine()
