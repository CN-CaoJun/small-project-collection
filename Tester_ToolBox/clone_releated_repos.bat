@echo off
setlocal
set REPO_DIR=%~dp0reference_modules
if not exist "%REPO_DIR%" mkdir "%REPO_DIR%"
cd /d "%REPO_DIR%"

echo cloning python-can ...
git clone https://github.com/hardbyte/python-can.git
echo cloning python-can-isotp ...
git clone https://github.com/pylessard/python-can-isotp.git
echo cloning python-udsoncan ...
git clone https://github.com/pylessard/python-udsoncan.git

echo cloning completed.
pause