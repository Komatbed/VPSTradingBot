# Dokumentacja Systemu Tradingowego (VPS Companion)

Dokument ten zawiera szczegółowy opis architektury, logiki decyzyjnej, funkcjonalności oraz struktury danych aplikacji tradingowej.

---

## 1. Przegląd Systemu i Źródła Danych

Aplikacja działa jako asystent tradingowy (Companion) uruchomiony na serwerze VPS. Jej głównym celem jest monitorowanie rynków 24/7, filtrowanie szumu rynkowego i wysyłanie wysokiej jakości sygnałów na Telegram.

### Źródła Danych
1.  **Ceny i Wolumen (Yahoo Finance):**
    *   Biblioteka `yfinance`.
    *   Dane pobierane w interwałach: M5, M15, H1, H4, D1.
    *   Obejmuje: Akcje (GPW, US), Indeksy, Surowce, Forex, Krypto.
2.  **Kalendarz Ekonomiczny (ForexFactory):**
    *   Własny scraper (`NewsClient`).
    *   Filtruje wydarzenia o wysokim wpływie (High Impact).
    *   Używany do blokowania handlu w okresach dużej zmienności.
3.  **Wiedza i Edukacja:**
    *   Wbudowane bazy danych (`INSTRUMENT_CATALOG`, `LEXICON`).

---

## 2. Logika Wyboru i Oceny Trade'u (Lejek Decyzyjny)

System analizuje rynki w procesie wieloetapowym ("Lejek"). Każdy etap musi zostać zaliczony, aby sygnał trafił do użytkownika.

### Etap 1: Analiza Techniczna i Trendu
Sprawdzenie podstawowych warunków dla każdego instrumentu z listy obserwowanych.

*   **Warunki Graniczne:**
    *   **Trend (EMA 200):** Cena musi być powyżej EMA200 dla LONG, poniżej dla SHORT.
    *   **RSI (14):**
        *   Dla LONG: RSI > 40 (momentum) i RSI < 70 (nie wykupiony).
        *   Dla SHORT: RSI < 60 (momentum) i RSI > 30 (nie wyprzedany).
    *   **MACD:** Potwierdzenie kierunku (Histogram > 0 lub przecięcie linii sygnałowej).
*   **Szacunkowa przepustowość:** ~40% wszystkich badanych instrumentów.

### Etap 2: Filtry Bezpieczeństwa (Hard Filters)
Odrzucenie sygnałów ryzykownych pomimo dobrej techniki.

*   **Warunki Graniczne:**
    *   **Filtr Newsowy:** Brak wydarzeń "High Impact" dla waluty bazowej/kwotowanej w oknie: 30 minut przed i 30 minut po.
    *   **Filtr Spreadu:** Spread nie może przekraczać określonego % wartości ceny (np. 0.05% dla Forex), aby nie "zjadał" zysku.
    *   **Sesje Tradingowe:** Preferowane godziny płynności (Londyn/Nowy Jork dla Forex/US, sesja lokalna dla GPW).
    *   **Wolumen:** Wykluczenie "martwych" instrumentów (Volume > 0).
*   **Szacunkowa przepustowość:** ~50% sygnałów z Etapu 1.

### Etap 3: Moduł Machine Learning (ML Advisor)
Ocena jakości sygnału przez wytrenowany model sztucznej inteligencji.

*   **Działanie:**
    *   Model: `RandomForestClassifier` (Las Losowy).
    *   Analizuje wektory cech (Feature Vector): [Wartość RSI, Histogram MACD, Odległość od EMA200, Zmienność ATR, Godzina dnia].
    *   Porównuje obecną sytuację z historyczną bazą danych (decyzje użytkownika).
*   **Warunki Graniczne:**
    *   **Confidence Score:** Model zwraca pewność w % (0-100).
    *   Wymagany próg: Zazwyczaj > 60% pewności modelu, aby przepuścić sygnał.
*   **Szacunkowa przepustowość:** ~30% sygnałów z Etapu 2.

### Etap 4: Zarządzanie Ryzykiem (Risk Management)
Obliczenie parametrów wejścia.

*   **Logika:**
    *   **Stop Loss (SL):** Oparty na zmienności (ATR). Np. `Cena - 1.5 * ATR`.
    *   **Take Profit (TP):** Wyliczany na podstawie minimalnego Risk:Reward (R:R).
    *   **Warunek R:R:** Jeśli potencjalny zysk do ryzyka jest mniejszy niż 1.5:1, sygnał jest **ODRZUCANY**.
*   **Szacunkowa przepustowość:** ~80% sygnałów z Etapu 3.

---

## 3. Moduł Machine Learning (Szczegóły)

Moduł ML w tym systemie nie przewiduje "przyszłej ceny", ale przewiduje **"jakość sygnału w ocenie użytkownika"**.

