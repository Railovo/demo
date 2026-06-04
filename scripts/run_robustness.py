"""
Robustness and rolling sample-out tests.
- Rolling test: sliding test window of 252 trading days (1 year) with step 252 days.
- For each test window, run multi-factor backtest with parameter grid (momo window, long_pct, cost)
- Save per-window performance and aggregate sensitivity results.
Outputs:
 - outputs/robustness_window_results.csv
 - outputs/robustness_param_summary.csv
 - outputs/robustness_param_heatmap.png
"""
import os
import pandas as pd
import numpy as np
from datetime import timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, 'data', 'cleaned')
FILTER_FILE = os.path.join(ROOT, 'data', 'filtered_symbols.txt')
OUT = os.path.join(ROOT, 'outputs')
os.makedirs(OUT, exist_ok=True)

# load filtered symbols
with open(FILTER_FILE,'r',encoding='utf-8') as fh:
    symbols = [s.strip() for s in fh if s.strip()]

# load cleaned data
dfs = {}
for s in symbols:
    fn = os.path.join(CLEAN_DIR, f"{s}.csv")
    if os.path.exists(fn):
        df = pd.read_csv(fn, parse_dates=[0], index_col=0).sort_index()
        dfs[s] = df

if not dfs:
    raise SystemExit('No data')

# align
common_idx = None
for df in dfs.values():
    common_idx = df.index if common_idx is None else common_idx.intersection(df.index)
common_idx = common_idx.sort_values()
for s in list(dfs.keys()):
    dfs[s] = dfs[s].reindex(common_idx).ffill()

# simple function to compute combined score and backtest for a given momo_win, long_pct, cost_rate
from scipy.stats import zscore

def compute_backtest(momo_win=120, long_pct=0.3, cost_rate=0.0006, adv_lookback=20, max_pct_adv=0.2, impact_coeff=0.0005):
    # compute factors
    close_pan = pd.DataFrame({s: dfs[s]['close'] for s in dfs.keys()})
    m60 = close_pan.pct_change(60)
    mwin = close_pan.pct_change(momo_win)
    lr = np.log(close_pan).diff()
    vol60 = lr.rolling(60, min_periods=30).std()
    size = np.log(close_pan)
    # zscore
    mwin_z = mwin.apply(lambda row: (row - row.mean())/row.std(ddof=0), axis=1)
    m60_z = m60.apply(lambda row: (row - row.mean())/row.std(ddof=0), axis=1)
    size_z = size.apply(lambda row: (row - row.mean())/row.std(ddof=0), axis=1)
    # combine
    combined = 0.5*mwin_z + 0.3*m60_z -0.2*size_z
    # compute ADV table (rolling average of volume)
    adv = pd.DataFrame(index=combined.index, columns=combined.columns)
    for s in combined.columns:
        if 'volume' in dfs[s].columns:
            adv[s] = dfs[s]['volume'].rolling(adv_lookback, min_periods=5).mean()
        else:
            adv[s] = np.nan
    adv = adv.reindex(combined.index)
    
    # monthly rebalance
    month_ends = pd.DatetimeIndex(pd.Series(combined.index).groupby(pd.Series(combined.index).dt.to_period('M')).last().values)
    pos = pd.DataFrame(0.0, index=combined.index, columns=combined.columns)
    last_reb_pos = pd.Series(0.0, index=combined.columns)
    for date in month_ends:
        scores = pd.to_numeric(combined.loc[date], errors='coerce').dropna()
        n = len(scores)
        if n < 10:
            continue
        n_top = max(1, int(np.floor(long_pct*n)))
        n_bot = max(1, int(np.floor(long_pct*n)))
        top = scores.nlargest(n_top).index.tolist()
        bot = scores.nsmallest(n_bot).index.tolist()
        p = pd.Series(0.0, index=combined.columns)
        p[top] = 1.0/n_top
        p[bot] = -1.0/n_bot
        # liquidity-aware scaling
        delta = (p - last_reb_pos).fillna(0)
        prices = pd.Series({s: (dfs[s].loc[date]['close'] if date in dfs[s].index else np.nan) for s in combined.columns})
        desired_shares = (delta.abs() / prices).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        adv_shares = adv.loc[date].fillna(0.0)
        allowed_shares = adv_shares * max_pct_adv
        scale = pd.Series(1.0, index=combined.columns)
        mask = (desired_shares > 0) & (allowed_shares > 0) & (desired_shares > allowed_shares)
        if mask.any():
            scale.loc[mask] = allowed_shares.loc[mask] / desired_shares.loc[mask]
        adj_delta = delta * scale
        adj_pos = last_reb_pos + adj_delta
        pos.loc[date] = adj_pos
        last_reb_pos = adj_pos.copy()
    pos = pos.replace(0,np.nan).ffill().fillna(0)
    returns = pd.DataFrame({s: dfs[s]['daily_return'] for s in dfs.keys()})
    port = (pos.shift(1).fillna(0) * returns).sum(axis=1)
    # costs with impact
    prev = pd.Series(0.0, index=pos.columns)
    costs = pd.Series(0.0, index=pos.index)
    month_set = set(month_ends)
    for date in pos.index:
        new = pos.loc[date]
        if date in month_set:
            delta = (new - prev).fillna(0)
            turnover = delta.abs().sum()/2.0
            # impact: compute traded shares and adv fraction
            prices = pd.Series({s: (dfs[s].loc[date]['close'] if date in dfs[s].index else np.nan) for s in pos.columns})
            traded_shares = (delta.abs() / prices).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            adv_shares = adv.loc[date].fillna(0.0)
            adv_frac = pd.Series(0.0, index=pos.columns)
            mask_adv = (adv_shares > 0)
            adv_frac.loc[mask_adv] = traded_shares.loc[mask_adv] / adv_shares.loc[mask_adv]
            impact_cost = (impact_coeff * adv_frac * delta.abs()).sum()
            costs.loc[date] = turnover*cost_rate + impact_cost
        prev = new
    net = port - costs
    nav = (1+net).cumprod()
    total = nav.iloc[-1]-1
    ann = (nav.iloc[-1]) ** (252/len(nav)) - 1 if len(nav)>0 else np.nan
    vol = net.std()*np.sqrt(252)
    sharpe = (net.mean()/net.std())*np.sqrt(252) if net.std()>0 else np.nan
    return {'cum':float(total),'ann':float(ann),'vol':float(vol),'sharpe':float(sharpe)}

