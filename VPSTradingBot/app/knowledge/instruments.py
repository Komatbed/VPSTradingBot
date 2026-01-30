# =============================================================================
# KATALOG INSTRUMENTÓW (INSTRUMENT CATALOG)
# =============================================================================
# Baza wiedzy o instrumentach finansowych handlowanych przez bota.
#
# Zawiera definicje manualne dla kluczowych aktywów oraz mechanizm 
# automatycznego generowania opisów na podstawie metadanych (Sektor/Typ).
# =============================================================================
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# Import metadanych z universe (musi być dostępny w ścieżce)
try:
    from app.data.instrument_universe import INSTRUMENT_METADATA
except ImportError:
    INSTRUMENT_METADATA = {}  # Fallback dla testów jednostkowych bez kontekstu app

@dataclass
class InstrumentInfo:
    symbol: str
    name: str
    asset_type: str  # Index, Stock, Forex, Commodity, Crypto, ETF
    description: str
    influences: List[str]
    volatility: str  # Low, Medium, High + context
    correlations: List[str]
    trading_tips: str
    
    # Rozszerzone pola dla Encyklopedii
    history: str = "Historia tego instrumentu jest w trakcie opracowywania."
    evolution: str = "Ewolucja instrumentu nie została jeszcze opisana."
    key_features: List[str] = field(default_factory=list)
    
    # Opcjonalne
    sector: Optional[str] = None
    components: Optional[List[str]] = None  # Dla indeksów
    
    # Nowe szczegółowe pola (Mała Wikipedia)
    founding_year: str = "Brak danych"
    company_size: str = "Brak danych"  # np. Market Cap, liczba pracowników
    products: List[str] = field(default_factory=list)  # np. iPhone, Kredyt Hipoteczny
    famous_for: str = "Brak danych"  # np. "Logo z Żubrem", "Rewolucja EV"

    def to_telegram_markdown(self) -> str:
        lines = [
            f"📘 **INSTRUMENT INFO** | {self.symbol}",
            f"🏷️ **Nazwa:** {self.name}",
            f"🧩 **Typ:** {self.asset_type}",
            "",
            f"📝 **Opis:**\n{self.description}",
            "",
            f"📜 **Historia:**\n{self.history[:200]}..." if len(self.history) > 200 else f"📜 **Historia:**\n{self.history}",
            "",
            "🌍 **Co na niego wpływa:**"
        ]
        for inf in self.influences:
            lines.append(f"🔸 {inf}")
            
        lines.append(f"\n📊 **Zmienność:** {self.volatility}")
        
        if self.key_features:
             lines.append("\n🔑 **Kluczowe cechy:**")
             for kf in self.key_features:
                 lines.append(f"🔸 {kf}")

        if self.correlations:
            lines.append(f"\n🔗 **Powiązania:**\n{', '.join(self.correlations)}")
            
        if self.evolution and len(self.evolution) > 10:
             lines.append(f"\n📈 **Ewolucja:**\n{self.evolution[:200]}...")

        if self.components:
            lines.append(f"\n🏗 **Skład:** {', '.join(self.components[:5])}...")
            
        lines.append(f"\n💡 **Zastosowanie w tradingu:**\n{self.trading_tips}")
        return "\n".join(lines)

