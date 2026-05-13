import random
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import asyncio
import json
import os
from datetime import datetime
from database import get_db
from models import init_db, Signal, Trade
from services.market_data import market_service
from services.signal_engine import signal_engine
from services.telegram_notifier import notifier
from services.paper_trading import paper_trader

from contextlib import asynccontextmanager

active_connections = set()

# Background task for Telegram signals
async def signal_bot_task():
    print("Background Signal Bot Started...")
    while True:
        try:
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
                # Always send a heartbeat if no signal found
                await notifier.send_message("🔍 *Bot Active*: Scanning NIFTY & BANKNIFTY...\nNo high-probability setups found right now.")
            
            # Check market every 5 minutes (300 seconds)
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Error in background signal bot: {e}")
            await notifier.send_message(f"⚠️ *Bot Error*: {str(e)[:50]}... Retrying in 60s.")
            await asyncio.sleep(60) # Wait a bit before retrying if error

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
    trade = paper_trader.execute_trade(data['symbol'], data['type'], data['price'])
    return trade

@app.get("/api/trades/open")
async def get_open_trades():
    return paper_trader.get_open_trades()

@app.post("/api/trade/close")
async def close_trade(data: dict):
    trade = paper_trader.close_trade(data['trade_id'], data['exit_price'])
    return trade

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

