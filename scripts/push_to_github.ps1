# Push helper for Windows PowerShell (does NOT store PAT)
param(
    [string]$RemoteUrl = 'https://github.com/Railovo/demo.git'
)

# Move to project root (assumes script in scripts/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location (Join-Path $scriptDir '..')

Write-Host "Working directory: $(Get-Location)"

# check git
try { git --version > $null 2>&1 } catch { Write-Host 'git not found. Install Git and retry.'; exit 1 }

Write-Host 'Configuring credential helper (manager-core)...'
git config --global credential.helper manager-core

# add remote if missing
$existing = & git remote
if ($existing -notcontains 'origin') {
    Write-Host "Adding remote origin -> $RemoteUrl"
    git remote add origin $RemoteUrl
} else {
    Write-Host "Remote 'origin' already exists. If you want to change it, run: git remote set-url origin <url>"
}

# set main branch
git branch -M main

Write-Host 'Pushing to origin main (you will be prompted for credentials if needed)...'
# This will prompt for username and password (use PAT as password for HTTPS)
$push = & git push -u origin main 2>&1
Write-Host $push
if ($LASTEXITCODE -ne 0) {
    Write-Host "\nPush failed. Troubleshooting tips:";
    Write-Host " - Ensure the remote repo exists on GitHub and was NOT initialized with a README.";
    Write-Host " - Create a Personal Access Token (PAT) on GitHub with 'repo' scope and use it as password when prompted.";
    Write-Host " - Optionally run: git remote set-url origin <your-url> to change remote, then retry.";
    Write-Host " - To avoid repeated prompts, keep credential.helper manager-core (it stores credentials securely).";
} else {
    Write-Host 'Push succeeded.'
}
