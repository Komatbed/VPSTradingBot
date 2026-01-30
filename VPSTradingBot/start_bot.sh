#!/bin/bash
echo "=========================================="
echo "  Uruchamianie VPS Companion (Linux)"
echo "=========================================="

# Sprawdz czy venv istnieje
if [ ! -d ".venv" ]; then
    echo "[INFO] Tworzenie srodowiska wirtualnego..."
    python3 -m venv .venv
fi

# Aktywuj srodowisko (zawsze)
source .venv/bin/activate

# Instalacja/Aktualizacja zaleznosci
echo "[INFO] Sprawdzanie i instalacja zaleznosci..."
pip install -r requirements.txt

# Uruchomienie bota
echo "Uruchamianie bota..."
python3 -m app.main
