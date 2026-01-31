@echo off
echo ==========================================
echo   Uruchamianie VPS Companion (Windows)
echo ==========================================

REM Sprawdz czy venv istnieje
if not exist ".venv" (
    echo [BLAD] Nie znaleziono srodowiska wirtualnego .venv!
    echo Uruchom najpierw: python -m venv .venv
    echo A nastepnie zainstaluj zaleznosci: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b
)

REM Aktywacja srodowiska
call .venv\Scripts\activate

REM Uruchomienie bota
echo Uruchamianie bota...
python -m app.main

pause