# =============================================================================
# WIEDZA SEKTOROWA (TEMPLATE DLA AUTOMATYCZNYCH OPISÓW)
# =============================================================================
SECTOR_KNOWLEDGE = {
    "Usługi Finansowe": {
        "desc": "Podmiot działający w sektorze finansowym (banki, ubezpieczenia, zarządzanie aktywami). Kluczowy dla przepływu kapitału w gospodarce.",
        "influences": ["Stopy procentowe (marża odsetkowa)", "Koniunktura gospodarcza (ryzyko kredytowe)", "Regulacje KNF/EBC/FED"],
        "volatility": "Średnia (wrażliwa na cykle makroekonomiczne)",
        "tips": "Sektor cykliczny. Banki zyskują w środowisku wysokich stóp procentowych. Uważaj na raporty kwartalne i dywidendy.",
        "products": ["Kredyty hipoteczne", "Konta osobiste", "Ubezpieczenia", "Leasing", "Obsługa firm"]
    },
    "Energetyka": {
        "desc": "Spółka zajmująca się wytwarzaniem, dystrybucją lub obrotem energią (konwencjonalną lub OZE). Strategiczny sektor dla gospodarki.",
        "influences": ["Ceny surowców energetycznych (węgiel, gaz)", "Ceny uprawnień do emisji CO2", "Polityka klimatyczna (Zielony Ład)"],
        "volatility": "Średnia / Wysoka (ryzyko polityczne i regulacyjne)",
        "tips": "Często spółki dywidendowe (Value). Wrażliwe na decyzje polityczne i zmiany taryf energetycznych.",
        "products": ["Energia elektryczna", "Ciepło systemowe", "Dystrybucja prądu", "OZE (Wiatr/Solar)"]
    },
    "Paliwa": {
        "desc": "Koncern paliwowo-energetyczny. Zajmuje się wydobyciem, rafinacją i sprzedażą ropy oraz gazu.",
        "influences": ["Ceny ropy naftowej (Brent/WTI)", "Kurs dolara (USD)", "Marże rafineryjne"],
        "volatility": "Wysoka (zależna od cen surowców)",
        "tips": "Silna korelacja z ceną ropy. Dobre zabezpieczenie przed inflacją w portfelu długoterminowym.",
        "products": ["Benzyna/Diesel", "Paliwo lotnicze", "Asfalt", "Produkty petrochemiczne"]
    },
    "Gaming": {
        "desc": "Producent lub wydawca gier wideo. Sektor łączy technologię z rozrywką i sztuką.",
        "influences": ["Premiery nowych gier (cykl produkcyjny)", "Sentyment graczy i recenzje (Metacritic)", "Kurs dolara (eksport)"],
        "volatility": "Bardzo Wysoka (skokowa zmienność pod premiery)",
        "tips": "Handel 'pod wydarzenia' (premiery). Ryzykowne utrzymywanie pozycji przez premiery (sell the news).",
        "products": ["Gry PC/Konsole", "Gry Mobilne", "Mikrotransakcje", "DLC"]
    },
    "IT": {
        "desc": "Spółka technologiczna oferująca oprogramowanie, usługi IT lub sprzęt. Sektor wzrostowy (Growth).",
        "influences": ["Popyt na cyfryzację i chmurę", "Koszty pracy (wynagrodzenia programistów)", "Kursy walut (eksport usług)"],
        "volatility": "Wysoka (duże beta względem rynku)",
        "tips": "Liderzy hossy. Wrażliwe na wzrost rentowności obligacji (wyższe stopy szkodzą wycenom Growth).",
        "products": ["Oprogramowanie (SaaS)", "Usługi chmurowe", "Konsulting IT", "Sprzęt komputerowy"]
    },
    "Surowce": {
        "desc": "Spółka wydobywcza (górnictwo). Zależna od cykli koniunkturalnych i popytu przemysłowego.",
        "influences": ["Ceny metali/surowców na rynkach światowych", "Kurs dolara (USD)", "Popyt z Chin"],
        "volatility": "Wysoka (cykliczna)",
        "tips": "Inwestycja w surowce to często gra na osłabienie dolara lub wzrost inflacji.",
        "products": ["Miedź", "Węgiel koksowy", "Stal", "Metale ziem rzadkich"]
    },
    "Handel": {
        "desc": "Sieć handlowa detaliczna lub hurtowa. Biznes oparty na skali i marży obrotowej.",
        "influences": ["Nastroje konsumenckie (sprzedaż detaliczna)", "Inflacja (koszty vs ceny)", "Płaca minimalna"],
        "volatility": "Średnia (sektor defensywny w przypadku dóbr podstawowych)",
        "tips": "Obserwuj dane o sprzedaży detalicznej. Spółki te często rosną stabilnie w czasach dobrej koniunktury.",
        "products": ["Artykuły spożywcze", "Odzież i obuwie", "Elektronika", "E-commerce"]
    },
    "Budownictwo": {
        "desc": "Firma budowlana lub deweloperska. Realizuje projekty infrastrukturalne lub mieszkaniowe.",
        "influences": ["Inwestycje publiczne (KPO, fundusze UE)", "Stopy procentowe (kredyty hipoteczne)", "Ceny materiałów budowlanych"],
        "volatility": "Wysoka (ryzyko kontraktowe)",
        "tips": "Sektor mocno cykliczny. Zależny od odblokowania środków unijnych i koniunktury na rynku nieruchomości.",
        "products": ["Mieszkania", "Drogi i mosty", "Budownictwo przemysłowe", "Materiały budowlane"]
    },
    "Crypto": {
        "desc": "Aktywo cyfrowe oparte na technologii blockchain. Nowa klasa aktywów alternatywnych.",
        "influences": ["Sentyment Risk-On/Risk-Off", "Regulacje (SEC, MiCA)", "Adopcja instytucjonalna"],
        "volatility": "Ekstremalnie Wysoka",
        "tips": "Tylko dla kapitału spekulacyjnego. Ogromne ryzyko, ale też potencjał stóp zwrotu niemożliwy na tradycyjnych rynkach.",
        "products": ["Transfer wartości", "Smart Contracts", "DeFi", "NFT"]
    },
    "Biotechnologia": {
        "desc": "Spółka pracująca nad nowymi lekami lub technologiami medycznymi. Sektor wysokiego ryzyka i wysokiej nagrody.",
        "influences": ["Wyniki badań klinicznych", "Decyzje FDA/EMA", "Partnerstwa z Big Pharma"],
        "volatility": "Bardzo Wysoka (binarne reakcje na wyniki badań)",
        "tips": "Handel newsowy. Często jedna informacja decyduje o być albo nie być spółki.",
        "products": ["Leki innowacyjne", "Terapie genowe", "Szczepionki", "Urządzenia medyczne"]
    }
}

# Domyślny template dla nieznanych sektorów
DEFAULT_TEMPLATE = {
    "desc": "Instrument finansowy notowany na rynku publicznym.",
    "influences": ["Sentyment rynkowy", "Ogólna kondycja gospodarki"],
    "volatility": "Zmienna",
    "tips": "Stosuj zasady zarządzania ryzykiem. Analizuj trend i wolumen."
}

