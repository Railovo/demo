Set-StrictMode -Version Latest
$cwd = 'C:\Users\24272\Desktop\quant'
Set-Location $cwd

$steps = @(
    'python scripts\download_hs300_akshare.py',
    'python scripts\data_cleaning.py',
    'python scripts\filter_pool.py',
    'python scripts\run_filtered_analysis.py',
    'python scripts\statistical_significance.py',
    'python scripts\visualize_stat_significance.py',
    'python scripts\multi_factor_portfolio.py',
    'python scripts\run_robustness.py',
    'python scripts\generate_presentation.py'
)

foreach ($s in $steps) {
    Write-Host "Running: $s"
    try {
        & cmd /c $s
        Write-Host "Success: $s"
    } catch {
        Write-Host "Failed: $s -- $_"
    }
}

# add and commit produced outputs and notebooks (best-effort)
try {
    git add outputs notebooks scripts
    git commit -m "Run demo pipeline: regenerate outputs" -q
    git push origin main -q
    Write-Host 'Committed and pushed demo outputs.'
} catch {
    Write-Host 'Git commit/push failed or nothing to commit.'
}

Write-Host 'Demo run complete. Check outputs/ for results.'
