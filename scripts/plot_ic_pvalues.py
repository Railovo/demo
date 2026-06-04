import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'outputs')
IC_FILE = os.path.join(OUT, 'stat_significance_ic_summary.csv')
SAVE = os.path.join(OUT, 'stat_ic_pvalues.png')

if not os.path.exists(IC_FILE):
    raise SystemExit(f'Missing {IC_FILE}')

ic = pd.read_csv(IC_FILE, index_col=0)
# look for p-value columns
pcols = [c for c in ic.columns if 'pvalue' in c.lower() or 'p_value' in c.lower() or 'pval' in c.lower()]
if not pcols:
    raise SystemExit('No p-value columns found.')
# prefer bootstrap then ttest
boot_col = None
tt_col = None
for c in pcols:
    if 'boot' in c.lower() or 'bootstrap' in c.lower():
        boot_col = c
    if 't' in c.lower() or 'ttest' in c.lower():
        tt_col = c
if boot_col is None:
    boot_col = pcols[0]
if tt_col is None and len(pcols) > 1:
    tt_col = pcols[1]

# transform p-values to -log10 scale for plotting stability
def safe_neglog(p):
    p = np.array(p, dtype=float)
    p[p <= 0] = 1e-300
    return -np.log10(p)

factors = ic.index.tolist()
plt.figure(figsize=(10, 4))
if tt_col is not None:
    plt.subplot(1,2,1)
    vals = safe_neglog(ic[tt_col].fillna(1.0))
    sns.barplot(x=vals, y=factors, palette='viridis')
    plt.xlabel('-log10 t-test p-value')
    plt.tight_layout()

plt.subplot(1,2,2)
vals2 = safe_neglog(ic[boot_col].fillna(1.0))
sns.barplot(x=vals2, y=factors, palette='rocket')
plt.xlabel('-log10 bootstrap p-value')
plt.tight_layout()

plt.suptitle('IC significance (higher = more significant)')
plt.savefig(SAVE, dpi=200, bbox_inches='tight')
print('Wrote', SAVE)