# =============================================================================
# KATALOG MANUALNY (Szczegółowe opisy dla najważniejszych)
# =============================================================================
INSTRUMENT_CATALOG: Dict[str, InstrumentInfo] = {
    # --- INDEKSY ---
    "NASDAQ": InstrumentInfo(
        symbol="^NDX", name="NASDAQ 100", asset_type="Indeks (US)", sector="Indeks",
        description="Indeks 100 największych spółek technologicznych w USA (bez finansów).",
        influences=["Stopy procentowe USA", "Wyniki spółek Tech", "Risk-On/Off"],
        volatility="Średnia/Wysoka", correlations=["S&P 500", "BTC"],
        trading_tips="Lider hossy. Kupuj w korektach w silnym trendzie wzrostowym.",
        history="Uruchomiony w 1985 roku (NASDAQ-100). Stał się symbolem rewolucji cyfrowej i bańki dot-com.",
        evolution="Od parkietu dla ryzykownych spółek do dominującego indeksu globalnej gospodarki cyfrowej.",
        key_features=["Dominacja Tech", "Wysoka płynność", "Brak sektora finansowego"],
        founding_year="1971 (giełda), 1985 (indeks)",
        company_size="Kapitalizacja spółek > 20 bln USD",
        products=["Indeks giełdowy", "Futures (NQ)", "Opcje", "ETFs (QQQ)"],
        famous_for="Dom dla Apple, Microsoft, NVIDIA i innych gigantów technologicznych."
    ),
    "SPX": InstrumentInfo(
        symbol="^GSPC", name="S&P 500", asset_type="Indeks (US)", sector="Indeks",
        description="Benchmark amerykańskiej gospodarki (500 największych spółek).",
        influences=["Makroekonomia USA", "Polityka FED"],
        volatility="Średnia", correlations=["VIX (odwrotna)"],
        trading_tips="Najlepszy do długoterminowego trendu i strategii Mean Reversion.",
        history="Stworzony przez Standard & Poor's w 1957 roku. Zastąpił wcześniejsze węższe indeksy.",
        evolution="Stały wzrost znaczenia spółek technologicznych kosztem przemysłu i energii.",
        key_features=["Dywersyfikacja", "Reprezentatywność", "Standard inwestycyjny"],
        founding_year="1957",
        company_size="Kapitalizacja > 40 bln USD",
        products=["Indeks giełdowy", "Futures (ES)", "ETFs (SPY, VOO)"],
        famous_for="Najważniejszy barometr kondycji gospodarki USA i świata."
    ),

    # --- POLSKA (WIG20 GIANTS) ---
    "PKO.WA": InstrumentInfo(
        symbol="PKO.WA", name="PKO Bank Polski", asset_type="Akcja (PL)", sector="Finanse",
        description="Największy bank uniwersalny w Polsce i Europie Środkowo-Wschodniej. Spółka Skarbu Państwa.",
        influences=["Stopy procentowe NBP (WIBOR)", "Kredyty frankowe (rezerwy)", "Dywidendy"],
        volatility="Średnia", correlations=["WIG20", "WIG-Banki"],
        trading_tips="Kluczowy składnik portfela dywidendowego. Wrażliwy na politykę państwa.",
        history="Założony w 1919 roku dekretem Naczelnika Państwa Józefa Piłsudskiego jako Pocztowa Kasa Oszczędności.",
        evolution="Od książeczek oszczędnościowych do lidera bankowości mobilnej (aplikacja IKO).",
        key_features=["Lider rynku", "Wysoka płynność", "Regularne dywidendy", "Kontrola państwowa"],
        founding_year="1919",
        company_size="Aktywa > 400 mld PLN, Zatrudnienie ~25 tys.",
        products=["Konta osobiste", "Kredyty hipoteczne", "Leasing", "Aplikacja IKO", "Bankowość korporacyjna"],
        famous_for="Logo ze skarbonką (dawniej) i 'PKO Bank Polski' obecnie. Najpopularniejszy bank w Polsce."
    ),
    "PKN.WA": InstrumentInfo(
        symbol="PKN.WA", name="Orlen", asset_type="Akcja (PL)", sector="Paliwa",
        description="Multienerygetyczny koncern (paliwa, gaz, energia, prasa). Największa firma w regionie CEE.",
        influences=["Ceny ropy i gazu", "Marże rafineryjne", "Polityka energetyczna rządu"],
        volatility="Średnia/Wysoka", correlations=["Ropa Brent", "USD/PLN"],
        trading_tips="Gra pod fuzje i przejęcia. Silnie powiązany z polityką.",
        history="Powstał w 1999 roku z fuzji Petrochemii Płock i CPN. W ostatnich latach przejął Energę, Lotos i PGNiG.",
        evolution="Transformacja z firmy paliwowej w koncern multienergetyczny inwestujący w OZE i SMR (mały atom).",
        key_features=["Dominacja w regionie", "Dywersyfikacja biznesu", "Udział Skarbu Państwa", "Sieć stacji paliw"],
        founding_year="1999 (fuzja CPN i Petrochemii)",
        company_size="Przychody > 300 mld PLN, Zatrudnienie > 60 tys.",
        products=["Paliwa (Verva, Efecta)", "Gaz ziemny", "Energia elektryczna", "Hot-dogi na stacjach", "Prasa (Polska Press)"],
        famous_for="Największa firma w Europie Środkowo-Wschodniej. Sponsor F1 (dawniej z Kubicą)."
    ),
    "KGH.WA": InstrumentInfo(
        symbol="KGH.WA", name="KGHM Polska Miedź", asset_type="Akcja (PL)", sector="Surowce",
        description="Jeden z czołowych światowych producentów miedzi i srebra rafinowanego.",
        influences=["Ceny miedzi (LME)", "Ceny srebra", "Kurs USD/PLN", "Podatek miedziowy"],
        volatility="Wysoka", correlations=["Miedź", "Srebro", "Dolar"],
        trading_tips="Czysta ekspozycja na surowce. Kupuj, gdy dolar słabnie, a Chiny stymulują gospodarkę.",
        history="Założony w 1961 roku po odkryciu gigantycznych złóż miedzi na Dolnym Śląsku przez Jana Wyżykowskiego.",
        evolution="Od lokalnej kopalni do globalnego gracza z aktywami w Chile (Sierra Gorda), USA i Kanadzie.",
        key_features=["Globalny gracz", "Wrażliwość walutowa", "Kluczowy eksporter", "Strategiczne znaczenie"],
        founding_year="1961",
        company_size="Zatrudnienie > 30 tys., Produkcja miedzi > 700 tys. ton rocznie",
        products=["Miedź katodowa", "Srebro", "Złoto", "Ołów", "Ren"],
        famous_for="Kombinat Górniczo-Hutniczy. Drugi największy producent srebra na świecie."
    ),
    "CDR.WA": InstrumentInfo(
        symbol="CDR.WA", name="CD Projekt", asset_type="Akcja (PL)", sector="Gaming",
        description="Najsłynniejszy polski producent gier (Wiedźmin, Cyberpunk 2077).",
        influences=["Sprzedaż back-katalogu", "Zapowiedzi nowych gier (Wiedźmin 4)", "Pozycje krótkie funduszy"],
        volatility="Wysoka", correlations=["NASDAQ (sentyment tech)"],
        trading_tips="Spółka 'newsowa'. Reaguje gwałtownie na plotki i zapowiedzi.",
        history="Założona w 1994 roku przez Marcina Iwińskiego i Michała Kicińskiego. Zaczynali od importu gier na giełdę komputerową.",
        evolution="Od dystrybutora i lokalizatora gier (Baldur's Gate) do globalnego dewelopera AAA (Wiedźmin, Cyberpunk).",
        key_features=["Silne IP (Wiedźmin)", "Rozpoznawalność globalna", "Wysokie ryzyko projektowe", "Platforma GOG.com"],
        founding_year="1994",
        company_size="Zatrudnienie > 1000 osób, Kapitalizacja zmienna (top Gamingu)",
        products=["Gra Wiedźmin (seria)", "Cyberpunk 2077", "Platforma GOG.com"],
        famous_for="Stworzenie serii gier o Wiedźminie i jednej z najdroższych gier w historii (Cyberpunk 2077)."
    ),
    "DNP.WA": InstrumentInfo(
        symbol="DNP.WA", name="Dino Polska", asset_type="Akcja (PL)", sector="Handel",
        description="Dynamicznie rozwijająca się sieć marketów spożywczych w Polsce.",
        influences=["Tempo otwarć nowych sklepów", "Inflacja żywności", "Koszty energii i pracy"],
        volatility="Średnia", correlations=["WIG20"],
        trading_tips="Spółka typu Growth. Kupowana dla wzrostu, nie dywidendy. Często droższa niż rynek.",
        history="Założona w 1999 roku przez Tomasza Biernackiego. Pierwszy sklep powstał w Wielkopolsce.",
        evolution="Agresywna ekspansja organiczna. Model biznesowy oparty na własności gruntów i standardowych projektach sklepów.",
        key_features=["Agresywna ekspansja", "Właściciel gruntów i sklepów", "Efektywność operacyjna", "Założyciel-miliarder"],
        founding_year="1999",
        company_size="Liczba sklepów > 2400, Zatrudnienie > 40 tys.",
        products=["Artykuły spożywcze", "Chemia gospodarcza", "Agro-Rydzyna (mięso)"],
        famous_for="Tajemniczy założyciel Tomasz Biernacki i niesamowite tempo otwierania nowych marketów (jeden dziennie)."
    ),
    "PEO.WA": InstrumentInfo(
        symbol="PEO.WA", name="Bank Pekao", asset_type="Akcja (PL)", sector="Finanse",
        description="Drugi największy bank w Polsce, znany z logo żubra.",
        influences=["Stopy procentowe", "Dywidendy", "Kredyty korporacyjne"],
        volatility="Średnia", correlations=["WIG-Banki", "PKO.WA"],
        trading_tips="Solidna spółka dywidendowa. Często porusza się w parze z PKO BP.",
        history="Założony w 1929 roku jako Bank Polska Kasa Opieki, by obsługiwać Polonię.",
        evolution="Powrót w polskie ręce (odkupienie od UniCredit przez PZU/PFR) i silna cyfryzacja (aplikacja PeoPay).",
        key_features=["Marka (Żubr)", "Segment korporacyjny", "Dywidenda", "Private Banking"],
        founding_year="1929",
        company_size="Aktywa > 300 mld PLN, Zatrudnienie ~13 tys.",
        products=["Konta osobiste", "Kredyty firmowe", "Private Banking", "Biuro Maklerskie", "PeoPay"],
        famous_for="Żubr w logo. Obsługa dużych firm i klientów zamożnych."
    ),
    "LPP.WA": InstrumentInfo(
        symbol="LPP.WA", name="LPP", asset_type="Akcja (PL)", sector="Odzież",
        description="Polski gigant odzieżowy, właściciel marek Reserved, Cropp, House, Mohito, Sinsay.",
        influences=["Kursy walut (USD/PLN, EUR/PLN)", "Koszty frachtu", "Popyt konsumencki"],
        volatility="Wysoka", correlations=["WIG-Odzież"],
        trading_tips="Najdroższa nominalnie akcja na GPW. Wrażliwa na wyniki sprzedaży e-commerce.",
        history="Założona w 1991 roku w Gdańsku przez Marka Piechockiego i Jerzego Lubiańca.",
        evolution="Od hurtowni odzieży do globalnej sieci retail. Rozwój marki Sinsay (segment value) stał się motorem napędowym.",
        key_features=["Globalny zasięg", "E-commerce", "Sinsay", "Rodzinny charakter (fundacja)"],
        founding_year="1991",
        company_size="Salony w > 39 krajach, Zatrudnienie > 30 tys.",
        products=["Reserved", "Cropp", "House", "Mohito", "Sinsay"],
        famous_for="Budowa polskiego imperium modowego i skuteczna rywalizacja z Zarą (Inditex) i H&M."
    ),
    "PZU.WA": InstrumentInfo(
        symbol="PZU.WA", name="PZU", asset_type="Akcja (PL)", sector="Ubezpieczenia",
        description="Największy ubezpieczyciel w Europie Środkowo-Wschodniej. Gigant dywidendowy.",
        influences=["Szkodowość (pogoda)", "Wyniki inwestycyjne", "Polityka dywidendowa"],
        volatility="Niska/Średnia", correlations=["WIG20", "Obligacje"],
        trading_tips="Defensywna spółka typu 'Value'. Idealna pod dywidendę.",
        history="Tradycje sięgają 1803 roku. W obecnej formie od 1952 roku jako Państwowy Zakład Ubezpieczeń.",
        evolution="Od monopolisty PRL do nowoczesnej grupy finansowej (właściciel Banku Pekao i Alior Banku).",
        key_features=["Lider rynku", "Wysoka dywidenda", "Udział Skarbu Państwa", "Stabilność"],
        founding_year="1803 (tradycje), 1952 (PZU)",
        company_size="Aktywa > 400 mld PLN, Zatrudnienie > 40 tys.",
        products=["Ubezpieczenia OC/AC", "Ubezpieczenia na życie", "PPK", "Inwestycje", "Opieka zdrowotna"],
        famous_for="Hasło 'Przezorny zawsze ubezpieczony' i dominacja na polskim rynku."
    ),
    "ALE.WA": InstrumentInfo(
        symbol="ALE.WA", name="Allegro", asset_type="Akcja (PL)", sector="E-commerce",
        description="Najpopularniejsza platforma zakupowa w Polsce. Lider e-handlu.",
        influences=["Wydatki konsumenckie", "Konkurencja (Amazon/Temu)", "Marże logistyczne"],
        volatility="Wysoka", correlations=["WIG-Tech", "AMZN"],
        trading_tips="Spółka wzrostowa. Wrażliwa na sentyment do sektora tech i wyniki kwartalne.",
        history="Powstało w 1999 roku jako polski odpowiednik serwisu aukcyjnego (początkowo własność QXL).",
        evolution="Od serwisu aukcyjnego dla hobbystów do potężnego marketplace z własną logistyką (One Box).",
        key_features=["Dominacja w PL", "Allegro Smart", "Własna logistyka", "Wysoka rozpoznawalność"],
        founding_year="1999",
        company_size="GMV > 50 mld PLN, Miliony aktywnych kupujących.",
        products=["Marketplace", "Allegro Smart", "Allegro Pay", "One Box"],
        famous_for="Bycie 'polskim Amazonem' i pokonanie eBay na lokalnym rynku."
    ),
    "SPL.WA": InstrumentInfo(
        symbol="SPL.WA", name="Santander Bank Polska", asset_type="Akcja (PL)", sector="Usługi Finansowe",
        description="Jeden z największych banków komercyjnych w Polsce, część hiszpańskiej grupy Santander.",
        influences=["Stopy procentowe", "Sytuacja w strefie euro", "Koszt ryzyka"],
        volatility="Średnia", correlations=["WIG-Banki", "Banco Santander"],
        trading_tips="Bank o silnej pozycji kapitałowej. Często płaci wysokie dywidendy.",
        history="Dawniej Bank Zachodni WBK (powstały z fuzji BZ i WBK). Od 2018 roku pod marką Santander.",
        evolution="Transformacja z banku regionalnego (Wrocław/Wielkopolska) w ogólnopolskiego lidera, przejęcie Kredyt Banku i Deutsche Bank Polska.",
        key_features=["Globalna marka", "Innowacyjność", "Silny segment detaliczny i MŚP"],
        founding_year="2001 (jako BZ WBK), korzenie sięgają 1988",
        company_size="Zatrudnienie > 11 tys., Aktywa > 250 mld PLN",
        products=["Konto Jakie Chcę", "Kredyty gotówkowe", "Leasing", "Factoring"],
        famous_for="Reklamy z Chuckiem Norrisem (jako BZ WBK) i czerwony branding."
    ),
    "ALR.WA": InstrumentInfo(
        symbol="ALR.WA", name="Alior Bank", asset_type="Akcja (PL)", sector="Usługi Finansowe",
        description="Uniwersalny bank komercyjny, znany z innowacyjności i 'cyfrowego buntu'.",
        influences=["Stopy procentowe", "Portfel kredytowy (ryzyko)", "Współpraca z PZU (główny akcjonariusz)"],
        volatility="Średnia/Wysoka", correlations=["WIG-Banki", "PZU.WA"],
        trading_tips="Często bardziej zmienny niż PKO czy Pekao. Lider cyfryzacji.",
        history="Założony w 2008 roku jako start-up bankowy przez grupę Carlo Tassara. Zadebiutował w szczycie kryzysu finansowego.",
        evolution="Od 'banku wyższej kultury' do lidera technologii blockchain i AI w bankowości. Przejął Meritum Bank i część BPH.",
        key_features=["Innowacyjność", "Bankowość cyfrowa", "Kantor Walutowy"],
        founding_year="2008",
        company_size="Zatrudnienie > 7 tys., Aktywa > 80 mld PLN",
        products=["Konto Jakże Osobiste", "Kantor Walutowy", "Kredyt konsumencki", "Alior Pay"],
        famous_for="Melonik w logo i hasło 'Wyższa kultura bankowości'."
    ),
    "MBK.WA": InstrumentInfo(
        symbol="MBK.WA", name="mBank", asset_type="Akcja (PL)", sector="Usługi Finansowe",
        description="Ikona mobilnej bankowości w Polsce. Skupiony na klientach miejskich i cyfrowych.",
        influences=["Kredyty frankowe (duży portfel)", "Stopy procentowe", "Sentyment do sektora bankowego"],
        volatility="Wysoka (ryzyko prawne CHF)", correlations=["WIG-Banki", "Commerzbank"],
        trading_tips="Silnie uzależniony od wyroków TSUE ws. frankowiczów. Fundamentalnie bardzo zyskowny biznes core'owy.",
        history="Powstał jako BRE Bank w 1986 roku. Marka mBank uruchomiona w 2000 roku jako pierwszy bank wirtualny.",
        evolution="Rebranding z BRE Banku na mBank w 2013 roku. Pionier bankowości internetowej i mobilnej.",
        key_features=["Lider mobile", "Klient wielkomiejski", "Obciążenie CHF", "Grupa Commerzbank"],
        founding_year="1986 (BRE), 2000 (marka mBank)",
        company_size="Zatrudnienie > 6 tys., ok. 5 mln klientów detalicznych",
        products=["mKonto", "Aplikacja mobilna", "Kredyty hipoteczne", "eMakler"],
        famous_for="Pierwszy internetowy bank w Polsce. Kolorowa 'kwiatowa' identyfikacja wizualna."
    ),
    "BDX.WA": InstrumentInfo(
        symbol="BDX.WA", name="Budimex", asset_type="Akcja (PL)", sector="Budownictwo",
        description="Lider rynku budowlanego w Polsce. Generalny wykonawca infrastruktury.",
        influences=["Inwestycje publiczne (KPO)", "Ceny materiałów", "Waloryzacja kontraktów"],
        volatility="Średnia", correlations=["WIG-Budownictwo"],
        trading_tips="Spółka dywidendowa o solidnych fundamentach. Zależna od funduszy UE.",
        history="Powstał w 1968 roku jako Centrala Handlu Zagranicznego Budownictwa.",
        evolution="Od eksportera usług budowlanych do lidera krajowego rynku infrastruktury i kubatury.",
        key_features=["Portfel zamówień", "Dywidenda", "Inwestor strategiczny (Ferrovial)"],
        founding_year="1968",
        company_size="Portfel zamówień > 13 mld PLN",
        products=["Autostrady", "Koleje", "Budynki użyteczności publicznej", "Energetyka"],
        famous_for="Budowa kluczowych dróg i autostrad w Polsce."
    ),
    "PCO.WA": InstrumentInfo(
        symbol="PCO.WA", name="Pepco Group", asset_type="Akcja (PL)", sector="Handel",
        description="Europejska sieć dyskontów niespożywczych (Pepco, Dealz, Poundland).",
        influences=["Inflacja (koszty/popyt)", "Ekspansja w Europie", "Kursy walut"],
        volatility="Średnia/Wysoka", correlations=["WIG-Odzież"],
        trading_tips="Model dyskontowy sprawdza się w trudnych czasach. Szybka ekspansja.",
        history="Marka Pepco powstała w Polsce w 2004 roku (wywodzi się z UK).",
        evolution="Niesamowita ekspansja w Europie Środkowej i Zachodniej. Debiut na GPW w 2021.",
        key_features=["Format dyskontowy", "Szybki wzrost", "Międzynarodowy zasięg"],
        founding_year="1999 (Poundland), 2004 (Pepco PL)",
        company_size="> 4000 sklepów w Europie",
        products=["Odzież dziecięca", "Dom i dekoracje", "Zabawki", "FMCG (Dealz)"],
        famous_for="Tanie ubrania dla dzieci i artykuły do domu ('Więcej za mniej')."
    ),

    # --- USA GIANTS ---
    "AAPL": InstrumentInfo(
        symbol="AAPL", name="Apple Inc.", asset_type="Akcja (US)", sector="Technologia",
        description="Producent iPhone'a, Maca i usług cyfrowych. Największa spółka świata.",
        influences=["Sprzedaż iPhone", "Przychody z usług", "Chiny (popyt/produkcja)"],
        volatility="Średnia", correlations=["NASDAQ"],
        trading_tips="Safe haven sektora technologicznego. Silny trend, rzadkie głębokie korekty.",
        history="Założona 1 kwietnia 1976 przez Steve'a Jobsa, Steve'a Wozniaka i Ronalda Wayne'a w garażu.",
        evolution="Od komputerów osobistych (Apple II, Mac), przez rewolucję mobilną (iPod, iPhone), do usług i wearables.",
        key_features=["Ekosystem (Walled Garden)", "Ogromne zapasy gotówki", "Lojalność klientów", "Design"],
        founding_year="1976",
        company_size="Pierwsza spółka warta 3 bln USD, Zatrudnienie > 160 tys.",
        products=["iPhone", "Mac", "iPad", "Apple Watch", "AirPods", "Usługi (App Store, Apple Music)"],
        famous_for="iPhone, który zmienił świat telefonów. Perfekcyjny marketing i design."
    ),
    "TSLA": InstrumentInfo(
        symbol="TSLA", name="Tesla", asset_type="Akcja (US)", sector="Motoryzacja",
        description="Lider aut elektrycznych (EV) i energii odnawialnej.",
        influences=["Dostawy aut", "Postępy w FSD (Autopilot)", "Osoba Elona Muska"],
        volatility="Bardzo Wysoka", correlations=["Bitcoin", "Tech Growth"],
        trading_tips="Ulubieniec spekulantów. Ogromne ruchy intraday.",
        history="Założona w 2003 roku (Elon Musk dołączył w 2004). Nazwana na cześć Nikoli Tesli.",
        evolution="Od niszowego Roadstera, przez masowy Model 3/Y, do Cybertrucka i robotyki (Optimus).",
        key_features=["Innowacja", "Kultowa marka", "Zmienność", "Sieć Supercharger"],
        founding_year="2003",
        company_size="Zatrudnienie > 140 tys. Najcenniejszy producent aut świata.",
        products=["Model S/3/X/Y", "Cybertruck", "Powerwall", "Megapack", "Autopilot FSD"],
        famous_for="Przyspieszenie przejścia świata na zrównoważoną energię. Elon Musk."
    ),
    "NVDA": InstrumentInfo(
        symbol="NVDA", name="NVIDIA", asset_type="Akcja (US)", sector="Półprzewodniki",
        description="Dominator rynku chipów AI i kart graficznych.",
        influences=["Popyt na AI (Data Centers)", "Gry komputerowe", "Chiny (eksport)"],
        volatility="Wysoka", correlations=["SOXX", "NASDAQ"],
        trading_tips="Lokomotywa hossy AI. Kupuj silne wybicia.",
        history="Założona w 1993 roku przez Jensena Huanga. Początkowo skupiona na grafice 3D do gier.",
        evolution="Wynalezienie GPU (1999), wejście w obliczenia równoległe (CUDA) i dominacja w AI (H100/Blackwell).",
        key_features=["Monopol w AI", "Marże > 70%", "Wzrost wykładniczy", "CUDA"],
        founding_year="1993",
        company_size="Kapitalizacja > 2 bln USD, Zatrudnienie ~30 tys.",
        products=["GeForce (Gaming)", "H100/Blackwell (Data Center)", "Omniverse", "Drive (Auto)"],
        famous_for="Chipy napędzające rewolucję Sztucznej Inteligencji (ChatGPT działa na GPU Nvidia)."
    ),
    "MSFT": InstrumentInfo(
        symbol="MSFT", name="Microsoft", asset_type="Akcja (US)", sector="Technologia",
        description="Gigant oprogramowania (Windows, Office) i chmury (Azure).",
        influences=["Wzrost Azure", "Adopcja AI (Copilot)", "Rynek PC"],
        volatility="Średnia", correlations=["NASDAQ"],
        trading_tips="Stabilny wzrost. Dobra defensywa w sektorze tech.",
        history="Założony w 1975 przez Billa Gatesa i Paula Allena. Wizja: 'Komputer na każdym biurku'.",
        evolution="Od systemu DOS/Windows, przez erę Internet Explorera, do chmury Azure i AI (inwestycja w OpenAI).",
        key_features=["Azure", "Subskrypcje (SaaS)", "AI (OpenAI)", "Dywersyfikacja"],
        founding_year="1975",
        company_size="Kapitalizacja > 3 bln USD, Zatrudnienie > 220 tys.",
        products=["Windows", "Office 365", "Azure", "Xbox", "LinkedIn", "Copilot"],
        famous_for="System Windows i pakiet Office. Największy inwestor w OpenAI (ChatGPT)."
    ),
    "GOOGL": InstrumentInfo(
        symbol="GOOGL", name="Alphabet (Google)", asset_type="Akcja (US)", sector="Technologia",
        description="Lider wyszukiwania internetowego, reklamy cyfrowej i wideo (YouTube).",
        influences=["Wydatki na reklamę", "Regulacje antymonopolowe", "Rozwój AI (Gemini)"],
        volatility="Średnia", correlations=["NASDAQ", "META"],
        trading_tips="Dominator rynku reklamowego. Wrażliwy na konkurencję w AI.",
        history="Założona w 1998 roku przez Larry'ego Page'a i Sergeya Brina w garażu w Menlo Park.",
        evolution="Od prostej wyszukiwarki do konglomeratu Alphabet (Android, YouTube, Waymo, Google Cloud).",
        key_features=["Monopol w Search", "YouTube", "Android", "Innowacje (DeepMind)"],
        founding_year="1998",
        company_size="Kapitalizacja > 1.5 bln USD, Zatrudnienie > 180 tys.",
        products=["Wyszukiwarka", "YouTube", "Android", "Google Cloud", "Pixel", "Gemini"],
        famous_for="Zorganizowanie światowych zasobów informacji. 'Google' to synonim wyszukiwania."
    ),
    "AMZN": InstrumentInfo(
        symbol="AMZN", name="Amazon", asset_type="Akcja (US)", sector="E-commerce",
        description="Globalny lider handlu elektronicznego i chmury obliczeniowej (AWS).",
        influences=["Wydatki konsumenckie", "Wzrost AWS", "Koszty logistyki"],
        volatility="Średnia/Wysoka", correlations=["NASDAQ", "XLY (Discretionary)"],
        trading_tips="AWS to motor zysków, e-commerce to motor przychodów. Obserwuj marże.",
        history="Założona w 1994 roku przez Jeffa Bezosa jako księgarnia internetowa.",
        evolution="Od sprzedaży książek do 'sklepu ze wszystkim', lidera chmury (AWS) i streamingu (Prime).",
        key_features=["Dominacja e-commerce", "AWS (Lider chmury)", "Logistyka", "Prime"],
        founding_year="1994",
        company_size="Kapitalizacja > 1.8 bln USD, Zatrudnienie > 1.5 mln.",
        products=["Sklep Amazon", "AWS", "Prime Video", "Kindle", "Alexa/Echo"],
        famous_for="Rewolucja w zakupach online i stworzenie rynku chmury obliczeniowej (AWS)."
    ),
    "META": InstrumentInfo(
        symbol="META", name="Meta Platforms", asset_type="Akcja (US)", sector="Technologia",
        description="Właściciel największych platform społecznościowych: Facebook, Instagram, WhatsApp.",
        influences=["Liczba użytkowników (DAU/MAU)", "Przychody z reklam", "Wydatki na Metaverse/AI"],
        volatility="Wysoka", correlations=["NASDAQ", "GOOGL"],
        trading_tips="Maszynka do gotówki z reklam. Wrażliwa na zmiany prywatności (Apple iOS).",
        history="Założona w 2004 roku jako TheFacebook przez Marka Zuckerberga na Harvardzie.",
        evolution="Od serwisu dla studentów do globalnego imperium social media i inwestycji w VR/AI.",
        key_features=["Efekt sieciowy", "Miliardy użytkowników", "Monetyzacja danych", "Lider VR"],
        founding_year="2004",
        company_size="Kapitalizacja > 1.2 bln USD, Użytkownicy > 3 mld miesięcznie.",
        products=["Facebook", "Instagram", "WhatsApp", "Messenger", "Quest (VR)"],
        famous_for="Połączenie miliardów ludzi i kontrowersje związane z prywatnością danych."
    ),

    # --- CRYPTO & COMMODITIES ---
    "BTC": InstrumentInfo(
        symbol="BTC-USD", name="Bitcoin", asset_type="Kryptowaluta", sector="Crypto",
        description="Cyfrowe złoto. Pierwsza i największa kryptowaluta.",
        influences=["Napływy do ETF", "Halving", "Sentyment globalny"],
        volatility="Bardzo Wysoka", correlations=["NASDAQ (okresowo)"],
        trading_tips="Tylko dla kapitału ryzyka. HODL lub swing trading.",
        history="Powstał w 2009 jako odpowiedź na kryzys bankowy.",
        evolution="Instytucjonalizacja poprzez ETFy Spot.",
        key_features=["Decentralizacja", "Ograniczona podaż"]
    ),
    "GOLD": InstrumentInfo(
        symbol="GC=F", name="Złoto", asset_type="Surowiec", sector="Metale Szlachetne",
        description="Ochrona kapitału i zabezpieczenie przed chaosem.",
        influences=["Realne stopy proc.", "Dolar (USD)", "Geopolityka"],
        volatility="Średnia", correlations=["USD (ujemna)"],
        trading_tips="Akumuluj w czasie spokoju, sprzedawaj w euforii strachu.",
        history="Pieniądz od tysiącleci.",
        key_features=["Safe Haven", "Brak ryzyka kontrahenta"]
    ),
    "OIL": InstrumentInfo(
        symbol="CL=F", name="Ropa WTI", asset_type="Surowiec", sector="Energia",
        description="Krew gospodarki. Kluczowy surowiec energetyczny.",
        influences=["OPEC+", "Wojny", "Popyt globalny"],
        volatility="Wysoka", correlations=["Akcje Energy"],
        trading_tips="Bardzo techniczny, ale wrażliwy na nagłe newsy.",
        history="Podstawa ery przemysłowej.",
        key_features=["Geopolityka", "Cykliczność"]
    )
}

