"""
Run factors and IC on filtered symbol list and save outputs + plots.
"""
import os
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, 'data', 'cleaned')
FILTER_FILE = os.path.join(ROOT, 'data', 'filtered_symbols.txt')
OUT_DIR = os.path.join(ROOT, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(FILTER_FILE):
    raise SystemExit('Filtered list not found. Run filter_pool.py first.')

with open(FILTER_FILE, 'r', encoding='utf-8') as fh:
    symbols = [line.strip() for line in fh if line.strip()]

if not symbols:
    raise SystemExit('No symbols in filtered list')

# load
dfs = {}
for s in symbols:
    path = os.path.join(CLEAN_DIR, f"{s}.csv")
    if not os.path.exists(path):
        print('Missing', path)
        continue
    df = pd.read_csv(path, parse_dates=[0], index_col=0).sort_index()
    dfs[s] = df

# align
common_index = None
for df in dfs.values():
    common_index = df.index if common_index is None else common_index.intersection(df.index)
common_index = common_index.sort_values()
for s in list(dfs.keys()):
    dfs[s] = dfs[s].reindex(common_index).ffill()

# factors
factor_names = ['m60','m120','vol60','size']
factor_panels = {name: pd.DataFrame(index=common_index, columns=list(dfs.keys())) for name in factor_names}
for s, df in dfs.items():
    close = df['close']
    m60 = close.pct_change(60)
    m120 = close.pct_change(120)
    lr = np.log(close).diff()
    vol60 = lr.rolling(60, min_periods=30).std()
    size = np.log(df['close'])
    factor_panels['m60'][s] = m60
    factor_panels['m120'][s] = m120
    factor_panels['vol60'][s] = vol60
    factor_panels['size'][s] = size

# create cross-sectional zscores
cs_z = {name: factor_panels[name].copy() for name in factor_names}
for name in factor_names:
    cs = factor_panels[name]
    cs_z[name] = cs.apply(lambda row: (row - row.mean())/row.std(ddof=0), axis=1)

# industry mapping: prefer official mapping in outputs/industry_map.csv, fallback to cluster-based proxy
from sklearn.cluster import KMeans
lookback = 252
map_path = os.path.join(OUT_DIR, 'industry_map.csv')
cluster_labels = {}
# try official mapping first
if os.path.exists(map_path):
    try:
        im = pd.read_csv(map_path, dtype=str)
        if 'symbol' in im.columns and 'industry' in im.columns:
            cluster_labels = dict(zip(im['symbol'].astype(str), im['industry'].astype(str)))
            pd.Series(cluster_labels).to_csv(os.path.join(OUT_DIR, 'industry_clusters.csv'))
            print('Loaded official industry map from', map_path)
        else:
            print('industry_map.csv found but missing symbol/industry columns; will fallback to clustering')
    except Exception as e:
        print('Failed to read industry_map.csv:', e)

# fallback to KMeans clustering on recent returns
if not cluster_labels:
    if len(common_index) >= lookback:
        recent_idx = common_index[-lookback:]
    else:
        recent_idx = common_index
    # build return matrix for clustering (using daily pct change)
    ret_mat = pd.DataFrame({s: dfs[s]['close'].pct_change().loc[recent_idx] for s in dfs.keys()})
    ret_mat = ret_mat.dropna(axis=1, how='any')
    if ret_mat.shape[1] >= 10:
        corr = ret_mat.corr().fillna(0)
        X = corr.values
        n_clusters = min(12, max(2, ret_mat.shape[1] // 20))
        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(X)
        cols = corr.columns
        cluster_labels = dict(zip(cols, kmeans.labels_))
        pd.Series(cluster_labels).to_csv(os.path.join(OUT_DIR, 'industry_clusters.csv'))
    else:
        print('Skipping clustering: too few symbols for reliable clusters')

# forward returns
fwd_horizon = 20
fwd_returns = pd.DataFrame(index=common_index, columns=list(dfs.keys()))
for s, df in dfs.items():
    fwd_returns[s] = df['close'].shift(-fwd_horizon) / df['close'] - 1

# IC (with cluster neutralization)
ic_df = pd.DataFrame(index=common_index, columns=factor_names)
for date in common_index:
    for name in factor_names:
        x = cs_z[name].loc[date].astype(float)
        # cluster neutralize if available
        if cluster_labels:
            clusters = pd.Series(cluster_labels)
            cl = clusters.reindex(x.index)
            # subtract cluster means
            x = x - x.groupby(cl).transform('mean')
        y = fwd_returns.loc[date].astype(float)
        valid = x.notna() & y.notna()
        if valid.sum() < 10:
            ic = np.nan
        else:
            ic = spearmanr(x[valid], y[valid]).correlation
        ic_df.at[date, name] = ic

ic_df = pd.DataFrame(index=common_index, columns=factor_names)
for date in common_index:
    for name in factor_names:
        x = factor_panels[name].loc[date].astype(float)
        y = fwd_returns.loc[date].astype(float)
        valid = x.notna() & y.notna()
        if valid.sum() < 10:
            ic = np.nan
        else:
            ic = spearmanr(x[valid], y[valid]).correlation
        ic_df.at[date, name] = ic

ic_df.to_csv(os.path.join(OUT_DIR, 'filtered_factors_ic.csv'))

# rolling IC mean
rolling = ic_df.rolling(252, min_periods=30).mean()
rolling.to_csv(os.path.join(OUT_DIR, 'filtered_ic_rolling.csv'))

# plot rolling IC
plt.figure(figsize=(8,4))
for name in factor_names:
    plt.plot(rolling.index, rolling[name], label=name)
plt.legend()
plt.title('IC rolling mean (252 days)')
plt.xlabel('date')
plt.ylabel('IC')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'filtered_ic_rolling.png'))
plt.close()

# quintile monthly returns
month_ends = pd.DatetimeIndex(pd.Series(common_index).groupby(pd.Series(common_index).dt.to_period('M')).last().values)
q_rets = []
for date in month_ends:
    try:
        factor_cs = factor_panels['m60'].loc[date]
        fwd_cs = fwd_returns.loc[date]
    except KeyError:
        continue
    valid = factor_cs.notna() & fwd_cs.notna()
    if valid.sum() < 20:
        continue
    ranked = factor_cs[valid].rank(method='first')
    quint = pd.qcut(ranked, 5, labels=False)
    df_q = pd.DataFrame({'quint': quint, 'fwd': fwd_cs[valid].values}, index=ranked.index)
    mean_by_q = df_q.groupby('quint')['fwd'].mean()
    row = {'date': date}
    for q in range(5):
        row[f'q{q+1}'] = mean_by_q.get(q, np.nan)
    q_rets.append(row)

if q_rets:
    qret_df = pd.DataFrame(q_rets).set_index('date').sort_index()
else:
    qret_df = pd.DataFrame(columns=[f'q{i+1}' for i in range(5)])

qret_df.to_csv(os.path.join(OUT_DIR, 'filtered_quintile_monthly_returns.csv'))

# plot cumulative returns for quintiles
if not qret_df.empty:
    cum = (1 + qret_df.fillna(0)).cumprod()
    plt.figure(figsize=(8,4))
    for col in cum.columns:
        plt.plot(cum.index, cum[col], label=col)
    plt.legend()
    plt.title('Quintile cumulative monthly returns (by m60)')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'filtered_quintile_cum_returns.png'))

print('Filtered analysis complete. Outputs in', OUT_DIR)
