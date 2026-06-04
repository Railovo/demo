"""
计算简单因子（60日动量）并做月度中性多空回测（等权多头前1，空头后1），保存结果。
"""
import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, 'data', 'cleaned')
OUT_DIR = os.path.join(ROOT, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

symbols = ['sh600519','sh601318','sz000858','sz000001','sz000333']
# load
dfs = {}
for s in symbols:
    fn = os.path.join(CLEAN_DIR, f"{s}.csv")
    if not os.path.exists(fn):
        print('Missing', fn)
        continue
    df = pd.read_csv(fn, parse_dates=[0], index_col=0)
    df = df.sort_index()
    dfs[s] = df

# align dates
common_index = None
for df in dfs.values():
    if common_index is None:
        common_index = df.index
    else:
        common_index = common_index.intersection(df.index)
common_index = common_index.sort_values()

for s in list(dfs.keys()):
    dfs[s] = dfs[s].reindex(common_index).ffill()

# compute momentum (60 trading days) using past returns (avoid lookahead)
momentum = pd.DataFrame(index=common_index)
for s, df in dfs.items():
    momentum[s] = df['close'].pct_change(60)

# monthly rebalance on month end
# pandas newer versions require 'ME' for month end
month_ends = momentum.resample('ME').last().index
positions = {}  # date -> {symbol: weight}
for date in month_ends:
    if date not in momentum.index:
        date = momentum.index[momentum.index.get_indexer([date], method='ffill')[0]]
    vals = momentum.loc[:date].iloc[-1]
    ranked = vals.dropna().sort_values(ascending=False)
    if len(ranked) < 2:
        continue
    top = ranked.index[0]
    bottom = ranked.index[-1]
    w = {}
    w[top] = 0.5
    w[bottom] = -0.5
    positions[date] = w

# simulate daily returns
port_ret = pd.Series(0.0, index=common_index)
current_pos = {}
pos_dates = sorted(positions.keys())
pos_iter = iter(pos_dates)
next_reb = next(pos_iter, None)
for i, date in enumerate(common_index):
    if next_reb is not None and date >= next_reb:
        current_pos = positions[next_reb]
        next_reb = next(pos_iter, None)
    # compute daily portfolio return
    daily_r = 0.0
    for s, w in current_pos.items():
        r = dfs[s].loc[date, 'daily_return'] if 'daily_return' in dfs[s].columns else np.nan
        if pd.isna(r):
            r = 0.0
        daily_r += w * r
    port_ret.loc[date] = daily_r

# cumulative
cum = (1+port_ret).cumprod()
summary = {
    'start': cum.index.min(),
    'end': cum.index.max(),
    'cumulative_return': float(cum.iloc[-1]-1),
    'annual_return': float((cum.iloc[-1]) ** (252/len(cum)) -1),
    'annual_vol': float(port_ret.std()*np.sqrt(252)),
    'sharpe': float((port_ret.mean()/port_ret.std())*np.sqrt(252)) if port_ret.std()>0 else None
}
print('Backtest summary:', summary)

cum.to_csv(os.path.join(OUT_DIR, 'simple_momentum_cum.csv'))
pd.Series(summary).to_csv(os.path.join(OUT_DIR, 'simple_momentum_summary.csv'))
print('Saved outputs to', OUT_DIR)
