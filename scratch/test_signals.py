import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.signal_engine import signal_engine

async def test_signal_generation():
    print("--- Testing Live Option Signal Engine ---")
    
    for i in range(5):
        print(f"\n--- Scanning Markets (Attempt {i+1}) ---")
        best_signal = await signal_engine.scan_markets()
        
        if best_signal:
            if best_signal.get("status") == "SIDEWAYS":
                print("[SKIP] Market is sideways. No safe trades.")
            else:
                print(f"[OK] {best_signal['market']} Signal Generated: {best_signal['type']}")
                print(f"   Option: {best_signal['symbol']}")
                print(f"   Spot: {best_signal['spot_price']}")
                print(f"   Live Premium: {best_signal['live_premium']}")
                print(f"   Confidence: {best_signal['confidence']}%")
                print(f"   Entry: {best_signal['entry_min']} - {best_signal['entry_max']}")
                print(f"   SL: {best_signal['stop_loss']} | T1: {best_signal['target_1']} | T2: {best_signal['target_2']}")
                print(f"   Reasons: {', '.join(best_signal['reasons'])}")
                break # We found a real signal
        else:
            print("[SKIP] No valid setups found (Neutral Market or Strict Filters active)")
        
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_signal_generation())
