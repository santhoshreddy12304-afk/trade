import asyncio
from datetime import datetime
import pandas as pd
import yfinance as yf
from jugaad_data.nse import NSELive

class BrokerDataService:
    def __init__(self):
        self.nse = NSELive()
        # Fallback tracking
        self.last_spot_prices = {"NIFTY 50": 22000.0, "BANKNIFTY": 48000.0, "SENSEX": 74000.0}

    async def get_live_data(self, symbol):
        """Fetches live spot data."""
        symbol_map = {"SENSEX": "^BSESN", "NIFTY 50": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        yf_symbol = symbol_map.get(symbol, symbol)
        
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: yf.download(yf_symbol, period="1d", interval="1m", progress=False))
            
            if data.empty:
                return {
                    "price": self.last_spot_prices.get(symbol, 0),
                    "change": 0.0,
                    "percent_change": 0.0,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "status": "Market Closed"
                }

            latest = data.iloc[-1]
            open_price = float(data.iloc[0]['Open'].iloc[0]) if isinstance(data.iloc[0]['Open'], pd.Series) else float(data.iloc[0]['Open'])
            current_price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
            
            change = current_price - open_price
            percent_change = (change / open_price) * 100 if open_price > 0 else 0
            
            self.last_spot_prices[symbol] = current_price

            return {
                "price": round(current_price, 2),
                "change": round(change, 2),
                "percent_change": round(percent_change, 2),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "status": "Live"
            }
        except Exception as e:
            print(f"Error fetching live spot for {symbol}: {e}")
            return None

    def get_live_option_chain(self, index="NIFTY"):
        """Fetches the real live option chain from NSE using jugaad-data."""
        if index == "NIFTY 50":
            index = "NIFTY"
        
        # SENSEX is BSE, not supported by NSELive option chain easily
        if index == "SENSEX":
            return None 

        try:
            oc = self.nse.index_option_chain(index)
            if 'records' not in oc:
                return None
            return oc['records']
        except Exception as e:
            print(f"NSE Option Chain Error for {index}: {e}")
            return None

    def get_historical_data(self, symbol="NIFTY 50", period="2d", interval="5m"):
        """Fetches historical data using yfinance for indicator calculation."""
        symbol_map = {"SENSEX": "^BSESN", "NIFTY 50": "^NSEI", "BANKNIFTY": "^NSEBANK"}
        yf_symbol = symbol_map.get(symbol, symbol)
        
        try:
            data = yf.download(yf_symbol, period=period, interval=interval, progress=False)
            if data.empty:
                return pd.DataFrame()
            
            # Reset index to make 'Datetime' a column if needed
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            return data
        except Exception as e:
            print(f"Error fetching historical data for {yf_symbol}: {e}")
            return pd.DataFrame()

market_service = BrokerDataService()
