from datetime import datetime
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramNotifier:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, text):
        if not self.token or not self.chat_id:
            print("Telegram credentials missing. Skipping notification.")
            return False
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
                )
                return response.status_code == 200
            except Exception as e:
                print(f"Telegram Error: {e}")
                return False

    async def send_signal(self, signal_data):
        emoji = "📈" if "CALL" in signal_data['type'] else "📉"
        
        reasons_bullet = "\n".join([f"• {r}" for r in signal_data.get('reasons', [])])
        
        text = (
            f"📊 *LIVE {signal_data['market']} ANALYSIS*\n\n"
            f"Market State: {signal_data.get('market_state', 'UNKNOWN')}\n\n"
            f"Signal: *{signal_data['type']}*\n\n"
            f"Option: {signal_data['symbol']}\n\n"
            f"Spot Price: {signal_data.get('spot_price', 0)}\n\n"
            f"Live Premium: {signal_data.get('live_premium', 0)}\n\n"
            f"Entry Zone: {signal_data.get('entry_min', 0)} - {signal_data.get('entry_max', 0)}\n"
            f"Stop Loss: {signal_data.get('stop_loss', 0)}\n"
            f"Target 1: {signal_data.get('target_1', 0)}\n"
            f"Target 2: {signal_data.get('target_2', 0)}\n\n"
            f"Confidence: {signal_data['confidence']}%\n\n"
            f"Trade Quality: HIGH\n\n"
            f"Reason:\n{reasons_bullet}\n\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return await self.send_message(text)

    async def send_sideways_warning(self):
        text = "⚠️ *No Safe Trade Opportunity*\nMarket is currently sideways or lacks momentum. Waiting for clear breakout."
        return await self.send_message(text)

notifier = TelegramNotifier()

