@echo off
echo Starting Trading Bot System...
echo Check bot_output.log for logs if console is silent.

:: Set Python Path
set PYTHONPATH=%CD%

:: Check if venv exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found, using system python...
)

:: Run the application
python app/main.py

pause
