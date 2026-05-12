import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.signal_engine import signal_engine

async def test_signal_generation():
    print("--- Testing Signal Generation ---")
    
    for i in range(5):
        print(f"\n--- Attempt {i+1} ---")
        print("Testing SENSEX...")
        signal_sensex = await signal_engine.generate_signal("SENSEX")
        if signal_sensex:
            print(f"[OK] SENSEX Signal Generated: {signal_sensex['type']} @ {signal_sensex['entry_price']}")
            print(f"   Confidence: {signal_sensex['confidence']}%")
            print(f"   SL: {signal_sensex['stop_loss']} | T1: {signal_sensex['target_1']} | T2: {signal_sensex['target_2']}")
        else:
            print("[SKIP] No SENSEX Signal generated (Neutral Market)")

        print("Testing NIFTY 50...")
        signal_nifty = await signal_engine.generate_signal("NIFTY 50")
        if signal_nifty:
            print(f"[OK] NIFTY Signal Generated: {signal_nifty['type']} @ {signal_nifty['entry_price']}")
            print(f"   Confidence: {signal_nifty['confidence']}%")
            print(f"   SL: {signal_nifty['stop_loss']} | T1: {signal_nifty['target_1']} | T2: {signal_nifty['target_2']}")
        else:
            print("[SKIP] No NIFTY Signal generated (Neutral Market)")
        
        if signal_sensex or signal_nifty:
            break
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_signal_generation())
