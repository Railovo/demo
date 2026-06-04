"""
Compute common factors across the cleaned data pool and run IC + quintile analysis.
Saves outputs to outputs/ directory: factors_ic.csv, quintile_monthly_returns.csv
"""
import os
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(ROOT, 'data', 'cleaned')
OUT_DIR = os.path.join(ROOT, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

# load cleaned files
files = [f for f in os.listdir(CLEAN_DIR) if f.endswith('.csv') and f != 'summary_stats.csv']
dfs = {}
for f in files:
    s = os.path.splitext(f)[0]
    path = os.path.join(CLEAN_DIR, f)
    try:
        df = pd.read_csv(path, parse_dates=[0], index_col=0)
        dfs[s] = df.sort_index()
    except Exception as e:
        print('Failed load', f, e)

if not dfs:
    raise SystemExit('No cleaned data found')

# align index (intersection of dates)
common_index = None
for df in dfs.values():
    if common_index is None:
        common_index = df.index
    else:
        common_index = common_index.intersection(df.index)
common_index = common_index.sort_values()

# reindex and forward-fill
for s in list(dfs.keys()):
    dfs[s] = dfs[s].reindex(common_index).ffill()

# compute factors
factors = {}
for s, df in dfs.items():
    series_close = df['close']
    # momentum
    m60 = series_close.pct_change(60)
    m120 = series_close.pct_change(120)
    # volatility: std of log returns
    lr = np.log(series_close).diff()
    vol60 = lr.rolling(window=60, min_periods=30).std()
    # size: log of market cap if available
    if 'outstanding_share' in df.columns:
        size = np.log(df['outstanding_share'] * df['close'].replace(0, np.nan))
    else:
        size = np.log(df['close'])
    factors[s] = pd.DataFrame({'m60': m60, 'm120': m120, 'vol60': vol60, 'size': size}, index=common_index)

# create factor panel
factor_names = ['m60','m120','vol60','size']
factor_panels = {name: pd.DataFrame(index=common_index, columns=list(dfs.keys())) for name in factor_names}
for s in factors:
    for name in factor_names:
        factor_panels[name][s] = factors[s][name]

# compute forward 20-day returns for each asset
fwd_horizon = 20
fwd_returns = pd.DataFrame(index=common_index, columns=list(dfs.keys()))
for s, df in dfs.items():
    fwd_returns[s] = (df['close'].shift(-fwd_horizon) / df['close'] - 1)

# compute daily Spearman IC for each factor
ic_df = pd.DataFrame(index=common_index, columns=factor_names)
for date in common_index:
    for name in factor_names:
        x = factor_panels[name].loc[date].astype(float)
        y = fwd_returns.loc[date].astype(float)
        valid = x.notna() & y.notna()
        if valid.sum() < 5:
            ic = np.nan
        else:
            ic = spearmanr(x[valid], y[valid]).correlation
        ic_df.at[date, name] = ic

ic_df.to_csv(os.path.join(OUT_DIR, 'factors_ic.csv'))
print('Wrote factors_ic.csv')

# monthly quintile analysis: rebalance monthly, compute avg forward returns per quintile
q_rets = []
# compute month-ends that are actual trading days in common_index
# group common_index by month and take the last trading date of each month
month_ends = pd.DatetimeIndex(pd.Series(common_index).groupby(pd.Series(common_index).dt.to_period('M')).last().values)
for date in month_ends:
    # assemble cross-section of factors at date
    # ensure date exists in index (it should by construction)
    try:
        factor_cs = factor_panels['m60'].loc[date]
        fwd_cs = fwd_returns.loc[date]
    except KeyError:
        # skip if date not found
        continue
    valid = factor_cs.notna() & fwd_cs.notna()
    if valid.sum() < 10:
        continue
    ranked = factor_cs[valid].rank(method='first')
    quint = pd.qcut(ranked, 5, labels=False)
    df_q = pd.DataFrame({'quint': quint, 'fwd': fwd_cs[valid].values}, index=ranked.index)
    mean_by_q = df_q.groupby('quint')['fwd'].mean()
    row = {'date': date}
    for q in range(5):
        row[f'q{q+1}'] = mean_by_q.get(q, np.nan)
    q_rets.append(row)

if not q_rets:
    # no quintile rows collected; create empty dataframe with q1..q5 columns and date index
    qret_df = pd.DataFrame(columns=[f"q{i+1}" for i in range(5)])
    qret_df.index.name = 'date'
else:
    qret_df = pd.DataFrame(q_rets).set_index('date').sort_index()
qret_df.to_csv(os.path.join(OUT_DIR, 'quintile_monthly_returns.csv'))
print('Wrote quintile_monthly_returns.csv')

# save simple IC summary
ic_summary = ic_df.rolling(window=252, min_periods=30).mean().tail(1).T
if ic_summary.shape[0] == 0:
    # no rolling IC available; write empty file with header
    pd.DataFrame(columns=['ic_rolling_mean']).to_csv(os.path.join(OUT_DIR, 'ic_rolling_mean_latest.csv'))
    print('Wrote empty ic_rolling_mean_latest.csv')
else:
    ic_summary.columns = ['ic_rolling_mean']
    ic_summary.to_csv(os.path.join(OUT_DIR, 'ic_rolling_mean_latest.csv'))
    print('Wrote ic_rolling_mean_latest.csv')
