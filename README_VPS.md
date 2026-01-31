# Instrukcja wdrożenia na VPS

## 1. Wymagania wstępne
- Zainstalowany Python 3.10 lub nowszy.
- Dostęp do terminala/CMD.

## 1a. Przygotowanie plików (Ważne!)
Przed wysłaniem plików na VPS, uruchom skrypt `prepare_deployment.ps1` (Windows PowerShell), aby stworzyć czystą paczkę:
```powershell
./prepare_deployment.ps1
```
Skrypt utworzy folder `deployment_package`. **Wyślij na VPS tylko zawartość tego folderu.**
Dzięki temu unikniesz problemów z uprawnieniami (Access Denied) związanych z folderami cache (`__pycache__`).

**UWAGA: ML Advisor**
Upewnij się, że w paczce znajduje się plik `ml/model.pkl` (wytrenowany model). Jeśli go nie ma, musisz go wytrenować lokalnie (`python ml/train_full.py`) i dograć ręcznie na VPS.

## 2. Instalacja zależności (Rozwiązanie błędu "externally managed environment")
Nowoczesne systemy Linux wymagają użycia wirtualnego środowiska (`venv`). Wykonaj poniższe komendy w folderze projektu:

```bash
# 1. Zainstaluj pakiet venv (jeśli go nie ma, np. na Ubuntu)
sudo apt update
sudo apt install python3-venv -y

# 2. Utwórz wirtualne środowisko
python3 -m venv .venv

# 3. Aktywuj środowisko
source .venv/bin/activate

# 4. Zainstaluj zależności (teraz zadziała bez błędów)
pip install -r requirements.txt
```

*Uwaga: Od teraz zawsze przed ręcznym uruchamianiem komend `python` lub `pip` musisz aktywować środowisko komendą `source .venv/bin/activate`.*

## 3. Konfiguracja
1. Skopiuj plik `.env.example` i zmień jego nazwę na `.env`.
2. Edytuj plik `.env` i uzupełnij wymagane dane:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ML_BASE_URL=http://localhost:8000` (Dla ML Advisora)

## 4. Uruchamianie

System składa się teraz z dwóch części:
1. **ML Advisor Server** (Serwer AI) - musi działać w tle.
2. **Trading Bot** (Główna aplikacja) - korzysta z serwera AI.

### Krok 1: Uruchom ML Advisor

**Windows:**
Uruchom plik `start_ml.bat`. Otworzy się nowe okno z serwerem. Zostaw je otwarte.

**Linux:**
```bash
chmod +x start_ml.sh
./start_ml.sh &
```

### Krok 2: Uruchom Trading Bota

**Windows:**
Uruchom plik `start_bot.bat`.

**Linux:**
```bash
chmod +x start_bot.sh
./start_bot.sh
```

## 5. Automatyzacja (Autostart - Zalecane dla VPS Linux)

Aby obie usługi wstawały same po restarcie:

### 1. Skonfiguruj ML Advisor Service
1. Edytuj `deploy/ml_advisor.service` (sprawdź ścieżki!).
2. Instalacja:
   ```bash
   sudo cp deploy/ml_advisor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable ml_advisor
   sudo systemctl start ml_advisor
   ```

### 2. Skonfiguruj Trading Bot Service
1. Edytuj `deploy/tradingbot.service` (sprawdź ścieżki!).
2. Instalacja:
   ```bash
   sudo cp deploy/tradingbot.service /etc/systemd/system/
   sudo systemctl enable tradingbot
   sudo systemctl start tradingbot
   ```

### Status usług
Możesz sprawdzić czy wszystko działa:
```bash
sudo systemctl status ml_advisor
sudo systemctl status tradingbot
```

## 6. Rozwiązywanie problemów (Troubleshooting)

### Błąd: "Permission denied" przy pip install
Jeśli widzisz błąd `OSError: [Errno 13] Permission denied: ... .venv/...`, oznacza to, że folder `.venv` został utworzony przez `root` (użyłeś `sudo`), a teraz próbujesz go używać jako zwykły użytkownik.

**Naprawa:**
Zmień właściciela folderu `.venv` na siebie:
```bash
sudo chown -R $USER:$USER .venv
```
Następnie spróbuj ponownie uruchomić `./start_ml.sh`.
