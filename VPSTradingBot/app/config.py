import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from app.data.instrument_universe import DEFAULT_INSTRUMENT_UNIVERSE, INSTRUMENT_SECTIONS

# =============================================================================
# KONFIGURACJA GLOBALNA APLIKACJI (VPS COMPANION)
# =============================================================================
# Ten plik jest CENTRALNYM punktem sterowania całą aplikacją.
# Znajdziesz tutaj:
# 1. Parametry Gamifikacji (XP, Rangi, Osiągnięcia)
# 2. Parametry Sentymentu (Progi strachu, wagi)
# 3. Parametry Newsów (Interwały aktualizacji)
# 4. Konfigurację techniczną (Tokeny, tryby, instrumenty)
#
# Zmieniaj te wartości ostrożnie. Są one używane przez wiele modułów.
# =============================================================================

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA GAMIFIKACJI (STAŁE I ZASADY)
# -----------------------------------------------------------------------------
class GamificationConstants:
    """
    Stałe i konfiguracja dla modułu grywalizacji (Gamification).
    Definiuje poziomy, rangi, tabele XP oraz osiągnięcia.
    """
    # --- XP & LEVELING ---
    XP_PER_LEVEL = 1000  # Wymagane XP na każdy kolejny poziom
    
    # Rangi (Tytuły) w zależności od poziomu
    # Format: (Min_Level, Title, Description)
    RANKS: List[Tuple[int, str, str]] = [
        (1,  "Novice Trader",       "Początkujący. Skup się na ochronie kapitału."),
        (5,  "Apprentice Trader",   "Uczeń. Budujesz swoje pierwsze nawyki."),
        (10, "Journeyman Trader",   "Czeladnik. Zaczynasz widzieć powtarzalność."),
        (20, "Master Trader",       "Mistrz. Proces jest ważniejszy niż wynik."),
        (50, "Grandmaster Trader",  "Arcymistrz. Trading to stan umysłu.")
    ]

    # --- TABELA XP (ZA CO NAGRADZAMY) ---
    XP_TABLE: Dict[str, int] = {
        # A. OTWARCIE POZYCJI (Niska nagroda - sam start to nie sukces)
        "action_enter": 10,       # Wejście w trade
        "action_skip": 5,         # Świadome odpuszczenie okazji
        
        # B. ZAMKNIĘCIE POZYCJI (Kluczowe dla nawyków)
        "close_tp": 50,           # Take Profit (Plan wykonany)
        "close_sl": 15,           # Stop Loss (Plan wykonany - ochrona kapitału!)
        "close_manual": 20,       # Manualne wyjście (Zmiana planu)
        "close_panic": 5,         # Paniczne wyjście (Niepolecane)
        "close_no_log": 0,        # Brak logowania wyniku
        
        # C. DZIENNIK I ANALIZA
        "journal_full": 5,        # Pełny wpis do dziennika (/result + opis)
        "journal_short": 2,       # Krótki wpis
        
        # D. EDUKACJA
        "edu_briefing": 10,       # Przeczytanie briefingu
        "edu_backtest": 5,        # Wykonanie backtestu
        "edu_learn": 2,           # Nauka pojęcia (/learn)
        "edu_tips": 1,            # Przeczytanie porady (/tips)
        
        # E. INNE
        "checkin": 5,             # Dzienna aktywność (uruchomienie bota)
    }

    # --- LIMITY (ANTI-FARMING) ---
    # Ile razy dziennie można dostać XP za daną czynność
    DAILY_LIMITS: Dict[str, int] = {
        "edu_learn": 5,           # Max 5 pojęć dziennie
        "edu_tips": 3,            # Max 3 porady dziennie
        "edu_backtest": 3,        # Max 3 backtesty dziennie
        "action_enter": 10,       # Max 10 wejść dziennie (anty-overtrading)
        "action_skip": 10         # Max 10 odpuszczeń dziennie
    }

    # --- STREAKI (SERIE) ---
    STREAKS: Dict[str, Dict[str, Any]] = {
        "journal_streak": {
            "name": "Journal Keeper",
            "thresholds": [3, 7, 14, 30, 60], # Dni z rzędu z wpisem
            "bonus_xp": [20, 50, 100, 200, 500]
        },
        "discipline_streak": {
            "name": "Iron Discipline",
            "condition": "close_tp_or_sl", # Trade zamknięty zgodnie z planem
            "thresholds": [5, 10, 20, 50], # Ilość trade'ów z rzędu
            "bonus_xp": [50, 150, 500, 1000]
        }
    }

    # --- OSIĄGNIĘCIA (ACHIEVEMENTS) ---
    ACHIEVEMENTS: List[Dict[str, Any]] = [
        {
            "id": "first_blood",
            "title": "Pierwszy Krok",
            "description": "Zaloguj swój pierwszy trade (/result).",
            "condition_type": "count",
            "condition_key": "trades_logged",
            "threshold": 1,
            "xp_reward": 50
        },
        {
            "id": "student",
            "title": "Pilny Student",
            "description": "Naucz się 5 pojęć (/learn).",
            "condition_type": "count",
            "condition_key": "manual_reads",
            "threshold": 5,
            "xp_reward": 100
        },
        {
            "id": "risk_manager",
            "title": "Strażnik Ryzyka",
            "description": "Zakończ 10 trade'ów na Stop Lossie.",
            "condition_type": "count",
            "condition_key": "close_sl_count",
            "threshold": 10,
            "xp_reward": 200
        },
        {
            "id": "process_oriented",
            "title": "Proces > Wynik",
            "description": "Zaloguj 50 trade'ów w dzienniku.",
            "condition_type": "count",
            "condition_key": "trades_logged",
            "threshold": 50,
            "xp_reward": 300
        }
    ]

    # --- DZIENNIK (SŁOWA KLUCZOWE) ---
    JOURNAL_KEYWORDS_BAD = ["panic", "fomo", "revenge", "zemsta", "błąd", "chciwość", "strach"]
    JOURNAL_KEYWORDS_GOOD = ["plan", "zgodnie", "sl", "tp", "strategy", "strategia"]

    # --- FLAVOR TEXT (WIADOMOŚCI MOTYWACYJNE) ---
    # Wiadomości motywacyjne wyświetlane przy logowaniu wyniku, w zależności od poziomu (Level < X)
    MOTIVATIONAL_MESSAGES: List[Tuple[int, str]] = [
        (5, "\n\n💡 *Tip:* Pamiętaj o Stop Lossie. Ochrona kapitału to priorytet."),
        (10, "\n\n👊 Dobra robota. Budujesz nawyki."),
        (20, "\n\n📈 Twoja dyscyplina procentuje.")
    ]