def get_instrument_info(query: str) -> Optional[InstrumentInfo]:
    """
    Wyszukuje informacje o instrumencie.
    1. Sprawdza katalog manualny (INSTRUMENT_CATALOG).
    2. Jeśli brak, sprawdza metadane (INSTRUMENT_METADATA) i generuje opis automatycznie.
    """
    q = query.upper().strip()
    
    # 1. Sprawdź katalog manualny (po kluczu)
    if q in INSTRUMENT_CATALOG:
        return INSTRUMENT_CATALOG[q]
        
    # 2. Sprawdź katalog manualny (po symbolu w obiekcie)
    for info in INSTRUMENT_CATALOG.values():
        if info.symbol == q:
            return info
            
    # 3. Fallback: Generowanie z metadanych
    # Sprawdź czy query jest kluczem w metadanych (np. "PKO.WA")
    if q in INSTRUMENT_METADATA:
        return _generate_info_from_metadata(q, INSTRUMENT_METADATA[q])
        
    # Sprawdź czy query jest nazwą w metadanych (fuzzy search)
    for ticker, meta in INSTRUMENT_METADATA.items():
        if q in meta["name"].upper() or q == ticker:
            return _generate_info_from_metadata(ticker, meta)
            
    return None

def _generate_info_from_metadata(ticker: str, meta: dict) -> InstrumentInfo:
    """
    Tworzy obiekt InstrumentInfo na podstawie metadanych i szablonów sektorowych.
    """
    sector = meta.get("sector", "Inne")
    asset_type = meta.get("type", "Instrument")
    name = meta.get("name", ticker)
    
    # Pobierz wiedzę dla sektora lub domyślną
    knowledge = SECTOR_KNOWLEDGE.get(sector, DEFAULT_TEMPLATE)
    
    # Dostosuj opis
    description = f"{knowledge['desc']} (Instrument typu: {asset_type})."
    
    return InstrumentInfo(
        symbol=ticker,
        name=name,
        asset_type=asset_type,
        sector=sector,
        description=description,
        influences=knowledge.get("influences", []),
        volatility=knowledge.get("volatility", "Nieokreślona"),
        correlations=[], # Trudno zgadnąć automatycznie
        trading_tips=knowledge.get("tips", "Brak specyficznych porad."),
        history=f"Instrument {name} jest notowany jako {ticker}. Należy do sektora {sector}.",
        evolution=f"Rozwój instrumentu jest ściśle powiązany z kondycją sektora: {sector}.",
        key_features=[f"Sektor: {sector}", f"Typ: {asset_type}", "Notowany publicznie"],
        founding_year="N/A",
        company_size="Zależna od wyceny rynkowej",
        products=knowledge.get("products", ["Standardowe produkty sektora"]),
        famous_for=f"Działalność w sektorze {sector}"
    )

def get_all_instruments() -> List[InstrumentInfo]:
    """
    Zwraca listę wszystkich dostępnych instrumentów (manualnych i generowanych).
    Używane np. przez Encyklopedię do generowania pełnej listy.
    """
    all_instruments = []
    
    # 1. Dodaj manualne (mają priorytet)
    processed_tickers = set()
    for ticker, info in INSTRUMENT_CATALOG.items():
        all_instruments.append(info)
        processed_tickers.add(ticker)
        processed_tickers.add(info.symbol) # Zabezpieczenie
        
    # 2. Dodaj pozostałe z metadanych
    for ticker, meta in INSTRUMENT_METADATA.items():
        if ticker not in processed_tickers:
            # Sprawdź czy nie ma go w manualnych pod inną nazwą (np. klucz vs symbol)
            # (Uproszczenie: zakładamy spójność kluczy)
            if ticker not in INSTRUMENT_CATALOG:
                all_instruments.append(_generate_info_from_metadata(ticker, meta))
                
    return all_instruments
