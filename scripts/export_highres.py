"""
Export high-resolution plots for presentation.
Reads CSV outputs and saves PNGs at 300 DPI.
"""
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')

# 1) filtered_ic_rolling.csv -> plot
ic_csv = os.path.join(OUT, 'filtered_ic_rolling.csv')
if os.path.exists(ic_csv):
    ic = pd.read_csv(ic_csv, parse_dates=[0], index_col=0)
    plt.figure(figsize=(10,4))
    for col in ic.columns:
        plt.plot(ic.index, ic[col], label=col)
    plt.legend()
    plt.title('IC rolling mean (252 days)')
    plt.xlabel('Date')
    plt.ylabel('IC')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'highres_filtered_ic_rolling.png'), dpi=300)
    plt.close()

# 2) filtered_quintile_monthly_returns.csv -> cumulative plot
q_csv = os.path.join(OUT, 'filtered_quintile_monthly_returns.csv')
if os.path.exists(q_csv):
    q = pd.read_csv(q_csv, parse_dates=[0], index_col=0).fillna(0)
    cum = (1 + q).cumprod()
    plt.figure(figsize=(10,4))
    for col in cum.columns:
        plt.plot(cum.index, cum[col], label=col)
    plt.legend()
    plt.title('Quintile cumulative monthly returns')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'highres_filtered_quintile_cum_returns.png'), dpi=300)
    plt.close()

# 3) multi_factor_nav.csv -> NAV plot
nav_csv = os.path.join(OUT, 'multi_factor_nav.csv')
if os.path.exists(nav_csv):
    nav = pd.read_csv(nav_csv, parse_dates=[0], index_col=0)
    plt.figure(figsize=(10,4))
    plt.plot(nav.index, nav.iloc[:,0])
    plt.title('Multi-factor portfolio NAV')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, 'highres_multi_factor_cum.png'), dpi=300)
    plt.close()

print('High-res exports saved in outputs/')
