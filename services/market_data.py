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
        """Fetches live data or generates simulated data."""
        if symbol == "SENSEX":
            base = self.last_prices["SENSEX"]
            change = random.uniform(-10, 10)
            self.last_prices["SENSEX"] += change
            return {
                "price": round(self.last_prices["SENSEX"], 2),
                "change": round(change, 2),
                "percent_change": round((change/base)*100, 2),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        elif symbol == "NIFTY 50":
            base = self.last_prices["NIFTY 50"]
            change = random.uniform(-5, 5)
            self.last_prices["NIFTY 50"] += change
            return {
                "price": round(self.last_prices["NIFTY 50"], 2),
                "change": round(change, 2),
                "percent_change": round((change/base)*100, 2),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
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

    def get_historical_data(self, symbol="^BSESN", period="1d", interval="5m"):
        """Fetches historical data using yfinance."""
        try:
            data = yf.download(symbol, period=period, interval=interval)
            return data
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()

market_service = MarketDataService()
