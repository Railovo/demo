"""
数据清洗脚本（供你在本地运行）
- 读取 data/ 下所有 CSV
- 标准化列名（date, open, high, low, close, volume, amount）
- 解析日期、按交易日排序、设置 date 为索引
- 填充/处理缺失值、计算 daily_return 和 log_return
- 输出到 data/cleaned/{symbol}.csv，并生成 data/cleaned/summary_stats.csv

运行：
    python scripts\data_cleaning.py
"""
import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
OUT_DIR = os.path.join(DATA_DIR, 'cleaned')
os.makedirs(OUT_DIR, exist_ok=True)

def standardize_cols(df):
    # lowercase, strip
    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    # common variants
    mapping = {
        'adj close': 'adj_close', 'close': 'close', 'volume': 'volume', 'amount': 'amount',
        'open': 'open', 'high': 'high', 'low': 'low', 'date': 'date'
    }
    for k,v in mapping.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k:v})
    return df

summary_rows = []
for fname in os.listdir(DATA_DIR):
    if not fname.lower().endswith('.csv'):
        continue
    path = os.path.join(DATA_DIR, fname)
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Skipping {fname}: read error {e}")
        continue

    df = standardize_cols(df)
    # try to find date column
    date_col = None
    for c in ['date', 'trade_date', 'time']:
        if c in df.columns:
            date_col = c
            break
    if date_col is None:
        # maybe first column is an index with dates
        df.columns = [c if i>0 else 'date' for i,c in enumerate(df.columns)]
        date_col = 'date'

    # parse dates
    try:
        df[date_col] = pd.to_datetime(df[date_col])
    except Exception:
        # try removing fractional seconds
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    df = df.dropna(subset=[date_col])
    df = df.sort_values(date_col).drop_duplicates(subset=[date_col])
    df = df.set_index(date_col)

    # ensure numeric columns
    for col in ['open','high','low','close','adj_close','volume','amount']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # prefer adj_close if available
    if 'adj_close' in df.columns:
        df['close'] = df['adj_close']

    # forward/backfill small gaps, drop rows without close
    df[['open','high','low','close']] = df[['open','high','low','close']].ffill().bfill()
    df['volume'] = df['volume'].fillna(0)
    df = df.dropna(subset=['close'])

    # compute returns
    df['daily_return'] = df['close'].pct_change()
    df['log_return'] = np.log(df['close']).diff()

    symbol = os.path.splitext(fname)[0]
    out_path = os.path.join(OUT_DIR, f"{symbol}.csv")
    df.to_csv(out_path)
    print(f"Wrote cleaned {out_path}")

    summary_rows.append({
        'symbol': symbol,
        'start': df.index.min(),
        'end': df.index.max(),
        'n_rows': len(df),
        'mean_daily_return': float(df['daily_return'].mean()) if 'daily_return' in df.columns else None,
        'std_daily_return': float(df['daily_return'].std()) if 'daily_return' in df.columns else None,
    })

# write summary
summary_df = pd.DataFrame(summary_rows)
summary_path = os.path.join(OUT_DIR, 'summary_stats.csv')
summary_df.to_csv(summary_path, index=False)
print(f"Wrote summary {summary_path}")
print('Data cleaning complete.')