# -----------------------------------------------------------------------------
# 2. KONFIGURACJA SENTYMENTU I RYZYKA (MFI / GTI)
# -----------------------------------------------------------------------------
class SentimentConstants:
    """
    Stałe i progi dla modułu analizy sentymentu.
    Definiuje progi MFI (Market Fear Index) i GTI (Global Tension Index).
    """
    # Cache
    CACHE_DURATION_SECONDS = 900  # 15 minut (dane nie zmieniają się co sekundę)

    # Market Fear Index (MFI) - Progi
    # Skala 0-100
    MFI_THRESHOLDS = {
        "low": 25,    # Poniżej 25: Niski strach (Complacency)
        "medium": 50, # 25-50: Umiarkowany
        "high": 75,   # 50-75: Wysoki strach
        "extreme": 75 # Powyżej 75: Ekstremalny strach (Panika)
    }

    # Global Tension Index (GTI) - Progi
    # Skala 0-100
    GTI_THRESHOLDS = {
        "low": 30,    # Poniżej 30: Spokój
        "medium": 50, # 30-50: Podwyższone napięcie
        "high": 75,   # 50-75: Napięty
        "extreme": 75 # Powyżej 75: Krytyczny
    }

    # Wagi scoringowe dla MFI
    VIX_WEIGHTS = {
        "low": 5,     # VIX < 12
        "normal": 25, # VIX 12-20
        "fear": 60,   # VIX 20-30
        "panic": 90   # VIX > 30
    }

# -----------------------------------------------------------------------------
# 3. KONFIGURACJA NEWSÓW I KALENDARZA
# -----------------------------------------------------------------------------
class NewsConstants:
    """
    Konfiguracja klienta newsów ekonomicznych.
    Określa częstotliwość aktualizacji i wpływ newsów na scoring.
    """
    UPDATE_INTERVAL_HOURS = 4     # Co ile godzin pobierać kalendarz
    HIGH_IMPACT_LOOKAHEAD_MIN = 60 # Ile minut w przód szukamy newsów High Impact
    IMPACT_PENALTY_POINTS = 20    # Ile punktów MFI/GTI dodawać za High Impact News

# -----------------------------------------------------------------------------
# 4. KONFIGURACJA ŚCIEŻEK (PATHS)
# -----------------------------------------------------------------------------
class Paths:
    """
    Centralna konfiguracja ścieżek do plików i katalogów.
    Ułatwia zarządzanie lokalizacją danych w jednym miejscu.
    """
    # Katalogi główne (względem root projektu)
    DATA_DIR = Path("app/data")
    TRADES_DIR = Path("trades")
    
    # Pliki danych
    USER_PROFILE = DATA_DIR / "user_profile.json"
    ECONOMIC_CALENDAR = DATA_DIR / "economic_calendar.json"
    ALERTS_CONFIG = DATA_DIR / "alerts_config.json"
    ACTIVE_TRADES = DATA_DIR / "active_trades.json"
    NEWS_CACHE = DATA_DIR / "news_cache.json"
    ECONOMIC_HISTORY = DATA_DIR / "economic_history.json"

