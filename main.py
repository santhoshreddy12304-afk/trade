import random
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import asyncio
import json
import os
import pytz
from datetime import datetime, time
from database import get_db
from models import init_db, Signal, Trade
from services.market_data import market_service
from services.signal_engine import signal_engine
from services.telegram_notifier import notifier
from services.paper_trading import paper_trader
from services.groww_broker import groww_broker

from contextlib import asynccontextmanager

active_connections = set()

def is_market_open():
    """Checks if the Indian stock market is open (9:15 AM - 3:30 PM IST)."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Weekends check
    if now.weekday() >= 5:
        return False, "Market is closed (Weekend)"
        
    start_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < start_time:
        return False, f"Market opens at 9:15 AM IST. Current IST: {now.strftime('%H:%M')}"
    if now > end_time:
        return False, "Market closed for today."
        
    return True, "LIVE"

# Background task for Telegram signals
async def signal_bot_task():
    print("Background Signal Bot Started...")
    while True:
        try:
            market_live, status_msg = is_market_open()
            
            if not market_live:
                print(f"BOT: {status_msg}")
                # Optional: Send heartbeat once an hour when closed
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist)
                if now.minute < 5: 
                    await notifier.send_message(f"💤 *Bot Standby*: {status_msg}\nNext live scan starts at 9:15 AM IST.")
                await asyncio.sleep(300) # Check again in 5 mins
                continue

            print(f"BOT: Scanning markets (IST {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M')})...")
            signal = await signal_engine.scan_markets()
            
            if signal:
                if signal.get("status") == "SIDEWAYS":
                    print("BOT: Market Sideways. Sending warning.")
                    await notifier.send_sideways_warning()
                else:
                    # Save to DB
                    db = next(get_db())
                    new_signal = Signal(**{k: v for k, v in signal.items() if hasattr(Signal, k)})
                    db.add(new_signal)
                    db.commit()
                    
                    print(f"BOT Generated Signal: {signal['type']} {signal['symbol']} @ {signal['live_premium']}")
                    await notifier.send_signal(signal)
                    
                    # Broadcast to websockets
                    signal_ws = dict(signal)
                    if isinstance(signal_ws.get("timestamp"), datetime):
                        signal_ws["timestamp"] = signal_ws["timestamp"].isoformat()
                    
                    for conn in list(active_connections):
                        try:
                            await conn.send_text(json.dumps({"type": "SIGNAL", "data": signal_ws}))
                        except:
                            pass
            else:
                # Still active but no high-prob setup
                await notifier.send_message("🔍 *Bot Scanning*: NIFTY, BANKNIFTY & SENSEX...\nNo high-probability setups found in the last 5 minutes.")
            
            # Continuous 5-minute cycle
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Error in background signal bot: {e}")
            await notifier.send_message(f"⚠️ *Bot Error*: {str(e)[:50]}... Retrying in 60s.")
            await asyncio.sleep(60) 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    init_db()
    task = asyncio.create_task(signal_bot_task())
    yield
    # Shutdown actions
    task.cancel()

app = FastAPI(title="AI Trading Assistant", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"request": request}
    )

@app.get("/api/signals")
async def get_signals(db: Session = Depends(get_db)):
    signals = db.query(Signal).order_by(Signal.timestamp.desc()).limit(10).all()
    return signals

@app.get("/api/market-summary")
async def get_market_summary():
    sensex = await market_service.get_live_data("SENSEX")
    nifty = await market_service.get_live_data("NIFTY 50")
    return {"SENSEX": sensex, "NIFTY": nifty}

@app.post("/api/trade/execute")
async def execute_trade(data: dict):
    mode = os.getenv("TRADING_MODE", "simulation").lower()
    
    # Always log as paper trade for internal tracking
    trade = paper_trader.execute_trade(data['symbol'], data['type'], data['price'])
    
    if mode == "live":
        qty = data.get("quantity", 1)
        broker_res = groww_broker.place_order(data['symbol'], data['type'], qty, data['price'])
        return {"trade": trade, "broker": broker_res}
        
    return trade

@app.get("/api/broker/status")
async def get_broker_status():
    return {
        "mode": os.getenv("TRADING_MODE", "simulation"),
        "connected": groww_broker.client is not None,
        "broker": "Groww"
    }

@app.get("/api/trades/open")
async def get_open_trades():
    return paper_trader.get_open_trades()

@app.post("/api/trade/close")
async def close_trade(data: dict):
    trade = paper_trader.close_trade(data['trade_id'], data['exit_price'])
    return trade

@app.get("/api/option-chain/{index}")
async def get_option_chain(index: str):
    data = market_service.get_live_option_chain(index)
    if not data:
        return {"error": "Option chain data not available for this index"}
    return data

@app.get("/api/trades/history")
async def get_trade_history(db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(Trade.timestamp.desc()).all()
    return trades

@app.get("/api/portfolio")
async def get_portfolio_summary():
    # Mix of paper trading and broker data if available
    paper_stats = paper_trader.get_stats()
    broker_data = groww_broker.get_portfolio()
    return {
        "paper": paper_stats,
        "broker": broker_data,
        "mode": os.getenv("TRADING_MODE", "simulation")
    }

@app.post("/api/force-signal")
async def force_signal():
    """Generates a test signal instantly for UI and Telegram"""
    signal = {
        "market": "NIFTY 50",
        "market_state": "TRENDING (BULLISH)",
        "symbol": "NIFTY 50 16MAY 22000 CE",
        "type": "BUY CALL",
        "spot_price": 22000,
        "live_premium": 95.5,
        "entry_min": 93.0,
        "entry_max": 97.0,
        "stop_loss": 80.0,
        "target_1": 125.0,
        "target_2": 150.0,
        "confidence": 99.0,
        "expiry": "16MAY",
        "reasons": ["Test Signal User Requested", "Instant Breakout Detected"],
        "timestamp": datetime.now()
    }
    
    # Save to DB
    db = next(get_db())
    new_signal = Signal(**{k: v for k, v in signal.items() if hasattr(Signal, k)})
    db.add(new_signal)
    db.commit()
    
    # Send to Telegram
    await notifier.send_signal(signal)
    
    # Broadcast to websocket
    signal_ws = dict(signal)
    signal_ws["timestamp"] = signal_ws["timestamp"].isoformat()
    
    for conn in list(active_connections):
        try:
            await conn.send_text(json.dumps({"type": "SIGNAL", "data": signal_ws}))
        except Exception as e:
            print(f"WS send error: {e}")
            
    return {"status": "success", "signal": signal}

@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            sensex = await market_service.get_live_data("SENSEX")
            nifty = await market_service.get_live_data("NIFTY 50")
            
            # Websocket now only pushes real live data. 
            # Signal generation is handled cleanly by the background bot task.
            # But we can query the DB for the latest signal to push to UI if needed, 
            # or just let the UI poll /api/signals.
            
            await websocket.send_text(json.dumps({
                "type": "MARKET_UPDATE",
                "data": {"SENSEX": sensex, "NIFTY": nifty}
            }))
            await asyncio.sleep(5) # Update UI every 5 seconds
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        active_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

