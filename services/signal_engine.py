import random
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
from services.market_data import market_service

class SignalEngine:
    def __init__(self):
        self.min_confidence = 70.0

    def calculate_indicators(self, df):
        """Calculates VWAP, RSI, EMA for the dataframe."""
        if df.empty:
            return df
        
        # Ensure correct column names for pandas-ta
        df.columns = [col.lower() for col in df.columns]
        
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["ema_9"] = ta.ema(df["close"], length=9)
        df["ema_21"] = ta.ema(df["close"], length=21)
        df["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
        
        # MACD
        macd = ta.macd(df["close"])
        if macd is not None and not macd.empty:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 2]
        else:
            df["macd"] = 0
            df["macd_signal"] = 0
            
        # Bollinger Bands
        bb = ta.bbands(df["close"])
        if bb is not None and not bb.empty:
            df["bb_lower"] = bb.iloc[:, 0]
            df["bb_mid"] = bb.iloc[:, 1]
            df["bb_upper"] = bb.iloc[:, 2]
        else:
            df["bb_lower"] = df["close"]
            df["bb_mid"] = df["close"]
            df["bb_upper"] = df["close"]
        
        return df

    async def generate_signal(self, index="SENSEX"):
        """Analyzes data and generates a trading signal based on technical indicators."""
        # 1. Fetch historical data
        df = market_service.get_historical_data(index, period="2d", interval="5m")
        if df.empty:
            print(f"Warning: Could not fetch historical data for {index}")
            return None
        
        # 2. Calculate indicators
        df = self.calculate_indicators(df)
        if df.empty or len(df) < 21:
            return None
            
        # Get the latest row
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = latest["close"]
        rsi = latest["rsi"]
        ema9 = latest["ema_9"]
        ema21 = latest["ema_21"]
        vwap = latest["vwap"]
        
        # 3. Advanced Strategy Logic (MACD + BB + RSI)
        trend = None
        confidence = 0.0
        
        macd_line = latest.get("macd", 0)
        macd_signal = latest.get("macd_signal", 0)
        prev_macd = prev.get("macd", 0)
        prev_macd_signal = prev.get("macd_signal", 0)
        bb_lower = latest.get("bb_lower", price)
        bb_upper = latest.get("bb_upper", price)
        
        # Bullish: MACD crossover up, Price near/below lower BB (bounce), RSI recovering > 40
        macd_cross_up = prev_macd <= prev_macd_signal and macd_line > macd_signal
        if macd_cross_up and price <= bb_lower * 1.01 and rsi > 40:
            trend = "BUY"
            confidence = min(95.0, 75.0 + (rsi / 5))
            
        # Bearish: MACD crossover down, Price near/above upper BB (rejection), RSI falling < 60
        macd_cross_down = prev_macd >= prev_macd_signal and macd_line < macd_signal
        if macd_cross_down and price >= bb_upper * 0.99 and rsi < 60:
            trend = "SELL"
            confidence = min(95.0, 75.0 + ((100 - rsi) / 5))
            
        # Optional: EMA trend continuation (if strong trend, MACD might not cross, but EMA is aligned)
        if not trend:
            if price > ema9 and ema9 > ema21 and rsi > 55 and macd_line > macd_signal:
                trend = "BUY"
                confidence = 70.0
            elif price < ema9 and ema9 < ema21 and rsi < 45 and macd_line < macd_signal:
                trend = "SELL"
                confidence = 70.0

        if not trend:
            return None

        # 4. Calculate SL and Targets
        if trend == "BUY":
            entry = price + (price * 0.0001) # Slight buffer
            sl = price - (price * 0.005)    # 0.5% SL
            t1 = price + (price * 0.008)    # 0.8% Target 1
            t2 = price + (price * 0.015)    # 1.5% Target 2
        else:
            entry = price - (price * 0.0001)
            sl = price + (price * 0.005)
            t1 = price - (price * 0.008)
            t2 = price - (price * 0.015)

        return {
            "symbol": f"{index} OPT",
            "type": trend,
            "entry_price": round(entry, 2),
            "stop_loss": round(sl, 2),
            "target_1": round(t1, 2),
            "target_2": round(t2, 2),
            "confidence": round(confidence, 1),
            "expiry": "CURRENT WEEK",
            "timestamp": datetime.now()
        }

signal_engine = SignalEngine()
