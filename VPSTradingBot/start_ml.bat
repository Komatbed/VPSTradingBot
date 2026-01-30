@echo off
echo Starting ML Advisor Server...

:: Aktywacja wirtualnego srodowiska (jesli istnieje)
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

:: Dodanie katalogu biezacego do PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;.

:: Uruchomienie serwera Uvicorn
python -m uvicorn ml.server:app --host 0.0.0.0 --port 8000
pause