# -----------------------------------------------------------------------------
# 5. GŁÓWNA KLASA KONFIGURACYJNA (RUNTIME)
# -----------------------------------------------------------------------------
@dataclass
class Config:
    """
    Główna klasa konfiguracyjna, ładowana ze zmiennych środowiskowych (.env).
    """
    environment: str          # 'production' lub 'practice'
    telegram_bot_token: str   # Token bota Telegrama
    telegram_chat_id: str     # ID chatu admina (dla powiadomień)
    mode: str                 # 'advisor' (doradca) lub 'auto' (automat - ostrożnie!)
    
    # Źródło danych
    data_source: str          # 'yahoo' (darmowe) lub inne
    instruments: List[str]    # Lista symboli do handlu/analizy
    timeframe: str            # Główny interwał (np. 'H1', 'M15')
    
    # Parametry techniczne
    data_poll_interval_seconds: float # Co ile sekund sprawdzać cenę
    
    # Zarządzanie kapitałem (Risk Management)
    base_currency: str               # Waluta konta (np. USD)
    risk_per_trade_percent: float    # Ryzyko na trade (np. 1.0 = 1%)
    max_trades_per_day: int          # Limit trade'ów dziennie (Safety)
    max_trades_per_instrument_per_day: int # Limit na instrument
    
    # ML / AI
    ml_base_url: str          # Adres serwera ML (opcjonalne)
    
    # Edukacja
    educational_mode: bool    # Czy tryb edukacyjny jest włączony (True/False)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Tworzy instancję konfiguracji na podstawie zmiennych środowiskowych.
        Obsługuje plik .env oraz opcjonalny local_config.json.
        Rozwiązuje listę instrumentów na podstawie podanych symboli lub sekcji.
        """
        load_dotenv()
        local_config: Dict[str, Any] = {}
        local_path = Path("local_config.json")
        if local_path.exists():
            try:
                local_config = json.loads(local_path.read_text(encoding="utf-8"))
            except Exception:
                local_config = {}

        def get_str(name: str, default: str) -> str:
            value = local_config.get(name)
            if isinstance(value, str) and value:
                return value
            return os.environ.get(name, default)

        def get_float(name: str, default: str) -> float:
            value = local_config.get(name)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
            return float(os.environ.get(name, default))

        def get_int(name: str, default: str) -> int:
            value = local_config.get(name)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
            return int(os.environ.get(name, default))

        environment = get_str("ENVIRONMENT", "practice")
        mode = get_str("MODE", "advisor")
        data_source = get_str("DATA_SOURCE", "yahoo")
        instruments_env = get_str("INSTRUMENTS", "")
        sections_env = get_str("INSTRUMENT_SECTIONS", "")
        
        # Parsowanie listy instrumentów
        if instruments_env and instruments_env.strip():
            instruments = [i.strip() for i in instruments_env.split(",") if i.strip()]
        elif sections_env and sections_env.strip():
            instruments = []
            section_names = [s.strip() for s in sections_env.split(",") if s.strip()]
            for name in section_names:
                instruments.extend(INSTRUMENT_SECTIONS.get(name, []))
        else:
            if data_source == "yahoo":
                instruments = list(DEFAULT_INSTRUMENT_UNIVERSE)
                # Ensure we log this fallback or at least return non-empty if default is populated
            else:
                instruments = ["EUR_USD"] # Fallback

        return cls(
            environment=environment,
            telegram_bot_token=get_str("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=get_str("TELEGRAM_CHAT_ID", ""),
            mode=mode,
            data_source=data_source,
            instruments=instruments,
            timeframe=get_str("TIMEFRAME", "H1"),
            data_poll_interval_seconds=get_float("DATA_POLL_INTERVAL_SECONDS", "60"),
            base_currency=get_str("BASE_CURRENCY", "USD"),
            risk_per_trade_percent=get_float("RISK_PER_TRADE_PERCENT", "1.0"),
            max_trades_per_day=get_int("MAX_TRADES_PER_DAY", "10"),
            max_trades_per_instrument_per_day=get_int("MAX_TRADES_PER_INSTRUMENT_PER_DAY", "3"),
            ml_base_url=get_str("ML_BASE_URL", ""),
            educational_mode=get_str("EDUCATIONAL_MODE", "true").lower() == "true",
        )
