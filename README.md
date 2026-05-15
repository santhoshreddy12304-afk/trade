# AI Trading Assistant - Indian Stock Market

A professional, AI-powered trading dashboard for Sensex and Nifty options.

## Features
- **Real-time Dashboard**: Live tracking of Sensex & Nifty.
- **AI Signal Engine**: Automated Buy/Sell signals with SL and Targets using MACD, RSI, and EMA.
- **Multi-View Interface**: Switch between Dashboard, Signals, Option Chain, and Trade History.
- **Live Option Chain**: Real-time market depth and premium tracking for NIFTY/BANKNIFTY.
- **Trade History**: Persistent logging of all trades with PnL tracking.
- **Telegram Integration**: Instant alerts to your Telegram bot.
- **Paper Trading**: Test strategies with a built-in simulation engine.
- **Premium UI**: Modern dark glassmorphism design with Lucide icons.

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- Telegram Bot Token (from @BotFather)

### 2. Installation
```bash
# Clone the repository
git clone <repo_url>
cd trader

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Fill in your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

### 4. Run the Application
```bash
uvicorn main:app --reload
```
Open `http://localhost:8000` in your browser.

## Deployment (Railway)
1. Push this code to GitHub.
2. Connect your repo to Railway.
3. Add Environment Variables in Railway settings.
4. Deployment is automatic via the provided `Procfile`.

## Disclaimer
Trading involves risk. This tool is for educational and assistant purposes only. Always verify signals before executing trades.
