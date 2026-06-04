"""
Multi-factor portfolio backtest (monthly rebalance, HS300 filtered pool)
- Loads data/filtered_symbols.txt
- Uses cleaned data from data/cleaned/
- Factors: m120, m60, vol60, size; cross-sectional zscore
- Neutralizes factors by regressing on size (log market cap)
- Combined score = 0.5*m120_z + 0.3*m60_z -0.2*size_z
- Portfolio: monthly rebalance, long top 30%, short bottom 30%, equal weight within legs, dollar-neutral
- Transaction cost: commission+slippage = 0.0003 + 0.0003 (per trade); cost applied on turnover
- Outputs: outputs/multi_factor_nav.csv, outputs/multi_factor_cum.png, outputs/multi_factor_summary.csv
"""

import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, 'data', 'cleaned')
FILTER_FILE = os.path.join(ROOT, 'data', 'filtered_symbols.txt')
OUT_DIR = os.path.join(ROOT, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(FILTER_FILE):
    raise SystemExit('Filtered list not found. Run filter_pool.py')

with open(FILTER_FILE, 'r', encoding='utf-8') as fh:
    symbols = [line.strip() for line in fh if line.strip()]

# load data
print(f'Loading {len(symbols)} symbols...')
dfs = {}
for s in symbols:
    fn = os.path.join(CLEAN_DIR, f"{s}.csv")
    if not os.path.exists(fn):
        continue
    df = pd.read_csv(fn, parse_dates=[0], index_col=0).sort_index()
    dfs[s] = df

if not dfs:
    raise SystemExit('No data loaded')

# align
common_index = None
for df in dfs.values():
    common_index = df.index if common_index is None else common_index.intersection(df.index)
common_index = common_index.sort_values()
for s in list(dfs.keys()):
    dfs[s] = dfs[s].reindex(common_index).ffill()

# compute factors
print('Computing factors...')
factor_names = ['m120','m60','vol60','size']
factor_panels = {name: pd.DataFrame(index=common_index, columns=list(dfs.keys())) for name in factor_names}
for s, df in dfs.items():
    close = df['close']
    m60 = close.pct_change(60)
    m120 = close.pct_change(120)
    lr = np.log(close).diff()
    vol60 = lr.rolling(60, min_periods=30).std()
    # size: log(marketcap) if outstanding_share available
    if 'outstanding_share' in df.columns:
        size = np.log(df['outstanding_share'] * df['close'].replace(0, np.nan))
    else:
        size = np.log(df['close'])
    factor_panels['m60'][s] = m60
    factor_panels['m120'][s] = m120
    factor_panels['vol60'][s] = vol60
    factor_panels['size'][s] = size

# cross-sectional zscore and neutralization by size
from scipy.stats import zscore

print('Z-scoring and neutralizing...')
cs_z = {name: factor_panels[name].copy() for name in factor_names}
for name in factor_names:
    cs = factor_panels[name]
    # cross-sectional zscore per date
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

# neutralize momentum factors by size via cross-sectional regression per date (after cluster mean removal)
def neutralize_by_size(X, size_series):
    # X, size_series are pandas Series aligned; return residual series
    mask = X.notna() & size_series.notna()
    res = pd.Series(index=X.index, dtype=float)
    if mask.sum() < 5:
        res[:] = np.nan
        return res
    lr = LinearRegression()
    try:
        lr.fit(size_series[mask].values.reshape(-1,1), X[mask].values.reshape(-1,1))
        pred = lr.predict(size_series.values.reshape(-1,1)).flatten()
        res = X.values - pred
        return pd.Series(res, index=X.index)
    except Exception:
        return X - X.mean()

m120_neu = pd.DataFrame(index=common_index, columns=list(dfs.keys()))
m60_neu = pd.DataFrame(index=common_index, columns=list(dfs.keys()))
clusters_series = pd.Series(cluster_labels) if cluster_labels else pd.Series(dtype=int)
for date in common_index:
    size_cs = cs_z['size'].loc[date]
    m120_cs = cs_z['m120'].loc[date]
    m60_cs = cs_z['m60'].loc[date]
    # remove cluster (industry) mean first if available
    if not clusters_series.empty:
        cl = clusters_series.reindex(m120_cs.index)
        m120_cs = m120_cs - m120_cs.groupby(cl).transform('mean')
        m60_cs = m60_cs - m60_cs.groupby(cl).transform('mean')
    try:
        m120_neu.loc[date] = neutralize_by_size(m120_cs, size_cs)
        m60_neu.loc[date] = neutralize_by_size(m60_cs, size_cs)
    except Exception:
        m120_neu.loc[date] = m120_cs
        m60_neu.loc[date] = m60_cs

# final factor scores: combine zscores (using neutralized for momentum)
print('Combining factors...')
# weights
w_m120 = 0.5
w_m60 = 0.3
w_size = -0.2
combined = w_m120 * m120_neu + w_m60 * m60_neu + w_size * cs_z['size']

# backtest: monthly rebalance on last trading day of month
month_ends = pd.DatetimeIndex(pd.Series(common_index).groupby(pd.Series(common_index).dt.to_period('M')).last().values)

# positions holder
positions = pd.DataFrame(0.0, index=common_index, columns=combined.columns)
long_pct = 0.3
short_pct = 0.3
for date in month_ends:
    if date not in combined.index:
        continue
    # ensure numeric scores
    scores = pd.to_numeric(combined.loc[date], errors='coerce')
    valid = scores.dropna()
    if len(valid) < 10:
        continue
    n = len(valid)
    # top/bottom quantiles
    n_top = max(1, int(np.floor(long_pct * n)))
    n_bot = max(1, int(np.floor(short_pct * n)))
    top = valid.nlargest(n_top).index.tolist()
    bot = valid.nsmallest(n_bot).index.tolist()
    # equal weight within legs, net zero
    if n_top>0:
        w_long = 1.0 / n_top
    else:
        w_long = 0
    if n_bot>0:
        w_short = -1.0 / n_bot
    else:
        w_short = 0
    pos = pd.Series(0.0, index=combined.columns)
    pos[top] = w_long
    pos[bot] = w_short
    positions.loc[date] = pos

# forward fill positions until next rebalance
positions = positions.replace(0, np.nan).ffill().fillna(0)

# daily portfolio returns
print('Simulating portfolio...')
returns = pd.DataFrame({s: dfs[s]['daily_return'] for s in dfs.keys()})
port_ret = (positions.shift(1).fillna(0) * returns).sum(axis=1)

# transaction costs at rebalance: compute turnover and apply cost
cost_rate = 0.0006  # commission + slippage total per unit traded
prev_pos = pd.Series(0.0, index=positions.columns)
costs = pd.Series(0.0, index=positions.index)
for date in positions.index:
    new_pos = positions.loc[date]
    if date in month_ends:
        turnover = (new_pos - prev_pos).abs().sum() / 2.0
        costs.loc[date] = turnover * cost_rate
    prev_pos = new_pos

# subtract costs on rebalance days from port_ret
net_port_ret = port_ret.copy()
net_port_ret = net_port_ret - costs

nav = (1 + net_port_ret).cumprod()
nav.to_csv(os.path.join(OUT_DIR, 'multi_factor_nav.csv'))

# summary
total_return = nav.iloc[-1] - 1
annual_return = (nav.iloc[-1]) ** (252/len(nav)) - 1 if len(nav)>0 else np.nan
annual_vol = net_port_ret.std() * np.sqrt(252)
sharpe = (net_port_ret.mean() / net_port_ret.std()) * np.sqrt(252) if net_port_ret.std() > 0 else np.nan
summary = {
    'start': str(nav.index.min()),
    'end': str(nav.index.max()),
    'cumulative_return': float(total_return),
    'annual_return': float(annual_return),
    'annual_vol': float(annual_vol),
    'sharpe': float(sharpe)
}
pd.Series(summary).to_csv(os.path.join(OUT_DIR, 'multi_factor_summary.csv'))

# plot
plt.figure(figsize=(8,4))
plt.plot(nav.index, nav.values)
plt.title('Multi-factor portfolio NAV')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'multi_factor_cum.png'))
plt.close()

print('Multi-factor backtest complete. Outputs in', OUT_DIR)
