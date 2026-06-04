"""
Attempt to fetch official A-share industry mapping using akshare.
Tries multiple akshare functions and heuristically extracts (code -> industry) mapping.
Saves outputs/industry_map.csv with columns: symbol (sh/sz prefixed), code (6-digit), industry
"""
import os
import akshare as ak
import pandas as pd
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
os.makedirs(OUT, exist_ok=True)

candidates = [
    'stock_industry_classified_em',
    'stock_industry_name_ths',
    'stock_board_industry_cons_ths',
    'stock_board_industry_cons_em',
    'stock_industry_concept_name_ths',
    'stock_board_industry_cons_cn',
]

found = False
mapping = {}

# helper to normalize code to sh/sz symbol
def norm_code(code):
    code = str(code).strip()
    code = code.zfill(6)
    prefix = 'sh' if code.startswith('6') or code.startswith('5') else 'sz'
    return prefix + code, code

# Try to call candidate functions if present
for func_name in candidates:
    if hasattr(ak, func_name):
        func = getattr(ak, func_name)
        try:
            print('Trying', func_name)
            df = func() if func.__code__.co_argcount == 0 else func()
            if df is None:
                continue
            if isinstance(df, pd.DataFrame):
                cols = [c.lower() for c in df.columns]
                # common patterns: columns include code, 成分代码, code, 代码, 股票代码, 成分券代码
                code_col = None
                name_col = None
                for c in df.columns:
                    cl = c.lower()
                    if '成分代码' in str(c) or '代码' in cl or 'code' in cl or '股票代码' in cl:
                        code_col = c
                    if '行业' in cl or 'industry' in cl or '板块' in cl or '名称' in cl or 'name' in cl:
                        # choose likely industry column
                        if 'industry' in cl or '行业' in cl or '板块' in cl:
                            name_col = c
                # some functions list industries with constituent codes in rows; handle those
                if code_col and name_col:
                    for _, r in df.iterrows():
                        try:
                            code = r[code_col]
                            industry = r[name_col]
                            sym, code6 = norm_code(code)
                            mapping[code6] = str(industry)
                        except Exception:
                            continue
                    if mapping:
                        found = True
                        break
                # some APIs return mapping where first column is industry and second column is constituent code list
                # attempt to parse rows
                for col in df.columns:
                    s = df[col].astype(str).str.cat(sep='|')
                    # look for 6-digit codes
                    codes = re.findall(r'\d{6}', s)
                    if codes:
                        # assign industry name from other columns or index
                        for idx, row in df.iterrows():
                            line = ' '.join([str(x) for x in row.values])
                            row_codes = re.findall(r'\d{6}', line)
                            for c in row_codes:
                                mapping[c] = idx if isinstance(idx, str) else str(idx)
                        if mapping:
                            found = True
                            break
        except Exception as e:
            print('Function', func_name, 'failed:', e)
    if found:
        break

# fallback: try stock_board_industry_cons_ths with parameter by querying industry list first
# try ak.stock_board_industry_name_ths() to get industries, then for each industry call ak.stock_board_industry_cons_ths(industry)
if not found:
    if hasattr(ak, 'stock_board_industry_name_ths') and hasattr(ak, 'stock_board_industry_cons_ths'):
        try:
            names = ak.stock_board_industry_name_ths()
            if isinstance(names, pd.DataFrame):
                for _, row in names.iterrows():
                    try:
                        ind = row.values[0]
                        cons = ak.stock_board_industry_cons_ths(ind)
                        if isinstance(cons, pd.DataFrame):
                            code_col = None
                            for c in cons.columns:
                                if '代码' in str(c) or 'code' in str(c).lower():
                                    code_col = c
                            for _, r in cons.iterrows():
                                code = r[code_col] if code_col else r.iloc[0]
                                mapping[str(code).zfill(6)] = str(ind)
                    except Exception:
                        continue
            if mapping:
                found = True
        except Exception as e:
            print('Fallback industry list approach failed:', e)

# write mapping
out_path = os.path.join(OUT, 'industry_map.csv')
if mapping:
    rows = []
    for code6, ind in mapping.items():
        sym = 'sh' + code6 if code6.startswith(('6','5')) else 'sz' + code6
        rows.append({'symbol': sym, 'code': code6, 'industry': ind})
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print('Wrote', out_path)
else:
    print('No mapping found via akshare heuristics. Please provide industry mapping in outputs/industry_map.csv')
