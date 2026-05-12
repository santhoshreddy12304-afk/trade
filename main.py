import random
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import asyncio
import json
import os
from database import get_db
from models import init_db, Signal, Trade
from services.market_data import market_service
from services.signal_engine import signal_engine
from services.telegram_notifier import notifier
from services.paper_trading import paper_trader

from contextlib import asynccontextmanager

# Background task for Telegram signals
async def signal_bot_task():
    print("Background Signal Bot Started...")
    while True:
        try:
            for symbol in ["SENSEX", "NIFTY 50"]:
                signal = await signal_engine.generate_signal(symbol)
                if signal:
                    # Save to DB
                    db = next(get_db())
                    new_signal = Signal(**signal)
                    db.add(new_signal)
                    db.commit()
                    
                    print(f"BOT Generated Signal: {signal['type']} {signal['symbol']} @ {signal['entry_price']}")
                    await notifier.send_signal(signal)
            
            # Check market every 5 minutes (300 seconds)
            await asyncio.sleep(300)
        except Exception as e:
            print(f"Error in background signal bot: {e}")
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

    return templates.TemplateResponse("index.html", {"request": request})

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

@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    await websocket.accept()
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

