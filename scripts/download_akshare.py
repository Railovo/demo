"""
Download Chinese A-share daily data using akshare and save to data/.
"""
import os
import akshare as ak

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(project_root, "data")
os.makedirs(data_dir, exist_ok=True)

codes = ["600519","000858","000001","601318"]  # common A-share examples
for code in codes:
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = prefix + code
    print(f"Downloading {symbol} ...")
    try:
        df = ak.stock_zh_a_daily(symbol=symbol)
        if df is None or df.empty:
            print(f"No data for {symbol}")
            continue
        out_path = os.path.join(data_dir, f"{symbol}.csv")
        df.to_csv(out_path, index=True)
        print(f"Saved {out_path}")
    except Exception as e:
        print(f"Failed {symbol}: {e}")