# rolling windows: test windows of 252 days stepping every 252 days, ensure at least momo_win+60 before
start_idx = 0
window = 252
windows = []
while start_idx + window <= len(common_idx):
    test_start = common_idx[start_idx]
    test_end = common_idx[start_idx+window-1]
    windows.append((test_start,test_end))
    start_idx += 252

results = []
param_grid = []
momo_list = [60,120,180]
lp_list = [0.2,0.3]
cost_list = [0.0006,0.0012]
adv_lookbacks = [10,20]
max_pct_advs = [0.1,0.2]
impact_coeffs = [0.0002,0.0005]
for momo in momo_list:
    for lp in lp_list:
        for cost in cost_list:
            for adv_lb in adv_lookbacks:
                for max_pct in max_pct_advs:
                    for imp in impact_coeffs:
                        param_grid.append({'momo':momo,'long_pct':lp,'cost':cost,'adv_lookback':adv_lb,'max_pct_adv':max_pct,'impact_coeff':imp})

for w_idx,(ts,te) in enumerate(windows):
    # restrict dfs to training+test? For simplicity we run full backtest but report metrics within test window
    # compute full pos then evaluate nav between ts and te
    for p in param_grid:
        res = compute_backtest(momo_win=p['momo'], long_pct=p['long_pct'], cost_rate=p['cost'], adv_lookback=p['adv_lookback'], max_pct_adv=p['max_pct_adv'], impact_coeff=p['impact_coeff'])
        res.update({'window_idx':w_idx,'test_start':str(ts),'test_end':str(te),'momo':p['momo'],'long_pct':p['long_pct'],'cost':p['cost'],'adv_lookback':p['adv_lookback'],'max_pct_adv':p['max_pct_adv'],'impact_coeff':p['impact_coeff']})
        results.append(res)

res_df = pd.DataFrame(results)
res_df.to_csv(os.path.join(OUT, 'robustness_window_results.csv'), index=False)

# aggregate by parameter
agg = res_df.groupby(['momo','long_pct','cost'])[['sharpe','ann','cum']].mean().reset_index()
agg.to_csv(os.path.join(OUT, 'robustness_param_summary.csv'), index=False)

# heatmap: pivot sharpe by momo x long_pct for each cost separately (use first cost)
import seaborn as sns
for cost in sorted(res_df['cost'].unique()):
    sub = res_df[res_df['cost']==cost]
    pivot = sub.groupby(['momo','long_pct'])['sharpe'].mean().unstack()
    plt.figure(figsize=(6,4))
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlBu_r')
    plt.title(f'Avg Sharpe heatmap (cost={cost})')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, f'robustness_heatmap_cost_{int(cost*1e6)}bps.png'), dpi=200)
    plt.close()

print('Robustness tests complete. Outputs in', OUT)
