import os
import sys
import subprocess
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki Pythona
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.data.instrument_universe import DEFAULT_INSTRUMENT_UNIVERSE

def main():
    print("=== Rozpoczynam pełne trenowanie modelu na całej bazie instrumentów ===")
    
    # 1. Przygotuj listę symboli
    # Usuwamy duplikaty jeśli są
    symbols = list(set(DEFAULT_INSTRUMENT_UNIVERSE))
    
    if "--test" in sys.argv or "--quick" in sys.argv:
        print("TRYB TESTOWY: Używam tylko pierwszych 5 symboli.")
        symbols = symbols[:5]
        
    print(f"Znaleziono {len(symbols)} instrumentów w bazie.")
    
    # Konwertuj do stringa po przecinku
    symbols_str = ",".join(symbols)
    
    # 2. Ustaw zmienne środowiskowe
    env = os.environ.copy()
    env["BACKTEST_SYMBOLS"] = symbols_str
    env["BACKTEST_TIMEFRAME"] = "h1" # Domyślnie h1, ale runner i tak zrobi d1 najpierw
    # Pozwalamy na zbieranie danych nawet z 'gorszych' instrumentów (dla celów nauki)
    # Ustawiamy bardzo niski próg expectancy, żeby runner nie odrzucał zbyt wielu symboli przed analizą h1
    # Ale uwaga: runner zbiera dane treningowe z D1 tak czy siak.
    # Jeśli chcemy dane z H1, musimy pozwolić na wejście w H1.
    env["BACKTEST_MIN_EXPECTANCY_1D"] = "-100.0" 
    
    print("Uruchamiam generowanie danych (Backtest Runner)... to może potrwać chwilę.")
    
    # 3. Uruchom Backtest Runner
    # Używamy subprocess, żeby uruchomić jako osobny proces (czystsza pamięć)
    try:
        # python -m app.backtest_runner
        subprocess.run([sys.executable, "-m", "app.backtest_runner"], env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas generowania danych: {e}")
        return

    print("\nGenerowanie danych zakończone.")
    
    # 4. Uruchom Trening
    print("Uruchamiam trenowanie modelu (ML Train)...")
    try:
        subprocess.run([sys.executable, "ml/train.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas trenowania modelu: {e}")
        return
        
    print("\n=== Proces zakończony sukcesem! ===")
    print("Model został wytrenowany na wszystkich dostępnych danych.")

if __name__ == "__main__":
    main()
