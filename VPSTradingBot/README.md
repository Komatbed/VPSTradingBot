# 🚀 Trading Bot VPS Companion

Profesjonalny asystent tradingowy zintegrowany z Telegramem, wyposażony w moduły analizy sentymentu, danych makroekonomicznych oraz wsparcia ML.

## 📋 Spis Treści
- [Wymagania](#-wymagania)
- [Instalacja](#-instalacja)
- [Uruchomienie](#-uruchomienie)
- [Zarządzanie (Manage CLI)](#-zarządzanie-manage-cli)
- [Funkcjonalności](#-funkcjonalności)
- [Struktura Projektu](#-struktura-projektu)

## 💻 Wymagania
- Python 3.10+
- Konto Telegram (Token Bota)
- (Opcjonalnie) Serwer VPS do pracy ciągłej

## 🛠 Instalacja

1. **Sklonuj repozytorium**
2. **Stwórz wirtualne środowisko:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. **Zainstaluj zależności:**
   ```powershell
   python manage.py install
   # lub
   pip install -r requirements.txt
   ```
4. **Skonfiguruj środowisko:**
   - Skopiuj `.env.example` do `.env` (jeśli istnieje, w przeciwnym razie stwórz `.env`).
   - Uzupełnij tokeny:
     ```ini
     TELEGRAM_BOT_TOKEN=twoj_token
     TELEGRAM_CHAT_ID=twoj_chat_id
     ML_BASE_URL=http://localhost:8000
     ```

## 🚀 Uruchomienie

Projekt posiada wbudowany skrypt zarządzający `manage.py`, który ułatwia codzienne operacje.

### 1. Start ML Server (wymagany dla logiki ML)
```powershell
python manage.py ml
```
_Uruchamia serwer FastAPI na porcie 8000._

### 2. Start Trading Bota
```powershell
python manage.py start
```
_Uruchamia głównego bota Telegramowego._

### 3. Diagnostyka Systemu
```powershell
python manage.py diag
```
_Wykonuje pełny skan integralności plików, połączeń API i stanu kodu._

## 🎮 Funkcjonalności

### 🤖 Telegram Bot
- **Sygnały**: Automatyczne powiadomienia o setupach (Trend, Momentum, Reversion).
- **Interakcja**: Przyciski pod sygnałami (Pomiń, Przypomnij, TradingView).
- **Komendy**:
  - `/menu` - Panel główny.
  - `/diag` - Status systemu.
  - `/briefing` - Poranny raport rynkowy.
  - `/learn <hasło>` - Leksykon tradera.
  - `/calc` - Szybki kalkulator ryzyka.

### 🧠 Edukacja & Gamifikacja
- **XP & Poziomy**: Zdobywaj doświadczenie za aktywność (czytanie briefingów, analiza setupów).
- **Leksykon**: Wbudowana baza wiedzy (RSI, FVG, Order Blocks).
- **Karty Wiedzy**: Losowe fiszki edukacyjne.

### 📊 Dane
- **Yahoo Finance**: Dane cenowe w czasie rzeczywistym (z mechanizmem retry).
- **News Client**: Kalendarz ekonomiczny (High Impact filter).
- **Sentiment Engine**: Analiza sentymentu rynkowego (MFI/GTI).

## 📂 Struktura Projektu

```
app/
├── analysis/       # Silniki analizy (Sentyment, Briefing)
├── data/           # Klienci danych (Yahoo, News, Profile)
├── execution/      # Egzekucja zleceń (Oanda/Paper)
├── gamification/   # Logika grywalizacji
├── knowledge/      # Baza wiedzy (Leksykon, Dekalog)
├── ml/             # Klient ML Advisor
├── strategy/       # Strategie handlowe
├── telegram_bot/   # Obsługa Telegrama (aiohttp)
├── diagnostics.py  # Silnik autodiagnostyki
└── main.py         # Entry point bota
ml/
└── server.py       # Serwer ML (FastAPI)
```

## 📝 Wskazówki Deweloperskie

- **Czyszczenie Cache**: `python manage.py clean`
- **Backtesty**: `python manage.py backtest`
- **Logi**: Zapisywane w folderze `logs/` (rotacja automatyczna).

---
*Projekt stworzony jako VPS Companion dla Traderów.*
