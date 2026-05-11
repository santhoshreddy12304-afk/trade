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
        
        return df

    async def generate_signal(self, index="SENSEX"):
        """Analyzes data and generates a trading signal."""
        # For simulation, we'll generate semi-random but logical signals
        # based on mock trend analysis
        
        current_data = await market_service.get_live_data(index)
        price = current_data["price"]
        
        # Mock logic for breakout detection
        trend = "BUY" if random.random() > 0.5 else "SELL"
        confidence = random.uniform(65, 95)
        
        if confidence < self.min_confidence:
            return None

        # Calculate logical SL and Targets
        if trend == "BUY":
            entry = price + 2
            sl = price - 50
            t1 = price + 80
            t2 = price + 150
        else:
            entry = price - 2
            sl = price + 50
            t1 = price - 80
            t2 = price - 150

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
