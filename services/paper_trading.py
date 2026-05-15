from models import Trade, SessionLocal
from datetime import datetime

class PaperTradingService:
    def execute_trade(self, symbol, type, price):
        db = SessionLocal()
        try:
            new_trade = Trade(
                symbol=symbol,
                type=type,
                entry_price=price,
                status="OPEN",
                timestamp=datetime.now()
            )
            db.add(new_trade)
            db.commit()
            db.refresh(new_trade)
            return new_trade
        finally:
            db.close()

    def close_trade(self, trade_id, exit_price):
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.exit_price = exit_price
                trade.status = "CLOSED"
                # Calculate PnL
                if trade.type == "BUY":
                    trade.pnl = (exit_price - trade.entry_price)
                else:
                    trade.pnl = (trade.entry_price - exit_price)
                db.commit()
                return trade
            return None
        finally:
            db.close()

    def get_open_trades(self):
        db = SessionLocal()
        try:
            return db.query(Trade).filter(Trade.status == "OPEN").all()
        finally:
            db.close()

    def get_stats(self):
        db = SessionLocal()
        try:
            total_trades = db.query(Trade).count()
            closed_trades = db.query(Trade).filter(Trade.status == "CLOSED").all()
            total_pnl = sum([t.pnl for t in closed_trades])
            return {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "open_count": db.query(Trade).filter(Trade.status == "OPEN").count()
            }
        finally:
            db.close()

paper_trader = PaperTradingService()
