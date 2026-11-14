@echo off
REM ============================================================
REM  One-time setup: links this folder to github.com/kaya7oast/ChiikawaFight
REM  Double-click it once. After that use push_update.bat (or GitHub Desktop).
REM ============================================================
cd /d "%~dp0"
where git >nul 2>nul || (echo Git is not installed. Get it from https://git-scm.com/download/win then run this again. & pause & exit /b 1)
if exist ".git" (echo This folder is already linked to GitHub. Use push_update.bat to upload changes. & pause & exit /b 0)

git init -b main
git remote add origin https://github.com/kaya7oast/ChiikawaFight.git
REM git needs a name for commits; use your GitHub username if none is set yet
git config user.name >nul 2>nul || git config user.name "kaya7oast"
git config user.email >nul 2>nul || git config user.email "kaya7oast@users.noreply.github.com"
echo Downloading the GitHub history (a sign-in window may pop up)...
git fetch origin || (echo Could not reach GitHub. & pause & exit /b 1)
REM adopt GitHub's history but KEEP every file in this folder exactly as it is
git reset origin/main
REM stop tracking junk that got uploaded before (cache files, the stray "github" folder)
git rm -r --cached --quiet --ignore-unmatch ballfight/__pycache__ ballfight/fighters/__pycache__ github
git add -A
git commit -m "Sync from my PC"
git push -u origin main
echo.
echo Done! This folder is now linked to GitHub. The website rebuilds in about 2 minutes.
pause
