@echo off
set PYTHONUTF8=1
REM Check if a file name was actually provided
if "%~1"=="" (
    echo [ERROR] Please provide a Python file to compile.
    echo Example: compile main.py
    exit /b 1
)

echo [INFO] Starting Nuitka compilation for: %1
echo [INFO] Starting Time: %TIME%
echo [INFO] Forcing UTF-8 mode and utilizing system-native Windows Runtimes...

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=force ^
    --nofollow-import-to=pandas.tests ^
    --lto=no ^
    --include-windows-runtime-dlls=no ^
    --jobs=4 ^
    --quiet ^
    %1

echo [INFO] Ending Time: %TIME%
echo [INFO] Compilation process finished.