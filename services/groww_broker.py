import os
import logging
from growwapi import GrowwAPI
from dotenv import load_dotenv

load_dotenv()

class GrowwBrokerService:
    def __init__(self):
        self.api_key = os.getenv("GROWW_API_KEY")
        self.api_secret = os.getenv("GROWW_API_SECRET")
        self.mode = os.getenv("TRADING_MODE", "simulation").lower()
        self.client = None
        
        if self.api_key and self.api_secret:
            try:
                # Initialize official Groww API client
                self.client = GrowwAPI(api_key=self.api_key, api_secret=self.api_secret)
                logging.info("Groww API Client Initialized successfully.")
            except Exception as e:
                logging.error(f"Failed to initialize Groww API: {e}")
        else:
            logging.warning("Groww API credentials missing. Running in Simulation/Mock mode.")

    def place_order(self, symbol, order_type, quantity, price=None, segment="CASH"):
        """
        Places an order via Groww. If in simulation mode, it logs the intent.
        """
        if self.mode == "simulation":
            logging.info(f"SIMULATION: Placing {order_type} order for {quantity} shares of {symbol}")
            return {"status": "success", "order_id": "MOCK_ORDER_123", "message": "Simulation mode active"}

        if not self.client:
            return {"status": "error", "message": "Groww API client not initialized"}

        try:
            # Note: Exchange and segment should be derived from symbol
            response = self.client.place_order(
                exchange="NSE",
                segment=segment,
                trading_symbol=symbol,
                quantity=quantity,
                order_type="LIMIT" if price else "MARKET",
                price=price,
                transaction_type=order_type
            )
            return response
        except Exception as e:
            logging.error(f"Groww Order Error: {e}")
            return {"status": "error", "message": str(e)}

    def get_portfolio(self):
        """Fetches current holdings and positions."""
        if self.mode == "simulation" or not self.client:
            return {"holdings": [], "positions": []}
            
        try:
            holdings = self.client.get_holdings()
            positions = self.client.get_positions()
            return {"holdings": holdings, "positions": positions}
        except Exception as e:
            logging.error(f"Groww Portfolio Error: {e}")
            return {"error": str(e)}

groww_broker = GrowwBrokerService()
