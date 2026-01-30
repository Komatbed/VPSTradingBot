# Moduł ML Server

Ten katalog zawiera implementację zewnętrznego serwera AI/ML, który służy jako doradca dla głównego bota tradingowego.

## Struktura

- `server.py`: Serwer FastAPI obsługujący żądania od bota.
- `logic.py`: Logika decyzyjna (ładowanie modelu, reguły heurystyczne, blacklisty).
- `requirements.txt`: Zależności Python dla modułu ML.
- `model.pkl`: (Opcjonalnie) Wytrenowany model scikit-learn (jeśli brak, system działa na regułach).

## Instalacja

Zaleca się utworzenie osobnego środowiska wirtualnego dla ML, jeśli zależności konfliktują z główną aplikacją, ale można też używać głównego venv.

```bash
pip install -r ml/requirements.txt
```

## Uruchomienie

Aby uruchomić serwer na porcie 8000:

```bash
python -m ml.server
```

LUB (używając uvicorn bezpośrednio):

```bash
uvicorn ml.server:app --reload --port 8000
```

## Integracja z Botem

W pliku `.env` głównej aplikacji ustaw:

```ini
ML_BASE_URL="http://localhost:8000"
```

Bot automatycznie wykryje URL i zacznie wysyłać zapytania o ocenę każdego sygnału przed otwarciem pozycji.

## API

### POST /evaluate_setup

Payload:
```json
{
    "instrument": "EURUSD",
    "timeframe": "M5",
    "strategy_id": "trend_following",
    "features": {
        "rr": 2.5,
        "confidence": 75.0,
        "expectancy_r": 0.6,
        "regime": "trending",
        "volatility": 0.0015
    }
}
```

Response:
```json
{
    "ml_score": 25.0,
    "blacklisted": false,
    "reason": "Ocena heurystyczna...",
    "parameter_adjustments": {
        "min_rr": 2.5
    }
}
```
