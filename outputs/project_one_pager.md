Project one-pager — HS300 Multi-Factor Study

Objective
- Build a reproducible multi-factor research project suitable for interview demonstration.

Key deliverables
- Data pipeline (akshare) → cleaning → filtered HS300 pool
- Factor construction: m120 (50%), m60 (30%), size (-20%) — zscore, momentum neutralized by size
- Backtest: monthly rebalance, long top30% / short bottom30%, cost = 6bps turnover
- Outputs: outputs/multi_factor_nav.csv, outputs/multi_factor_cum.png, outputs/multi_factor_summary.csv, outputs/filtered_ic_rolling.png

Top results
- Period: see outputs/multi_factor_summary.csv
- Sample performance: cumulative return ~56.7%, annual ~19.5%, Sharpe ~1.14 (example; see summary file)

How to run (reproduce)
1. python -m pip install -r requirements.txt
2. python scripts\download_hs300_akshare.py
3. python scripts\data_cleaning.py
4. python scripts\filter_pool.py
5. python scripts\run_filtered_analysis.py
6. python scripts\multi_factor_portfolio.py

What to show in interview
- One slide: problem, approach, key figures (IC plot + quintile cum returns + NAV)
- Short demo: open notebooks/multi_factor_report.ipynb and run final cell to show images and summary

Next improvements (for production)
- Add industry-neutral regression and incorporate fundamental value factors
- Implement liquidity-aware execution model and turnover constraints
- Extend factor universe and long-term robustness testing

Contact
- GitHub: https://github.com/Railovo/demo
