# Integracja Kalendarza Ekonomicznego - Dokumentacja

## 📖 Instrukcja Użytkownika

System integracji kalendarza ekonomicznego pozwala na śledzenie kluczowych wydarzeń rynkowych, analizę sentymentu ("strachu") oraz otrzymywanie spersonalizowanych powiadomień bezpośrednio w aplikacji Telegram.

### Dostępne Komendy

#### 1. `/kalendarz`
Wyświetla przegląd wydarzeń ekonomicznych na najbliższe 48 godzin.
*   **Działanie:** Pokazuje listę wydarzeń posortowaną chronologicznie.
*   **Filtrowanie:** Domyślnie pokazuje wydarzenia o wpływie `High` i `Medium`.
*   **Oznaczenia:**
    *   🔴 - Wysoki wpływ (High Impact)
    *   🟠 - Średni wpływ (Medium Impact)
    *   🟡 - Niski wpływ (Low Impact)

#### 2. `/wydarzenia [parametry]`
Zaawansowana wyszukiwarka wydarzeń na najbliższe 7 dni (lub określony termin).
*   **Składnia:** `/wydarzenia [waluta] [kategoria] [data]`
*   **Przykłady:**
    *   `/wydarzenia USD` - Wydarzenia dla dolara amerykańskiego.
    *   `/wydarzenia inflation` - Dane o inflacji (CPI, PPI).
    *   `/wydarzenia today` - Wydarzenia na dziś.
    *   `/wydarzenia tomorrow EUR` - Wydarzenia dla Euro na jutro.
    *   `/wydarzenia 2024-06-01` - Wydarzenia na konkretny dzień.
*   **Słowa kluczowe dat:** `today` (dziś), `tomorrow` (jutro), `jutro`, `dzisiaj`.
*   **Kategorie:** `Inflation` (Inflacja), `Employment` (Rynek pracy), `Central Bank` (Banki centralne), `Growth` (PKB), `Sentiment` (Nastroje).

#### 3. `/strach`
Analiza wskaźników strachu i niepewności rynkowej.
*   **Działanie:** Wyświetla aktualny poziom indeksów strachu (VIX, MFI) oraz listę nadchodzących wydarzeń "Fear-Inducing" (powodujących zmienność), takich jak decyzje FOMC, NFP czy odczyty CPI.

#### 4. `/alerts [akcja] [typ] [wartość]`
Zarządzanie spersonalizowanymi powiadomieniami.
*   **Wyświetlanie:** `/alerts` - Pokazuje listę aktywnych subskrypcji.
*   **Dodawanie:**
    *   `/alerts add currency USD` - Powiadomienia o wszystkich newsach dla USD.
    *   `/alerts add category Inflation` - Powiadomienia o danych inflacyjnych (dla wszystkich walut).
*   **Usuwanie:**
    *   `/alerts remove currency USD` - Usunięcie subskrypcji USD.
*   **Czyszczenie:** `/alerts clear` - Usunięcie wszystkich alertów.
*   **Zasada działania:** Otrzymasz powiadomienie 15 minut przed wydarzeniem High Impact spełniającym Twoje kryteria.

---

## 🛠️ Dokumentacja Techniczna

### Architektura Systemu

System składa się z trzech głównych komponentów:

1.  **NewsClient (`app/data/news_client.py`)**
    *   **Odpowiedzialność:** Pobieranie danych z zewnętrznego API (ForexFactory JSON), przetwarzanie, kategoryzacja i filtrowanie.
    *   **Cache:** Dane są przechowywane w pamięci oraz cachowane w `app/data/economic_calendar.json`.
    *   **Historia:** Przeszłe wydarzenia są archiwizowane w `app/data/economic_history.json`.
    *   **Monitoring:** Background task sprawdza co minutę nadchodzące wydarzenia i emituje eventy `ECONOMIC_EVENT_IMMINENT`.

2.  **AlertManager (`app/notifications/alert_manager.py`)**
    *   **Odpowiedzialność:** Zarządzanie subskrypcjami użytkowników.
    *   **Przechowywanie:** Konfiguracja alertów zapisywana w `app/data/alerts_config.json`.
    *   **Logika:** Mapowanie `chat_id` do preferencji (waluty, kategorie) i filtrowanie eventów dla odbiorców.

3.  **TelegramBot (`app/telegram_bot/bot.py`)**
    *   **Interfejs:** Obsługa komend i wyświetlanie danych.
    *   **Event Handling:** Nasłuchuje na eventy z `NewsClient` i dystrybuuje powiadomienia do odpowiednich użytkowników (Admin + Subskrybenci).

### Przepływ Danych (Data Flow)

1.  **Pobranie:** `NewsClient` pobiera JSON z `nfs.faireconomy.media` (co 4h).
2.  **Przetwarzanie:**
    *   Normalizacja stref czasowych do UTC.
    *   Klasyfikacja kategorii (`_classify_event_category`).
    *   Detekcja "Fear Events" (`_is_fear_inducing`).
3.  **Wykrycie Alertu:** Pętla w `NewsClient` wykrywa wydarzenie High Impact w oknie T-15 min.
4.  **Publikacja:** `NewsClient` publikuje `Event(type=ECONOMIC_EVENT_IMMINENT)`.
5.  **Dystrybucja:** `TelegramBot` odbiera event -> pyta `AlertManager` o odbiorców -> wysyła wiadomości.

### Struktura Plików Danych

*   **`economic_calendar.json`**: Aktualny tydzień wydarzeń.
*   **`economic_history.json`**: Archiwum minionych wydarzeń.
*   **`alerts_config.json`**:
    ```json
    {
      "123456789": {
        "currencies": ["USD", "EUR"],
        "categories": ["Inflation"]
      }
    }
    ```

### Testowanie

System pokryty jest testami w `tests/test_calendar_integration.py` (>80% pokrycia kluczowych ścieżek):
*   `test_news_client_categorization_and_fear`: Weryfikacja logiki klasyfikacji.
*   `test_news_client_filtering`: Testy filtrów walutowych, kategoryzacyjnych i czasowych.
*   `test_history_archiving`: Sprawdzenie mechanizmu archiwizacji.
*   `test_alert_manager`: Testy dodawania/usuwania subskrypcji i logiki powiadomień.

Uruchomienie testów:
```bash
python -m unittest tests/test_calendar_integration.py
```