*   **Cel:** Nauczyć się stylu tradingu użytkownika i odfiltrowywać sygnały, które system generuje, a które użytkownik zazwyczaj odrzuca (przycisk "POMIJAM").
*   **Trening (Learning Loop):**
    1.  Bot wysyła sygnał.
    2.  Użytkownik klika "✅ WCHODZĘ" lub "❌ POMIJAM".
    3.  System zapisuje ten wybór (Label: 1 lub 0) wraz z parametrami rynku w `learning_database.json`.
    4.  Model jest okresowo przetrenowywany na zaktualizowanej bazie.
*   **Pliki:**
    *   `app/ml/client.py`: Logika klienta ML.
    *   `app/data/learning_database.json`: Baza wiedzy (wektory cech + decyzje).

---

## 4. Funkcjonalności dla Użytkownika (Telegram Bot)

Interfejs główny to bot na Telegramie.

### Komendy Główne:
*   `/start` - Powitanie i sprawdzenie połączenia.
*   `/status` - Stan systemu (czy rynki są otwarte, uptime, ostatnie błędy).
*   `/stats` - Wyświetla statystyki skuteczności (Winrate, R:R, Drawdown) w formie estetycznego raportu.
*   `/trade [SYMBOL] [KIERUNEK]` - Ręczne wywołanie analizy dla konkretnego waloru (np. `/trade EURUSD LONG`).
*   `/calc [SYMBOL] entry=X sl=Y` - Kalkulator ryzyka i wielkości pozycji.

### Edukacja i Rozwój:
*   `/learn` - Losowe pojęcie z leksykonu tradingu.
*   `/tips` - Porada psychologiczna lub techniczna.
*   `/profile` - Profil gamifikacji (Poziom, XP, Osiągnięcia).
*   **Tryb Edukacyjny:** Do każdego sygnału dołączana jest sekcja "Analiza Edukacyjna" wyjaśniająca, dlaczego sygnał powstał (Słowa kluczowe, definicje).

### Zarządzanie:
*   `/favorites` (lub edycja pliku) - Zarządzanie listą ulubionych instrumentów.
*   `/pause` / `/resume` - Zatrzymanie/wznowienie wysyłania sygnałów.
*   **Menu Admina:** Restart bota, diagnostyka, podgląd logów.

---

## 5. Struktura Plików i Logów

### Logi (`/logs`)
Pliki logów są rotowane (stare są archiwizowane, aby nie zajmowały miejsca).
*   `app.log`: Główny log operacyjny. Zawiera informacje o:
    *   Pobraniu danych.
    *   Wygenerowaniu sygnału.
    *   Decyzjach ML.
    *   Wysłanych wiadomościach.
*   `errors.log`: Tylko błędy i wyjątki (np. brak połączenia z API, błędy parsowania).

### Dane (`/app/data`)
*   `user_favorites.json`: Lista symboli obserwowanych przez bota (edytowalna przez użytkownika).
*   `learning_database.json`: Baza danych historycznych decyzji do treningu ML.
*   `economic_calendar.json`: Cache kalendarza ekonomicznego (kopia lokalna na wypadek braku internetu).
*   `user_profile.json`: Postępy gracza (XP, Level, Statystyki).

### Backtesty (`/backtest_results`)
Folder zawiera raporty z symulacji historycznych.
*   Pliki `.json` / `.csv`: Wyniki testów strategii na danych historycznych (Skuteczność, Krzywa kapitału).

### Skrypty Uruchomieniowe
*   `start_bot.sh` / `.bat`: Skrypt uruchamiający środowisko wirtualne i proces bota.
*   `tradingbot.service`: Plik konfiguracyjny dla `systemd` (Linux/VPS) do autostartu aplikacji.

---

## 6. Szczegółowy Opis Plików Kodowych

Poniżej znajduje się opis odpowiedzialności poszczególnych modułów i plików w kodzie źródłowym (`app/`).

### Główne Pliki Aplikacji
*   `app/main.py`: Punkt wejścia aplikacji. Inicjalizuje wszystkie podsystemy (Bot Telegrama, Silnik Danych, Strategia, EventBus) i uruchamia główną pętlę asynchroniczną (`asyncio`).
*   `app/config.py`: Centralna konfiguracja. Przechowuje stałe, ścieżki do plików, ustawienia API oraz flagi konfiguracyjne (np. tryb edukacyjny).
*   `app/backtest_runner.py`: Silnik do przeprowadzania testów historycznych. Pozwala sprawdzić skuteczność strategii na danych z przeszłości bez ryzykowania kapitału.
*   `app/instrument_stats_builder.py`: Moduł obliczający statystyki skuteczności (Winrate, R:R, Drawdown) na podstawie historii transakcji.
*   `app/diagnostics.py`: Narzędzie do autodiagnostyki. Sprawdza połączenie z internetem, dostępność API i spójność plików konfiguracyjnych.

### Moduł Telegram (`app/telegram_bot/`)
*   `bot.py`: Główna klasa bota. Obsługuje komendy użytkownika (`/start`, `/trade`), interakcje z przyciskami (Callbacks) oraz formatowanie i wysyłanie wiadomości z sygnałami.

