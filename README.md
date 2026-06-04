![IC Rolling](outputs/filtered_ic_rolling.png)
![Quintile Cumulative Returns](outputs/filtered_quintile_cum_returns.png)

旗舰项目：沪深300 多因子研究（可复现）

快速开始：
1. 克隆仓库并进入项目目录
2. 创建虚拟环境并安装依赖：
   - PowerShell: scripts\setup_env.ps1
   - 或手动： python -m venv .venv && .\.venv\Scripts\python -m pip install -r requirements.txt
3. 下载并清洗数据（示例顺序）：
   python scripts\download_hs300_akshare.py
   python scripts\data_cleaning.py
   python scripts\filter_pool.py
   python scripts\run_filtered_analysis.py

结果文件： outputs/filtered_ic_rolling.png, outputs/filtered_quintile_cum_returns.png

主要结论：
- m120（中期动量）在筛选池上展现稳定正 IC；m60 弱正；vol/size 为负。

产物：notebooks/report.ipynb（可直接展示关键图表）、outputs/one_page_conclusion.md（适合放在简历附件）。

下一步建议：加入行业中性、交易成本模型，构建多因子组合并准备项目页。