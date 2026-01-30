#!/bin/bash

echo "==================================================="
echo "  Uruchamianie lokalnego backtestu (VPS Companion)"
echo "==================================================="

# Aktywacja venv jesli istnieje
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH=$(pwd)
export DATA_SOURCE="yahoo"

echo ""
echo "Uruchamianie skryptu backtestu..."
echo ""

python3 -m app.backtest_runner

if [ $? -ne 0 ]; then
    echo ""
    echo "[BLAD] Wystapil blad podczas backtestu."
    exit 1
fi

echo ""
echo "==================================================="
echo "  Backtest zakonczony sukcesem!"
echo "  Wyniki znajduja sie w folderze: backtests/"
echo "==================================================="
echo ""
