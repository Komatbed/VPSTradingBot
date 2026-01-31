# =============================================================================
# KNOWLEDGE CARDS (KARTY WIEDZY)
# =============================================================================
# Ten plik zawiera "Karty Wiedzy" - krótkie, skoncentrowane dawki edukacji
# na temat psychologii, zarządzania ryzykiem i procesów tradingowych.
#
# Każda karta (KnowledgeCard) składa się z:
# - Tematu (topic)
# - Definicji (definition)
# - Dlaczego to ważne (importance)
# - Przykładu (example)
#
# Karty są losowane w ramach grywalizacji lub na żądanie użytkownika.
# Dodawaj nowe karty w klasie KnowledgeDeck.
# =============================================================================
from dataclasses import dataclass
from typing import List, Optional
import random

@dataclass
class KnowledgeCard:
    topic: str
    definition: str
    importance: str
    example: str

class KnowledgeDeck:
    def __init__(self):
        self._cards: List[KnowledgeCard] = [
            KnowledgeCard(
                topic="Risk to Reward (R:R)",
                definition="Stosunek potencjalnej straty do zysku w transakcji.",
                importance="Pozwala być zyskownym nawet przy skuteczności < 50%. Bez R:R > 1:2 trading to matematyczne samobójstwo.",
                example="Ryzykujesz 100 zł (SL), aby zarobić 300 zł (TP). R:R = 1:3."
            ),
            KnowledgeCard(
                topic="FOMO (Fear Of Missing Out)",
                definition="Strach przed uciekającą okazją, prowadzący do impulsywnych wejść.",
                importance="To główny zabójca kont. Rynek zawsze da kolejną okazję.",
                example="Cena rośnie pionowo. Wskakujesz na szczycie bez planu, bo 'ucieka'. Cena zawraca. Tracisz."
            ),
            KnowledgeCard(
                topic="Stop Loss (SL)",
                definition="Zlecenie obronne zamykające stratną pozycję.",
                importance="To Twój pas bezpieczeństwa i koszt prowadzenia biznesu. Brak SL = bankructwo (kwestia czasu).",
                example="Kupujesz po 100. SL na 90. Jeśli cena spadnie do 90, system automatycznie ucina stratę 10."
            ),
            KnowledgeCard(
                topic="Trend is your friend",
                definition="Zasada podążania za głównym kierunkiem rynku.",
                importance="Płynięcie z prądem jest łatwiejsze. Kontrariańskie łapanie dołków ma niskie prawdopodobieństwo.",
                example="Na wykresie D1 są coraz wyższe szczyty. Nie szortuj, szukaj okazji do kupna na korektach."
            ),
            KnowledgeCard(
                topic="Overtrading",
                definition="Zbyt częste zawieranie transakcji lub zbyt duży wolumen.",
                importance="Prowadzi do zmęczenia, błędów i prowizji zjadających zysk. Mniej znaczy więcej.",
                example="Po stratnym dniu otwierasz 10 szybkich pozycji, żeby 'się odkuć'. Kończysz z 2x większą stratą."
            ),
            KnowledgeCard(
                topic="Dźwignia Finansowa",
                definition="Mechanizm pozwalający inwestować więcej niż masz kapitału.",
                importance="Dźwignia to miecz obosieczny. Zwiększa zyski, ale też straty. Nieumiejętne użycie = Margin Call.",
                example="Dźwignia 1:10. Ruch ceny o 1% zmienia stan Twojego konta o 10%."
            ),
            KnowledgeCard(
                topic="Kapitał Emocjonalny",
                definition="Zasób psychicznej energii do podejmowania racjonalnych decyzji.",
                importance="Gdy jesteś zmęczony, zły lub euforczyny, Twój kapitał emocjonalny jest niski. Wtedy robisz błędy.",
                example="Po serii strat czujesz chęć 'odegrania się'. To sygnał, że Twój kapitał emocjonalny się wyczerpał. Odejdź od komputera."
            )
        ]

    def draw_card(self) -> KnowledgeCard:
        return random.choice(self._cards)
from dataclasses import dataclass
from typing import List, Optional
import random

@dataclass
class KnowledgeCard:
    topic: str
    definition: str
    importance: str
    example: str

class KnowledgeDeck:
    def __init__(self):
        self._cards: List[KnowledgeCard] = [
            KnowledgeCard(
                topic="Risk to Reward (R:R)",
                definition="Stosunek potencjalnej straty do zysku w transakcji.",
                importance="Pozwala być zyskownym nawet przy skuteczności < 50%. Bez R:R > 1:2 trading to matematyczne samobójstwo.",
                example="Ryzykujesz 100 zł (SL), aby zarobić 300 zł (TP). R:R = 1:3."
            ),
            KnowledgeCard(
                topic="FOMO (Fear Of Missing Out)",
                definition="Strach przed uciekającą okazją, prowadzący do impulsywnych wejść.",
                importance="To główny zabójca kont. Rynek zawsze da kolejną okazję.",
                example="Cena rośnie pionowo. Wskakujesz na szczycie bez planu, bo 'ucieka'. Cena zawraca. Tracisz."
            ),
            KnowledgeCard(
                topic="Stop Loss (SL)",
                definition="Zlecenie obronne zamykające stratną pozycję.",
                importance="To Twój pas bezpieczeństwa i koszt prowadzenia biznesu. Brak SL = bankructwo (kwestia czasu).",
                example="Kupujesz po 100. SL na 90. Jeśli cena spadnie do 90, system automatycznie ucina stratę 10."
            ),
            KnowledgeCard(
                topic="Trend is your friend",
                definition="Zasada podążania za głównym kierunkiem rynku.",
                importance="Płynięcie z prądem jest łatwiejsze. Kontrariańskie łapanie dołków ma niskie prawdopodobieństwo.",
                example="Na wykresie D1 są coraz wyższe szczyty. Nie szortuj, szukaj okazji do kupna na korektach."
            ),
            KnowledgeCard(
                topic="Overtrading",
                definition="Zbyt częste zawieranie transakcji lub zbyt duży wolumen.",
                importance="Prowadzi do zmęczenia, błędów i prowizji zjadających zysk. Mniej znaczy więcej.",
                example="Po stratnym dniu otwierasz 10 szybkich pozycji, żeby 'się odkuć'. Kończysz z 2x większą stratą."
            )
        ]

    def draw_card(self) -> KnowledgeCard:
        return random.choice(self._cards)