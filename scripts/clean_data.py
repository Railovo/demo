"""
简单数据下载脚本：使用 yfinance 下载示例标的并保存到 data/ 目录
"""
import os
import yfinance as yf

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(project_root, "data")
os.makedirs(data_dir, exist_ok=True)

tickers = ["SPY", "AAPL", "MSFT", "GOOG"]
start = "2015-01-01"

for t in tickers:
    print(f"Downloading {t}...")
    df = yf.download(t, start=start, progress=False, auto_adjust=True)
    if df is None or df.empty:
        print(f"No data for {t}")
        continue
    out_path = os.path.join(data_dir, f"{t}.csv")
    df.to_csv(out_path)
    print(f"Saved {out_path}")

print("Done.")
