import asyncio
from services.telegram_notifier import notifier

async def test_connection():
    print("Testing Telegram Connection...")
    success = await notifier.send_message("🚀 *AI Trading Assistant connected successfully!*")
    if success:
        print("Success! Check your Telegram.")
    else:
        print("Failed. Please check your Token and Chat ID in .env")

if __name__ == "__main__":
    asyncio.run(test_connection())
