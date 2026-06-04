多因子/中频 旗舰项目（沪深300 池）

目标：生成可展示的、可复现的多因子研究项目，用于求职作品集。

关键脚本（按顺序运行）：
- scripts/download_hs300_akshare.py  # 下载沪深300 成分日线
- scripts/data_cleaning.py           # 数据清洗，输出 data/cleaned/
- scripts/filter_pool.py             # 按历史与流动性筛选池
- scripts/run_filtered_analysis.py   # 计算因子并生成 IC、分组回测图表

结果与可视化输出： outputs/filtered_ic_rolling.png, outputs/filtered_quintile_cum_returns.png

主要发现（简短）：
- m120（中期动量）在样本池上表现出稳定正 IC；m60 弱正；vol/size 为负。

复现：在项目根目录运行（建议在 .venv 中）：
    python -m pip install -r requirements.txt
    python scripts/download_hs300_akshare.py
    python scripts/data_cleaning.py
    python scripts/filter_pool.py
    python scripts/run_filtered_analysis.py

下一步建议：加入行业中性化、交易成本模拟、多因子回测，并整理 1 页结论用于简历附注。
