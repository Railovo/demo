"""
Generate synthetic OHLCV CSVs for given tickers to use for exercises when real data can't be fetched.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(project_root, "data")
os.makedirs(data_dir, exist_ok=True)

tickers = ["SPY", "AAPL", "MSFT", "GOOG"]
start = datetime(2015,1,1)
end = datetime(2025,1,1)
ndays = (end - start).days
rng = pd.date_range(start, end, freq='B')

for t in tickers:
    np.random.seed(abs(hash(t)) % (2**32))
    mu = 0.0003
    sigma = 0.01
    S0 = 100 + (abs(hash(t)) % 50)
    returns = np.random.normal(loc=mu, scale=sigma, size=len(rng))
    price = S0 * np.exp(np.cumsum(returns))
    df = pd.DataFrame(index=rng)
    df['Open'] = price * (1 + np.random.normal(0,0.002,size=len(rng)))
    df['High'] = df['Open'] * (1 + np.abs(np.random.normal(0,0.01,size=len(rng))))
    df['Low'] = df['Open'] * (1 - np.abs(np.random.normal(0,0.01,size=len(rng))))
    df['Close'] = price
    df['Adj Close'] = df['Close']
    df['Volume'] = (np.random.randint(1_000_000,5_000_000,size=len(rng)))
    out_path = os.path.join(data_dir, f"{t}.csv")
    df.to_csv(out_path, index=True)
    print(f"Wrote synthetic {out_path}")

print('Synthetic data generation complete.')
