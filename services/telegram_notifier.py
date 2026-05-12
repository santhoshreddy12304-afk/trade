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
        emoji = "🚀" if signal_data['type'] == 'BUY' else "📉"
        text = (
            f"{emoji} *AI TRADING SIGNAL: {signal_data['symbol']}*\n\n"
            f"Type: {signal_data['type']}\n"
            f"Entry: {signal_data['entry_price']}\n"
            f"Stop Loss: {signal_data['stop_loss']}\n"
            f"Target 1: {signal_data['target_1']}\n"
            f"Target 2: {signal_data['target_2']}\n"
            f"Confidence: {signal_data['confidence']}%\n"
            f"Expiry: {signal_data['expiry']}\n\n"
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return await self.send_message(text)

notifier = TelegramNotifier()
