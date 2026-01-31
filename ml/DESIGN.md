# ML Advisor Architecture Design

## 1. Wstęp
Moduł ML Advisor to zaawansowany system wspomagania decyzji tradingowych, działający jako zewnętrzny filtr dla sygnałów generowanych przez strategie algorytmiczne. Jego celem nie jest przewidywanie ceny, lecz ocena **jakości setupu** (Quality of Setup) w kontekście bieżących warunków rynkowych.

## 2. Architektura Warstwowa (Layered Architecture)

Decyzja o akceptacji trade'u przechodzi przez potok (pipeline) składający się z 7 warstw. Każda warstwa może zmodyfikować ocenę, dodać metadane lub zawetować transakcję.

### Warstwa 1: Market Playability Layer (Czy w ogóle gramy?)
*   **Cel:** Ochrona kapitału przed warunkami niesprzyjającymi handlowi.
*   **Logika:**
    *   Sprawdzenie godzin sesji (np. unikanie spreadów o 23:00).
    *   Bliskość danych makro (News Blackout): Jeśli High Impact News za < 30 min -> SKIP.
    *   Global Market Tension: Jeśli VIX > 40 (panika) -> SKIP (chyba że strategia typu Panic Reversal).

### Warstwa 2: Safety & Risk Layer (Hard Rules)
*   **Cel:** Eliminacja setupów o ujemnej wartości oczekiwanej matematycznej.
*   **Reguły:**
    *   `Risk:Reward < 1.0` -> REJECT (chyba że strategia Scalping z WinRate > 80%).
    *   `Signal Confidence < 50%` -> REJECT.
    *   `SL Distance` < Minimum Market Noise (zbyt ciasny SL).

### Warstwa 3: AI Prediction Layer (Probabilistic Core)
*   **Model:** Gradient Boosting (XGBoost/LightGBM) lub Random Forest.
    *   *Dlaczego nie Deep Learning?* Tabularne dane finansowe o niskim stosunku sygnału do szumu (low signal-to-noise ratio) lepiej obsługują drzewa decyzyjne, które są mniej podatne na overfitting przy małej liczbie próbek i łatwiejsze w interpretacji (Feature Importance).
*   **Input:** Wektor cech (opisany w sekcji 3).
*   **Output:** Prawdopodobieństwo sukcesu (`win_prob`), Oczekiwany zwrot (`expected_r`).

### Warstwa 4: Rule / Heuristic Layer (Trader's Wisdom)
*   **Cel:** Wprowadzenie wiedzy domenowej, której model mógł jeszcze nie wyłapać.
*   **Heurystyki:**
    *   **Trend Alignment:** Bonus za zgodność z trendem HTF (Higher Timeframe).
    *   **Liquidity Check:** Kara za trading w środku konsolidacji (wąski zakres, niska zmienność).
    *   **Session Premium:** Bonus za setupy London Open / NY Open.

### Warstwa 5: Feedback & Adaptation Layer
*   **Cel:** Dynamiczne dostosowanie kryteriów do zmienności.
*   **Mechanizm:**
    *   Jeśli `Volatility Percentile > 90%` (szpilki) -> Wymuś `Min RR = 2.5` (bo ryzyko poślizgu i zmienności jest duże).
    *   Jeśli `Market Regime = Ranging` -> Wymuś `Min Confidence = 80%` dla strategii trendowych.

### Warstwa 6: A+/B/C Setup Classification
*   **Klasyfikacja:**
    *   **A+ (Diamond):** Score > 85. Idealne warunki, zgoda AI i reguł. (Pełne ryzyko).
    *   **B (Gold):** Score 60-85. Dobre setupy, pewne mankamenty. (Standardowe ryzyko).
    *   **C (Trash):** Score < 60. Odrzucone. (Brak ryzyka).

### Warstwa 7: Explainability & Education Layer
*   **Cel:** Użytkownik musi rozumieć decyzję.
*   **Output:** Generowanie tekstu "Human-readable".
    *   "Odrzucono, ponieważ rynek jest w wąskiej konsolidacji przed danymi FOMC."
    *   "Zatwierdzono jako setup A+: Zgodność trendu H1/H4 + Wysoka płynność sesji Londyńskiej."

---

## 3. Feature Engineering

Zestaw cech przesyłanych do modelu:

### A. Setup Features
1.  `rr` (float): Risk to Reward ratio.
2.  `sl_distance_atr` (float): Odległość SL wyrażona w krotności ATR (czy SL jest techniczny czy przypadkowy?).
3.  `entry_type` (categorical): `pullback`, `breakout`, `reversal`.

### B. Market Regime Features
4.  `trend_strength_adx` (float): Siła trendu (np. ADX).
5.  `volatility_atr_percentile` (float 0-1): Czy zmienność jest niska (0.1) czy ekstremalna (0.9) na tle ostatnich N okresów.
6.  `htf_bias` (float -1 to 1): Kierunek trendu na wyższym interwale.

### C. Context Features
7.  `session_phase` (categorical): `asian_range`, `london_open`, `ny_overlap`, `late_us`.
8.  `news_proximity_min` (int): Minuty do najbliższego eventu High Impact.
9.  `time_of_day_score` (float): Historyczna skuteczność danej godziny dla instrumentu.

---

## 4. Model & Trening

*   **Typ:** Random Forest Classifier (na start) -> XGBoost (docelowo).
*   **Target:** `is_profitable` (1 jeśli profit > 0.5R, 0 w przeciwnym razie).
*   **Trening:** Offline, raz w tygodniu (re-training).
*   **Plik:** `ml/model.pkl`.
*   **Fallback:** Jeśli brak pliku, system działa w trybie `Rule-Based Expert System`.

---

## 5. Deployment Checklist

1.  [x] Struktura katalogów `ml/`.
2.  [x] Serwer API (`ml/server.py`).
3.  [x] Implementacja pełnej logiki warstwowej w `ml/logic.py`.
4.  [x] Rozszerzenie modelu danych wejściowych.
5.  [x] Integracja `StrategyEngine` z nowym API (przesyłanie dodatkowych cech).
6.  [x] Testy na danych historycznych (weryfikacja logiki `ml/test_logic.py` + `BacktestEngine`).