### Moduł Strategii (`app/strategy/`)
*   `engine.py`: Zarządca strategii. Uruchamia odpowiednią strategię dla danego instrumentu i interwału.
*   `base.py`: Klasa bazowa (szablon) dla wszystkich strategii. Definiuje wspólne metody (np. obliczanie wskaźników).
*   `trend_following.py`: Implementacja strategii podążania za trendem (EMA + RSI + MACD).
*   `momentum_breakout.py`: Implementacja strategii wybicia z konsolidacji (Bollinger Bands + Volume).

### Moduł Danych (`app/data/`)
*   `data_engine.py`: Koordynator pobierania danych. Zarządza kolejką zapytań do API, aby nie przekroczyć limitów.
*   `yahoo_client.py`: Klient biblioteki `yfinance`. Pobiera świece cenowe (OHLCV) dla wskazanych symboli.
*   `news_client.py`: Scraper kalendarza ekonomicznego. Pobiera dane o wydarzeniach makroekonomicznych i ocenia ich wpływ na rynek.
*   `instrument_universe.py`: Zarządza listą instrumentów (ulubione, czarna lista) oraz ich metadanymi (sektor, godziny handlu).
*   `tradingview_mapping.py`: Tłumaczy symbole z formatu Yahoo (np. `GC=F`) na format TradingView (np. `COMEX:GC1!`) dla linków do wykresów.

### Moduł Analizy (`app/analysis/`)
*   `sentiment_engine.py`: Silnik analizy sentymentu. Oblicza wskaźniki MFI (Market Fear Index) i GTI (Global Tension Index) na podstawie zmienności i korelacji.
*   `briefing.py`: Generator codziennych odpraw rynkowych. Agreguje dane o rynkach, newsach i sentymencie w jeden raport.

### Moduł Machine Learning (`app/ml/`)
*   `client.py`: Klient modelu ML. Odpowiada za przygotowanie danych (Feature Engineering), trening modelu (`fit`) oraz predykcję (`predict_proba`) dla nowych sygnałów.

### Moduł Ryzyka (`app/risk/`)
*   `engine.py`: Kalkulator wielkości pozycji. Oblicza Risk-per-Trade w oparciu o wielkość konta i odległość do Stop Loss.
*   `guard.py`: "Strażnik" przed overtradingiem. Blokuje otwieranie zbyt wielu pozycji na tym samym instrumencie lub w krótkim czasie.

### Moduł Edukacji i Wiedzy (`app/knowledge/`)
*   `lexicon.py`: Słownik pojęć tradingowych (np. co to jest RSI, Swap, Spread).
*   `instruments.py`: Encyklopedia instrumentów. Zawiera opisy spółek, surowców i par walutowych.
*   `manual.py`: Instrukcja obsługi bota dostępna z poziomu czatu.

### Moduł Gamifikacji (`app/gamification/`)
*   `engine.py`: Silnik grywalizacji. Przyznaje punkty doświadczenia (XP) za poprawne decyzje i awansuje użytkownika na kolejne poziomy (Novice -> Grandmaster).

### Rdzeń Systemu (`app/core/`)
*   `event_bus.py`: Szyna zdarzeń. Umożliwia asynchroniczną komunikację między modułami (np. "Dane pobrane" -> "Uruchom strategię").
*   `models.py`: Definicje struktur danych (Data Classes), takich jak `Signal`, `Trade`, `Bar`.

PRZYKŁĄDOWA WIADOMOŚĆ TELEGRAM:
🟢 **LONG** #CVX (Chevron) | H1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **Score:** ✨ 83/100
⚖️ **R:R:** 2.00R

📉 **Poziomy:**
   🔹 **Entry:** 169.92
   🛑 **SL:** 168.33
   🚀 **TP:** 173.10

📊 **Sentyment:**
   😨 Fear: 90.0
   ⚡ Tension: 90.0

ℹ️ **Uzasadnienie:**
Cena powyżej średniej. silne odchylenie od średniej, zgodność z EMA200. | Score: 78 (TRADE) (Strategia: trend_following_simple, Oczekiwany wynik: 0.42R). Wsparcie: 151.25, 154.90, 165.15. Wykres: https://www.tradingview.com/chart/?symbol=CVX
Dodatkowe atuty: Wysoka zmienność rynku (+5pkt), Dobra historyczna skuteczność (+5pkt), RSI wykupione (76.9, -5pkt).

🎓 **ANALIZA EDUKACYJNA**
🔸 **Słowa kluczowe:** RSI, EMA, TREND

📘 **Instrument: Chevron**
ℹ️ **Czym jest:** Koncern paliwowo-energetyczny. Zajmuje się wydobyciem, rafinacją i sprzedażą ropy oraz gazu. (Instrument typu: Akcja (US)).

💡 *Porada:* Nigdy nie ryzykuj więcej niż ustalone w planie (np. 1-2% kapitału na transakcję).
