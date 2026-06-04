"""
Script: scripts/visualize_stat_significance.py
Loads:
 - outputs/stat_significance_ic_summary.csv
 - outputs/stat_significance_backtest_summary.csv
 - outputs/multi_factor_nav.csv
Produces:
 - outputs/stat_ic_pvalues.png
 - outputs/backtest_sharpe_bootstrap.png

Saves PNGs at dpi=200.
"""
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style='whitegrid')

CAND_PVAL_BOOT = ['bootstrap_pvalue','bootstrap_pval','bootstrap_p','p_bootstrap','pvalue_bootstrap','p_value_bootstrap','boot_pvalue','boot_p']
CAND_PVAL_TT = ['ttest_pvalue','ttest_pval','ttest_p','p_ttest','pvalue_ttest','p_value_ttest','t_pvalue','t_p']
CAND_FACTOR = ['factor','name','factor_name']
CAND_NAV = ['nav','NAV','value','Value','portfolio','Portfolio']
CAND_BOOTSTRAP_SHARPE = ['bootstrap_sharpe','sharpe_bootstrap','boot_sharpe','bootstrap_sharpes','bootstrap_sharpes','bootstrap_stat']


def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    # try lower-cased match
    cols_lower = {col.lower(): col for col in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def plot_ic_pvalues(ic_csv, out_png):
    df = pd.read_csv(ic_csv)
    factor_col = find_col(df, CAND_FACTOR) or df.columns[0]
    boot_col = find_col(df, CAND_PVAL_BOOT)
    tt_col = find_col(df, CAND_PVAL_TT)

    # Build tidy dataframe for plotting
    records = []
    for idx, row in df.iterrows():
        factor = row.get(factor_col)
        if pd.isnull(factor):
            continue
        if boot_col and not pd.isnull(row.get(boot_col)):
            records.append({'factor': factor, 'test': 'bootstrap_pvalue', 'pvalue': row.get(boot_col)})
        if tt_col and not pd.isnull(row.get(tt_col)):
            records.append({'factor': factor, 'test': 'ttest_pvalue', 'pvalue': row.get(tt_col)})

    if not records:
        raise ValueError(f'No p-value columns found in {ic_csv}. Expected one of: {CAND_PVAL_BOOT} or {CAND_PVAL_TT}')

    plot_df = pd.DataFrame(records)

    plt.figure(figsize=(max(6, len(plot_df['factor'].unique())*0.5), 6))
    ax = sns.barplot(data=plot_df, x='factor', y='pvalue', hue='test')
    ax.axhline(0.05, color='red', linestyle='--', label='0.05')
    ax.set_xlabel('Factor')
    ax.set_ylabel('p-value')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_backtest_sharpe(backtest_csv, nav_csv, out_png):
    df = pd.read_csv(backtest_csv)
    # try to find bootstrap sharpe column
    boot_col = find_col(df, CAND_BOOTSTRAP_SHARPE)
    if boot_col is None:
        # fall back: pick the first numeric column
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            raise ValueError(f'No numeric columns found in {backtest_csv} to use as bootstrap sharpe distribution')
        boot_col = numeric_cols[0]

    boot = df[boot_col].dropna().astype(float)

    # load nav and compute observed Sharpe from returns
    nav_path = nav_csv
    if not os.path.exists(nav_path):
        raise FileNotFoundError(f'{nav_path} not found')
    nav_df = pd.read_csv(nav_path)

    nav_col = find_col(nav_df, CAND_NAV)
    if nav_col is None:
        # attempt to find first numeric column
        numcols = nav_df.select_dtypes(include=[np.number]).columns.tolist()
        if not numcols:
            raise ValueError(f'No NAV or numeric column found in {nav_path}')
        nav_col = numcols[0]

    nav_series = nav_df[nav_col].astype(float)
    # compute returns
    returns = nav_series.pct_change().dropna()
    if returns.empty:
        raise ValueError('Computed returns are empty; check NAV series')

    # annualize assuming daily frequency
    observed_sharpe = returns.mean() / returns.std() * np.sqrt(252)

    ci_low, ci_high = np.percentile(boot, [2.5, 97.5])

    plt.figure(figsize=(8,6))
    sns.histplot(boot, bins=50, kde=False, color='skyblue')
    plt.axvline(observed_sharpe, color='red', linewidth=2, label=f'Observed Sharpe = {observed_sharpe:.3f}')
    plt.axvline(ci_low, color='black', linestyle='--', label=f'95% CI lower = {ci_low:.3f}')
    plt.axvline(ci_high, color='black', linestyle='--', label=f'95% CI upper = {ci_high:.3f}')
    plt.xlabel('Bootstrap Sharpe')
    plt.ylabel('Frequency')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Visualize statistical significance results')
    parser.add_argument('--ic_csv', default='outputs/stat_significance_ic_summary.csv')
    parser.add_argument('--backtest_csv', default='outputs/stat_significance_backtest_summary.csv')
    parser.add_argument('--nav_csv', default='outputs/multi_factor_nav.csv')
    parser.add_argument('--out_ic', default='outputs/stat_ic_pvalues.png')
    parser.add_argument('--out_backtest', default='outputs/backtest_sharpe_bootstrap.png')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_ic), exist_ok=True)

    try:
        plot_ic_pvalues(args.ic_csv, args.out_ic)
        print(f'Wrote {args.out_ic}')
    except Exception as e:
        print(f'Failed to plot IC p-values: {e}')

    try:
        plot_backtest_sharpe(args.backtest_csv, args.nav_csv, args.out_backtest)
        print(f'Wrote {args.out_backtest}')
    except Exception as e:
        print(f'Failed to plot backtest sharpe: {e}')

if __name__ == '__main__':
    main()
