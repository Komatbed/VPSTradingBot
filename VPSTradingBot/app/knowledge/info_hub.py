# =============================================================================
# INFO HUB (CENTRUM INFORMACJI)
# =============================================================================
# Moduł zawierający ciekawostki i fakty o świecie finansów (Geopolityka, Ekonomia).
# Służy do budowania kontekstu rynkowego u użytkownika (dlaczego rynek się rusza?).
#
# Elementy (InfoBit) są losowane i prezentowane użytkownikowi jako "Czy wiesz, że...".
# =============================================================================
from dataclasses import dataclass
from typing import List, Optional
import random

@dataclass
class InfoBit:
    category: str
    title: str
    content: str  # 30-60 second read
    source: Optional[str] = None

class InfoHub:
    def __init__(self):
        self._bits: List[InfoBit] = [
            InfoBit(
                category="Geopolityka",
                title="Cieśnina Ormuz",
                content="To najważniejszy punkt przesyłu ropy na świecie. Przepływa przez nią około 20% światowego zapotrzebowania na ropę. Jakiekolwiek napięcia w tym rejonie (Iran/USA) natychmiast windują ceny ropy (OIL/WTI) i często umacniają dolara (bezpieczna przystań).",
            ),
            InfoBit(
                category="Ekonomia",
                title="Stopy procentowe a Waluty",
                content="Gdy bank centralny podnosi stopy procentowe, waluta zazwyczaj się umacnia, bo inwestorzy szukają wyższego zwrotu z obligacji. Obniżka stóp osłabia walutę. To dlatego decyzje FED (USA) czy EBC (Europa) powodują tak duże ruchy na EURUSD.",
            ),
            InfoBit(
                category="Historia Rynków",
                title="Tulipomania (1637)",
                content="Pierwsza odnotowana bańka spekulacyjna w historii. W Holandii ceny cebulek tulipanów osiągały wartość domów, by potem spaść do zera. Lekcja: Rynek potrafi być irracjonalny dłużej, niż Ty potrafisz pozostać wypłacalny.",
            ),
            InfoBit(
                category="Psychologia",
                title="Efekt Potwierdzenia",
                content="Mózg szuka informacji, które potwierdzają Twoją tezę (np. że cena wzrośnie), a ignoruje sygnały ostrzegawcze. To pułapka! Zawsze zadawaj sobie pytanie: 'Co musiałoby się stać, żebym uznał, że się mylę?'.",
            ),
            InfoBit(
                category="Makroekonomia",
                title="PKB (GDP)",
                content="Produkt Krajowy Brutto to suma wartości wszystkich dóbr i usług wytworzonych w kraju. Wysoki wzrost PKB = silna gospodarka = zazwyczaj silna waluta i rosnące giełdy. Spadek PKB przez 2 kwartały z rzędu to techniczna recesja.",
            ),
             InfoBit(
                category="Surowce",
                title="Złoto (XAUUSD) jako Safe Haven",
                content="Złoto nie generuje odsetek, więc traci na atrakcyjności, gdy stopy procentowe są wysokie. Jednak w czasach strachu (wojna, krach, inflacja), kapitał ucieka do złota, traktując je jako 'bezpieczną przystań' trzymającą wartość.",
            ),
        ]

    def get_random_bit(self) -> InfoBit:
        return random.choice(self._bits)

    def get_bit_by_category(self, category: str) -> Optional[InfoBit]:
        filtered = [b for b in self._bits if b.category.lower() == category.lower()]
        return random.choice(filtered) if filtered else None

    def get_all_categories(self) -> List[str]:
        return list(set(b.category for b in self._bits))
from dataclasses import dataclass
from typing import List, Optional
import random

@dataclass
class InfoBit:
    category: str
    title: str
    content: str  # 30-60 second read
    source: Optional[str] = None

class InfoHub:
    def __init__(self):
        self._bits: List[InfoBit] = [
            InfoBit(
                category="Geopolityka",
                title="Cieśnina Ormuz",
                content="To najważniejszy punkt przesyłu ropy na świecie (20% globalnego popytu). Napięcia tutaj = wzrost cen ropy (OIL) i dolara (USD) jako bezpiecznej przystani.",
            ),
            InfoBit(
                category="Ekonomia",
                title="Stopy procentowe a Waluty",
                content="Wyższe stopy = wyższy zwrot z obligacji = napływ kapitału = silniejsza waluta. Decyzje FED/EBC to główne motory trendów na EURUSD.",
            ),
            InfoBit(
                category="Psychologia",
                title="Efekt Potwierdzenia",
                content="Mózg ignoruje sygnały przeczące Twojej tezie. Zadaj sobie pytanie: 'Co musiałoby się stać, żebym uznał, że się mylę?'.",
            ),
             InfoBit(
                category="Surowce",
                title="Złoto (XAU) vs Realne Stopy",
                content="Złoto nie płaci odsetek. Gdy realne stopy procentowe (stopy - inflacja) rosną, złoto traci. Gdy spadają (lub jest wojna), złoto zyskuje.",
            ),
        ]

    def get_random_bit(self) -> InfoBit:
        return random.choice(self._bits)