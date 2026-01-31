@echo off
chcp 65001 > nul
echo ===================================================
echo   Uruchamianie lokalnego backtestu (VPS Companion)
echo ===================================================

REM Sprawdz czy istnieje venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [INFO] Nie znaleziono wirtualnego srodowiska ^(.venv^). Uzywam systemowego Pythona.
)

REM Ustawienia domyslne (mozna nadpisac w .env)
set PYTHONPATH=%CD%
set DATA_SOURCE=yahoo

echo.
echo Uruchamianie skryptu backtestu...
echo.

python -m app.backtest_runner

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BLAD] Wystapil blad podczas backtestu.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo   Backtest zakonczony sukcesem!
echo   Wyniki znajduja sie w folderze: backtests\
echo ===================================================
echo.
pause
