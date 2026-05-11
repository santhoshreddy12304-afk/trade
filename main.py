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

app = FastAPI(title="AI Trading Assistant")

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

# Initialize Database
@app.on_event("startup")
async def startup_event():
    init_db()

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
            
            # Occasionally generate a signal for the demo
            if random.random() > 0.98:
                signal = await signal_engine.generate_signal("SENSEX")
                if signal:
                    # Save to DB
                    db = next(get_db())
                    new_signal = Signal(**signal)
                    db.add(new_signal)
                    db.commit()
                    # Notify Telegram
                    await notifier.send_signal(signal)
                    # Send signal over websocket
                    await websocket.send_text(json.dumps({"type": "SIGNAL", "data": signal}))

            await websocket.send_text(json.dumps({
                "type": "MARKET_UPDATE",
                "data": {"SENSEX": sensex, "NIFTY": nifty}
            }))
            await asyncio.sleep(2) # Update every 2 seconds
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
    except Exception as e:
        print(f"WebSocket Error: {e}")

