@echo off
chcp 65001 > nul
echo ===================================================
echo   Wysylanie wynikow backtestu na VPS
echo ===================================================

REM --- KONFIGURACJA (UZUPELNIJ DANE) ---
set VPS_USER=ubuntu
set VPS_HOST=51.77.59.105
set VPS_PATH=C:/Sciezka/Do/Aplikacji/backtests/
REM -------------------------------------

echo Wysylanie plikow JSON z folderu backtests/ do %VPS_USER%@%VPS_HOST%:%VPS_PATH% ...

REM Wymaga zainstalowanego klienta OpenSSH (wbudowany w Windows 10/11)
scp backtests/*.json %VPS_USER%@%VPS_HOST%:%VPS_PATH%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [BLAD] Nie udalo sie wyslac plikow. Sprawdz dane logowania i sciezke.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [SUKCES] Pliki wyslane! Zrestartuj bota na VPS, aby zaladowal nowe dane.
pause
