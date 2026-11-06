@echo off
set PYTHONUTF8=1

REM Check if a file name was actually provided
if "%~1"=="" (
    echo [ERROR] Please provide a Python file to compile.
    echo Example: compile main.py
    exit /b 1
)

echo [INFO] Starting Nuitka compilation for: %1
set "start_time=%TIME%"
echo [INFO] Starting Time: %start_time%
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

set "end_time=%TIME%"
echo [INFO] Ending Time: %end_time%

:: --- Calculate Time Difference ---
for /f "tokens=1-4 delims=:., " %%a in ("%start_time%") do (
    set /a "start_h=100%%a %% 100", "start_m=100%%b %% 100", "start_s=100%%c %% 100", "start_ms=100%%d %% 100"
)
for /f "tokens=1-4 delims=:., " %%a in ("%end_time%") do (
    set /a "end_h=100%%a %% 100", "end_m=100%%b %% 100", "end_s=100%%c %% 100", "end_ms=100%%d %% 100"
)

set /a "hours=end_h-start_h", "mins=end_m-start_m", "secs=end_s-start_s", "ms=end_ms-start_ms"

if %ms% lss 0 set /a "secs=secs-1", "ms=ms+100"
if %secs% lss 0 set /a "mins=mins-1", "secs=secs+60"
if %mins% lss 0 set /a "hours=hours-1", "mins=mins+60"
if %hours% lss 0 set /a "hours=hours+24"

set /a "totalsecs=hours*3600 + mins*60 + secs"

echo [INFO] Compilation process finished.
echo [INFO] Time Elapsed: %hours%h %mins%m %secs%.%ms%s (%totalsecs% seconds total)