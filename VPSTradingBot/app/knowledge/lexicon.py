# =============================================================================
# LEKSYKON TRADERA (TRADING LEXICON)
# =============================================================================
# Słownik pojęć tradingowych używany przez komendę /learn <hasło>.
#
# Format: KLUCZ (wielkie litery): "Definicja w Markdown".
# Definicje powinny być krótkie (max 30-60s czytania) i praktyczne.
# =============================================================================
from typing import Dict

LEXICON: Dict[str, str] = {
    "R:R": (
        "**Risk to Reward Ratio (R:R)**\n"
        "Stosunek ryzyka do potencjalnego zysku. Np. R:R 1:3 oznacza, że ryzykujesz 1 jednostkę (np. 100 zł), "
        "aby zarobić 3 jednostki (300 zł). W tym systemie szukamy setupów z R:R minimum 1:2."
    ),
    "RSI": (
        "**Relative Strength Index (RSI)**\n"
        "Wskaźnik określający siłę trendu i momenty zwrotne.\n"
        "🔸 RSI > 70: Rynek wykupiony (potencjalne spadki).\n"
        "🔸 RSI < 30: Rynek wyprzedany (potencjalne wzrosty).\n"
        "🔸 40-60: Strefa neutralna/kontynuacji trendu."
    ),
    "SMA/EMA": (
        "**Średnie Kroczące (SMA/EMA)**\n"
        "Linie pokazujące średnią cenę z X ostatnich świec.\n"
        "🔸 SMA: Prosta średnia.\n"
        "🔸 EMA: Średnia wykładnicza (większa waga ostatnich cen).\n"
        "Służą do określania trendu (cena nad średnią = trend wzrostowy)."
    ),
    "PINBAR": (
        "**Pinbar**\n"
        "Świeca z długim cieniem i małym korpusem. Sygnalizuje odrzucenie ceny.\n"
        "🔸 Długi dolny cień: Odrzucenie spadków (sygnał na wzrosty).\n"
        "🔸 Długi górny cień: Odrzucenie wzrostów (sygnał na spadki)."
    ),
    "TREND": (
        "**Trend**\n"
        "Kierunek, w którym podąża rynek.\n"
        "🔸 Wzrostowy (Bullish): Wyższe szczyty i wyższe dołki.\n"
        "🔸 Spadkowy (Bearish): Niższe szczyty i niższe dołki.\n"
        "🔸 Boczny (Konsolidacja): Cena porusza się w kanale poziomym."
    ),
    "ZMIENNOŚĆ": (
        "**Zmienność (Volatility)**\n"
        "Miara tego, jak mocno i szybko zmienia się cena.\n"
        "Wysoka zmienność daje szansę na duże zyski, ale niesie większe ryzyko. "
        "Niska zmienność (konsolidacja) jest często trudna do handlowania strategiami trendowymi."
    ),
    "REGIM RYNKOWY": (
        "**Regim Rynkowy**\n"
        "Ogólny stan zachowania rynku. System rozpoznaje:\n"
        "• TREND: Silny ruch kierunkowy.\n"
        "• RANGING: Trend boczny/konsolidacja.\n"
        "• HIGH_VOLATILITY: Chaos/duże skoki cenowe (ryzykowne).\n"
        "Strategie są dobierane pod aktualny regim."
    ),
    "SPREAD": (
        "**Spread**\n"
        "Różnica między ceną kupna (Ask) a ceną sprzedaży (Bid).\n"
        "To główny koszt transakcji u brokera. Im niższy spread, tym łatwiej o zysk (szczególnie w scalpingu)."
    ),
    "LONG/SHORT": (
        "**Long vs Short**\n"
        "• Long (Długa): Kupujesz, licząc na wzrost ceny.\n"
        "• Short (Krótka): Sprzedajesz, licząc na spadek ceny (zarabiasz, gdy rynek leci w dół)."
    ),
    "LEWAR": (
        "**Dźwignia (Lewar)**\n"
        "Mechanizm pozwalający inwestować więcej niż masz na koncie. Np. Dźwignia 1:30 oznacza, że mając 1000 zł, kontrolujesz pozycję wartą 30 000 zł.\n"
        "⚠️ Zwiększa zyski, ale też drastycznie zwiększa ryzyko szybkich strat."
    ),
    "FVG": (
        "**Fair Value Gap (FVG)**\n"
        "Nierównowaga cenowa (Imbalance). Luka między cieniem pierwszej a trzeciej świecy w silnym ruchu.\n"
        "Cena często wraca do FVG, aby 'wypełnić' lukę przed kontynuacją ruchu. To świetne miejsce na wejście (tzw. retest)."
    ),
    "ORDER BLOCK": (
        "**Order Block (OB)**\n"
        "Ostatnia świeca przeciwna do ruchu przed silnym impulsem (np. ostatnia spadkowa przed wystrzałem w górę).\n"
        "To tutaj instytucje (Smart Money) składały swoje zlecenia. Cena często reaguje po powrocie do tej strefy."
    ),
    "LIQUIDITY": (
        "**Płynność (Liquidity)**\n"
        "Miejsca, gdzie 'leżą pieniądze' (Stop Lossy detalistów). Zazwyczaj powyżej wyraźnych szczytów lub poniżej dołków.\n"
        "Rynek często fałszywie przebija te poziomy (Liquidity Grab), aby zebrać zlecenia i ruszyć w przeciwną stronę."
    ),
    "SŁOWNIK": (
        "**Dostępne hasła:**\n"
        "🔸 R:R\n"
        "🔸 RSI\n"
        "🔸 SMA/EMA\n"
        "🔸 PINBAR\n"
        "🔸 TREND\n"
        "🔸 ZMIENNOŚĆ\n"
        "🔸 REGIM RYNKOWY\n"
        "🔸 SPREAD\n"
        "🔸 LONG/SHORT\n"
        "🔸 LEWAR\n"
        "🔸 FVG (Smart Money)\n"
        "🔸 ORDER BLOCK (Smart Money)\n"
        "🔸 LIQUIDITY (Smart Money)\n\n"
        "Wpisz `/learn <hasło>` aby poznać szczegóły."
    )
}

TRADING_TIPS: Dict[str, str] = {
    "1": "Nigdy nie ryzykuj więcej niż ustalone w planie (np. 1-2% kapitału na transakcję).",
    "2": "Nie goń rynku (FOMO). Jeśli przegapiłeś wejście, czekaj na kolejną okazję.",
    "3": "Prowadź dziennik transakcyjny. Analiza błędów to najszybsza droga do nauki.",
    "4": "Trend is your friend. Łatwiej zarobić grając z trendem niż łapiąc szczyty/dołki.",
    "5": "Cierpliwość to 90% tradingu. Czekaj na setup A+.",
}