import random
import time
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

class MarketDataService:
    def __init__(self):
        self.mode = "simulation" # Default
        self.symbols = ["SENSEX", "NIFTY 50"]
        self.last_prices = {"SENSEX": 72000.0, "NIFTY 50": 22000.0}
        
    async def get_live_data(self, symbol):
        """Fetches live/latest data using yfinance."""
        symbol_map = {"SENSEX": "^BSESN", "NIFTY 50": "^NSEI"}
        yf_symbol = symbol_map.get(symbol, symbol)
        
        try:
            # Run in executor to avoid blocking the async event loop
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: yf.download(yf_symbol, period="1d", interval="1m", progress=False))
            
            if data.empty:
                # Fallback to last known price if market is closed or no data
                return {
                    "price": round(self.last_prices.get(symbol, 0), 2),
                    "change": 0.0,
                    "percent_change": 0.0,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "status": "Market Closed / No Data"
                }

            # Extract the last row safely handling MultiIndex columns
            latest = data.iloc[-1]
            open_price = float(data.iloc[0]['Open'].iloc[0]) if isinstance(data.iloc[0]['Open'], pd.Series) else float(data.iloc[0]['Open'])
            current_price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
            
            change = current_price - open_price
            percent_change = (change / open_price) * 100 if open_price > 0 else 0
            
            self.last_prices[symbol] = current_price

            return {
                "price": round(current_price, 2),
                "change": round(change, 2),
                "percent_change": round(percent_change, 2),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Error fetching live data for {yf_symbol}: {e}")
            return None

    async def get_option_chain(self, index="SENSEX"):
        """Generates a mock option chain for Sensex."""
        current_price = self.last_prices[index]
        strike_base = round(current_price / 100) * 100
        strikes = [strike_base + (i * 100) for i in range(-5, 6)]
        
        chain = []
        for strike in strikes:
            ce_price = max(5, strike_base - strike + 500) / 2
            pe_price = max(5, strike - strike_base + 500) / 2
            chain.append({
                "strike": strike,
                "ce": {
                    "price": round(ce_price + random.uniform(-2, 2), 2),
                    "oi": random.randint(10000, 50000),
                    "volume": random.randint(50000, 200000)
                },
                "pe": {
                    "price": round(pe_price + random.uniform(-2, 2), 2),
                    "oi": random.randint(10000, 50000),
                    "volume": random.randint(50000, 200000)
                }
            })
        return chain

    def get_historical_data(self, symbol="SENSEX", period="2d", interval="5m"):
        """Fetches historical data using yfinance."""
        symbol_map = {
            "SENSEX": "^BSESN",
            "NIFTY 50": "^NSEI"
        }
        yf_symbol = symbol_map.get(symbol, symbol)
        
        try:
            print(f"Fetching historical data for {symbol} ({yf_symbol})...")
            data = yf.download(yf_symbol, period=period, interval=interval, progress=False)
            if data.empty:
                print(f"Warning: No data found for {yf_symbol}")
                return pd.DataFrame()
            
            # Reset index to make 'Datetime' a column if needed, or keep it as index
            # pandas-ta usually handles index well, but let's ensure it's clean
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            return data
        except Exception as e:
            print(f"Error fetching historical data for {yf_symbol}: {e}")
            return pd.DataFrame()

market_service = MarketDataService()
