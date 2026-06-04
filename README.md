量化项目模板（多因子/中频）

说明：
- 运行 scripts\setup_env.ps1 创建 .venv 并安装依赖
- 使用 scripts\download_akshare.py 下载国内 A 股数据到 data/ 下；如需美股示例，可使用 scripts\generate_synthetic_data.py 生成合成样本（避免 yfinance 限流）
- 首次提交已创建，本地仓库在此目录

下一步：执行第1周任务：运行 setup_env 并下载数据，然后打开 notebooks/clean_data.ipynb 或 scripts/clean_data.py 开始数据清洗。