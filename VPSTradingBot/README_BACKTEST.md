# Instrukcja Backtestów Lokalnych

Aby odciążyć VPS, zaleca się przeprowadzanie backtestów na komputerze lokalnym, a następnie przesyłanie wyników na serwer. System automatycznie nauczy się z przesłanych danych.

## 1. Przygotowanie środowiska lokalnego

1. Upewnij się, że masz zainstalowanego Pythona (3.9+).
2. Zainstaluj wymagane biblioteki:
   ```cmd
   pip install -r requirements.txt
   ```
3. (Opcjonalnie) Skonfiguruj plik `.env` jeśli chcesz zmienić domyślne parametry (np. listę instrumentów).
   * Utwórz `.env` na wzór `.env.example`.
   * Możesz zdefiniować `BACKTEST_SYMBOLS=EURUSD=X,GBPUSD=X` aby przetestować tylko wybrane pary.

## 2. Uruchomienie Backtestu

Wystarczy uruchomić przygotowany skrypt:

* **Windows**: Kliknij dwukrotnie `run_local_backtest.bat`
* **Linux/Mac**: Uruchom `./run_local_backtest.sh`

Skrypt:
1. Pobierze dane historyczne (z Yahoo Finance).
2. Przeprowadzi symulację strategii.
3. Zapisze wyniki w folderze `backtests/` (pliki `.json` i podsumowania `.csv`).

## 3. Wysyłka wyników na VPS

Aby bot na VPS skorzystał z nowej wiedzy:

1. Edytuj plik `upload_backtests_template.bat` (notatnikiem).
2. Uzupełnij dane logowania do VPS:
   * `VPS_USER`: nazwa użytkownika (np. administrator)
   * `VPS_HOST`: adres IP serwera
   * `VPS_PATH`: ścieżka do folderu `backtests/` na serwerze (np. `C:/TradingBot/backtests/`)
3. Zapisz plik (możesz zmienić nazwę na `upload_backtests.bat`).
4. Uruchom go.

Alternatywnie skopiuj pliki `*.json` z lokalnego folderu `backtests/` do tego samego folderu na VPS ręcznie (np. przez Pulpit Zdalny).

## 4. Efekt

Po restarcie bota na VPS (lub przy kolejnym odświeżeniu), system wczyta pliki JSON i zaktualizuje wskaźnik `Expectancy` (oczekiwana skuteczność) dla danych par walutowych.
