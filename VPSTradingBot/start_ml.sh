#!/bin/bash
# Uruchamianie serwera ML Advisor

echo "=========================================="
echo "  Uruchamianie ML Advisor Server (Linux)"
echo "=========================================="

# Sprawdz czy venv istnieje
if [ ! -d ".venv" ]; then
    echo "[INFO] Tworzenie srodowiska wirtualnego..."
    python3 -m venv .venv
fi

# Aktywuj srodowisko (zawsze)
source .venv/bin/activate

# Instalacja/Aktualizacja zaleznosci (zawsze sprawdzamy)
echo "[INFO] Sprawdzanie i instalacja zaleznosci..."
pip install -r requirements.txt

# Dodanie katalogu bieżącego do PYTHONPATH
export PYTHONPATH=$PYTHONPATH:.

# Uruchomienie serwera Uvicorn (FastAPI)
echo "Starting ML Advisor Server on port 8000..."
python -m uvicorn ml.server:app --host 0.0.0.0 --port 8000
