Quick guide: push local repo to GitHub (HTTPS, use PAT)

1. On GitHub: create new repo "Railovo/demo" (do NOT initialize with README). Copy the HTTPS URL: https://github.com/Railovo/demo.git

2. Generate PAT (Personal Access Token):
   - GitHub -> Settings -> Developer settings -> Personal access tokens -> Generate new token (classic)
   - Give 'repo' scope, generate, copy token (shown once).

3. In PowerShell (project root):
   - Allow script: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   - Run helper (script auto-uses repo URL but you can pass one):
     .\scripts\push_to_github.ps1 https://github.com/Railovo/demo.git
   - When prompted for username enter: Railovo
   - For password enter: the PAT you generated

4. If push fails:
   - Run: git remote set-url origin https://github.com/Railovo/demo.git
   - Retry the push command above

5. Optional: configure credential manager to cache credentials
   git config --global credential.helper manager-core

Notes:
- The script does NOT store your PAT. The credential manager securely caches it.
- If you prefer SSH, follow GitHub SSH key setup and use the SSH remote URL.
