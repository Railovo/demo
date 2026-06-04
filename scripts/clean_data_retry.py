"""
Retrying data download with pauses and threads disabled to avoid rate limits.
"""
import os
import time
import yfinance as yf

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(project_root, "data")
os.makedirs(data_dir, exist_ok=True)

tickers = ["SPY", "AAPL", "MSFT", "GOOG"]
start = "2015-01-01"

for t in tickers:
    print(f"Downloading {t}...")
    for attempt in range(1,4):
        try:
            df = yf.download(t, start=start, progress=False, auto_adjust=True, threads=False)
            if df is None or df.empty:
                raise ValueError("No data returned")
            out_path = os.path.join(data_dir, f"{t}.csv")
            df.to_csv(out_path)
            print(f"Saved {out_path}")
            break
        except Exception as e:
            print(f"Attempt {attempt} failed for {t}: {e}")
            if attempt < 3:
                time.sleep(5)
            else:
                print(f"Giving up on {t} after 3 attempts")
    time.sleep(2)

print("Done.")
