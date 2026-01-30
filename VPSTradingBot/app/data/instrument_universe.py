"""
Moduł definiujący uniwersum instrumentów finansowych dostępnych w aplikacji.
Zawiera listy symboli (tickerów) pogrupowane w kategorie oraz metadane
niezbędne do wyświetlania informacji w UI i Telegramie.
"""
from typing import Dict, List

# ======================================================
# 1. DEFINICJE SEKCJI INSTRUMENTÓW
# ======================================================

# A. POLSKIE AKCJE (GPW)
"""Lista spółek notowanych na Giełdzie Papierów Wartościowych w Warszawie."""
POLISH_STOCKS = [
    "PKO.WA", "SPL.WA", "ALR.WA", "MBK.WA", "JSW.WA", "LPP.WA", "PGE.WA", "TPE.WA",
    "CCC.WA", "CPS.WA", "OPL.WA", "ACP.WA", "BHW.WA", "ING.WA", "BOS.WA", "ENA.WA",
    "ENG.WA", "KER.WA", "TXT.WA", "MAB.WA", "MRC.WA", "PKP.WA", "TEN.WA", "PLW.WA",
    "DNP.WA", "ATT.WA", "STP.WA", "CIG.WA", "KTY.WA", "MLP.WA", "ERB.WA", "GPW.WA",
    "SLV.WA", "PXM.WA", "MFO.WA", "AMC.WA", "KGH.WA", "PEO.WA", "CDR.WA", "PKN.WA",
    "PZU.WA", "KRU.WA", "11B.WA", "BDX.WA", "VRG.WA"
]

# B. GLOBALNE GIGANTY (GLOBAL GIANTS)
"""Największe światowe spółki (Blue Chips) z różnych sektorów."""
GLOBAL_GIANTS = [
    "BRK-B", "V", "MA", "PG", "KO", "PEP", "XOM", "WMT", "HD", "CRM", "SAP", "NKE",
    "MCD", "SBUX", "BAC", "C", "UNH", "PFE", "MRK", "T", "VZ", "RIO", "BHP", "SHOP",
    "LIN", "SAP.DE", "NESN.SW", "ROG.SW", "NOVN.SW", "BAYN.DE", "MC.PA", "LULU",
    "RACE", "AIR.PA", "SIE.DE", "JPM", "JNJ", "CVX", "DIS", "NFLX", "GS", "MS", "LVMUY"
]

# C. TECH GIANTS (FAVORITES)
"""Spółki technologiczne o dużej kapitalizacji i wysokiej zmienności."""
TECH_GIANTS = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "ADBE", "INTC",
    "AMD", "CSCO", "ORCL", "IBM", "ASML", "AVGO", "TSM", "PLTR", "CRWD", "PANW", "SMCI"
]

# D. ETFs & INDICES
"""Fundusze ETF oraz główne indeksy giełdowe."""
ETFS_INDICES = [
    "SPY", "VOO", "IWM", "EFA", "EEM", "VWO", "XLF", "XLY", "XLP", "XLV", "XLI", "XLU",
    "^GSPC", "^NDX", "^DJI", "^RUT", "^STOXX50E", "^FTSE", "^GDAXI", "^N225", "VGK",
    "VEA", "VTI", "VT", "IEMG", "EWZ", "EWJ", "EWH", "EWT", "EWC", "EWG", "EWQ", "EWI",
    "EWL", "HYG", "LQD", "IVV", "QQQ", "XLK", "XLE", "ETFBW20TR.WA", "URA", "IEF",
    "SHY", "IEI", "BND", "AGG", "^VIX", "DX-Y.NYB"
]

# E. COMMODITIES & FUTURES
"""Surowce, metale szlachetne oraz kontrakty futures."""
COMMODITIES = [
    "GLD", "SLV", "USO", "UNG", "TLT", "GC=F", "SI=F", "PL=F", "PA=F", "HG=F", "CL=F",
    "BZ=F", "NG=F", "HO=F", "RB=F", "ZC=F", "ZS=F", "ZW=F", "SB=F", "KC=F", "CC=F",
    "CT=F", "ZR=F", "PALL", "PPLT", "DBA", "DBB", "DBO", "CORN", "SOYB", "WEAT",
    "IAU", "CPER", "UGA", "WOOD", "JJC", "JO", "CANE", "NIB", "KRBN"
]

# F. CRYPTO
"""Główne kryptowaluty notowane do dolara amerykańskiego."""
CRYPTO = [
    "BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD", "BCH-USD", "LTC-USD", "ADA-USD",
    "DOGE-USD", "BNB-USD", "DOT-USD", "MATIC-USD", "AVAX-USD", "LINK-USD", "UNI-USD"
]

# ======================================================
# 2. MAPOWANIE SEKCJI (INSTRUMENT_SECTIONS)
# ======================================================
INSTRUMENT_SECTIONS = {
    "POLISH_STOCKS": POLISH_STOCKS,
    "GLOBAL_GIANTS": GLOBAL_GIANTS,
    "TECH_GIANTS": TECH_GIANTS,
    "ETFS_INDICES": ETFS_INDICES,
    "COMMODITIES": COMMODITIES,
    "CRYPTO": CRYPTO
}

# ======================================================
# 3. DOMYŚLNY UNIWERSUM (DEFAULT_INSTRUMENT_UNIVERSE)
# ======================================================
# Domyślnie wszystkie zdefiniowane
DEFAULT_INSTRUMENT_UNIVERSE = (
    POLISH_STOCKS + GLOBAL_GIANTS + TECH_GIANTS + ETFS_INDICES + COMMODITIES + CRYPTO
)

# ======================================================
# 9. METADATA (Dla Bazy Wiedzy / UI)
# ======================================================

"""
Słownik metadanych instrumentów.
Klucz: Symbol instrumentu (np. 'PKO.WA')
Wartość: Słownik z polami:
  - name: Pełna nazwa
  - type: Typ instrumentu (Akcja, ETF, Indeks, itp.)
  - sector: Sektor gospodarki
"""
INSTRUMENT_METADATA = {
    # --- POLSKA (GPW) ---
    "PKO.WA": {"name": "PKO BP", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "SPL.WA": {"name": "Santander Bank Polska", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "ALR.WA": {"name": "Alior Bank", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "MBK.WA": {"name": "mBank", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "JSW.WA": {"name": "Jastrzębska Spółka Węglowa", "type": "Akcja (PL)", "sector": "Surowce"},
    "LPP.WA": {"name": "LPP", "type": "Akcja (PL)", "sector": "Odzież"},
    "PGE.WA": {"name": "PGE", "type": "Akcja (PL)", "sector": "Energetyka"},
    "TPE.WA": {"name": "Tauron", "type": "Akcja (PL)", "sector": "Energetyka"},
    "CCC.WA": {"name": "CCC", "type": "Akcja (PL)", "sector": "Handel"},
    "CPS.WA": {"name": "Cyfrowy Polsat", "type": "Akcja (PL)", "sector": "Media"},
    "OPL.WA": {"name": "Orange Polska", "type": "Akcja (PL)", "sector": "Telekomunikacja"},
    "ACP.WA": {"name": "Asseco Poland", "type": "Akcja (PL)", "sector": "IT"},
    "BHW.WA": {"name": "Citi Handlowy", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "ING.WA": {"name": "ING Bank Śląski", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "BOS.WA": {"name": "BOŚ Bank", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "ENA.WA": {"name": "Enea", "type": "Akcja (PL)", "sector": "Energetyka"},
    "ENG.WA": {"name": "Energa", "type": "Akcja (PL)", "sector": "Energetyka"},
    "KER.WA": {"name": "Kernel", "type": "Akcja (PL)", "sector": "Rolnictwo"},
    "TXT.WA": {"name": "Text SA (LiveChat)", "type": "Akcja (PL)", "sector": "IT"},
    "MAB.WA": {"name": "Mabion", "type": "Akcja (PL)", "sector": "Biotechnologia"},
    "MRC.WA": {"name": "Mercator", "type": "Akcja (PL)", "sector": "Medyczne"},
    "PKP.WA": {"name": "PKP Cargo", "type": "Akcja (PL)", "sector": "Transport"},
    "TEN.WA": {"name": "Ten Square Games", "type": "Akcja (PL)", "sector": "Gaming"},
    "PLW.WA": {"name": "PlayWay", "type": "Akcja (PL)", "sector": "Gaming"},
    "DNP.WA": {"name": "Dino Polska", "type": "Akcja (PL)", "sector": "Handel"},
    "ATT.WA": {"name": "Atende", "type": "Akcja (PL)", "sector": "IT"},
    "STP.WA": {"name": "Stalprodukt", "type": "Akcja (PL)", "sector": "Przemysł"},
    "CIG.WA": {"name": "CI Games", "type": "Akcja (PL)", "sector": "Gaming"},
    "KTY.WA": {"name": "Krynica Vitamin", "type": "Akcja (PL)", "sector": "Spożywczy"},
    "MLP.WA": {"name": "MLP Group", "type": "Akcja (PL)", "sector": "Nieruchomości"},
    "ERB.WA": {"name": "Erbud", "type": "Akcja (PL)", "sector": "Budownictwo"},
    "GPW.WA": {"name": "Giełda Papierów Wartościowych", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "SLV.WA": {"name": "Selvita", "type": "Akcja (PL)", "sector": "Biotechnologia"},
    "PXM.WA": {"name": "Polimex Mostostal", "type": "Akcja (PL)", "sector": "Budownictwo"},
    "MFO.WA": {"name": "MFO", "type": "Akcja (PL)", "sector": "Przemysł"},
    "AMC.WA": {"name": "Amica", "type": "Akcja (PL)", "sector": "AGD"},
    "ETFBW20TR.WA": {"name": "Beta ETF WIG20TR", "type": "ETF (PL)", "sector": "Indeks"},
    "KGH.WA": {"name": "KGHM Polska Miedź", "type": "Akcja (PL)", "sector": "Surowce"},
    "PEO.WA": {"name": "Bank Pekao", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "CDR.WA": {"name": "CD Projekt", "type": "Akcja (PL)", "sector": "Gaming"},
    "PKN.WA": {"name": "Orlen", "type": "Akcja (PL)", "sector": "Paliwa"},
    "PZU.WA": {"name": "PZU", "type": "Akcja (PL)", "sector": "Ubezpieczenia"},
    "KRU.WA": {"name": "Kruk", "type": "Akcja (PL)", "sector": "Usługi Finansowe"},
    "11B.WA": {"name": "11 bit studios", "type": "Akcja (PL)", "sector": "Gaming"},
    "BDX.WA": {"name": "Budimex", "type": "Akcja (PL)", "sector": "Budownictwo"},
    "VRG.WA": {"name": "VRG", "type": "Akcja (PL)", "sector": "Odzież"},

    # --- GLOBAL GIANTS ---
    "BRK-B": {"name": "Berkshire Hathaway", "type": "Akcja (US)", "sector": "Usługi Finansowe"},
    "V": {"name": "Visa", "type": "Akcja (US)", "sector": "Usługi Finansowe"},
    "MA": {"name": "Mastercard", "type": "Akcja (US)", "sector": "Usługi Finansowe"},
    "PG": {"name": "Procter & Gamble", "type": "Akcja (US)", "sector": "Dobra podstawowe"},
    "KO": {"name": "Coca-Cola", "type": "Akcja (US)", "sector": "Napoje"},
    "PEP": {"name": "PepsiCo", "type": "Akcja (US)", "sector": "Napoje"},
    "XOM": {"name": "Exxon Mobil", "type": "Akcja (US)", "sector": "Paliwa"},
    "WMT": {"name": "Walmart", "type": "Akcja (US)", "sector": "Handel"},
    "HD": {"name": "Home Depot", "type": "Akcja (US)", "sector": "Handel"},
    "CRM": {"name": "Salesforce", "type": "Akcja (US)", "sector": "IT"},
    "SAP": {"name": "SAP", "type": "Akcja (US)", "sector": "IT"},
    "NKE": {"name": "Nike", "type": "Akcja (US)", "sector": "Odzież"},
    "MCD": {"name": "McDonald's", "type": "Akcja (US)", "sector": "Gastronomia"},
    "SBUX": {"name": "Starbucks", "type": "Akcja (US)", "sector": "Gastronomia"},
    "BAC": {"name": "Bank of America", "type": "Akcja (US)", "sector": "Usługi Finansowe"},
    "C": {"name": "Citigroup", "type": "Akcja (US)", "sector": "Usługi Finansowe"},
    "UNH": {"name": "UnitedHealth", "type": "Akcja (US)", "sector": "Medyczne"},
    "PFE": {"name": "Pfizer", "type": "Akcja (US)", "sector": "Farmacja"},
    "MRK": {"name": "Merck", "type": "Akcja (US)", "sector": "Farmacja"},
    "T": {"name": "AT&T", "type": "Akcja (US)", "sector": "Telekomunikacja"},
    "VZ": {"name": "Verizon", "type": "Akcja (US)", "sector": "Telekomunikacja"},
    "RIO": {"name": "Rio Tinto", "type": "Akcja (UK/US)", "sector": "Górnictwo"},
    "BHP": {"name": "BHP Group", "type": "Akcja (AU/US)", "sector": "Górnictwo"},
    "SHOP": {"name": "Shopify", "type": "Akcja (US)", "sector": "E-commerce"},
    "LIN": {"name": "Linde", "type": "Akcja (US)", "sector": "Chemia"},
    "SAP.DE": {"name": "SAP (DE)", "type": "Akcja (DE)", "sector": "IT"},
    "NESN.SW": {"name": "Nestle", "type": "Akcja (CH)", "sector": "Spożywczy"},
    "ROG.SW": {"name": "Roche", "type": "Akcja (CH)", "sector": "Farmacja"},
    "NOVN.SW": {"name": "Novartis", "type": "Akcja (CH)", "sector": "Farmacja"},
    "BAYN.DE": {"name": "Bayer", "type": "Akcja (DE)", "sector": "Farmacja/Chemia"},
    "MC.PA": {"name": "LVMH", "type": "Akcja (FR)", "sector": "Dobra luksusowe"},
    "LULU": {"name": "Lululemon", "type": "Akcja (US)", "sector": "Odzież"},
    
    # --- TECH GIANTS (FAVORITES) ---
    "AAPL": {"name": "Apple", "type": "Akcja (US)", "sector": "Technologia"},
    "MSFT": {"name": "Microsoft", "type": "Akcja (US)", "sector": "Technologia"},
    "GOOGL": {"name": "Alphabet (Google) A", "type": "Akcja (US)", "sector": "Technologia"},
    "GOOG": {"name": "Alphabet (Google) C", "type": "Akcja (US)", "sector": "Technologia"},
    "AMZN": {"name": "Amazon", "type": "Akcja (US)", "sector": "E-commerce"},
    "META": {"name": "Meta Platforms", "type": "Akcja (US)", "sector": "Technologia"},
    "NVDA": {"name": "Nvidia", "type": "Akcja (US)", "sector": "Półprzewodniki"},
    "TSLA": {"name": "Tesla", "type": "Akcja (US)", "sector": "Motoryzacja"},
    "ADBE": {"name": "Adobe", "type": "Akcja (US)", "sector": "Oprogramowanie"},
    "INTC": {"name": "Intel", "type": "Akcja (US)", "sector": "Półprzewodniki"},
    "AMD": {"name": "AMD", "type": "Akcja (US)", "sector": "Półprzewodniki"},
    "CSCO": {"name": "Cisco", "type": "Akcja (US)", "sector": "Sieci"},
    "ORCL": {"name": "Oracle", "type": "Akcja (US)", "sector": "Oprogramowanie"},
    "IBM": {"name": "IBM", "type": "Akcja (US)", "sector": "IT"},
    "ASML": {"name": "ASML", "type": "Akcja (EU)", "sector": "Półprzewodniki"},
    "AVGO": {"name": "Broadcom", "type": "Akcja (US)", "sector": "Półprzewodniki"},
    "TSM": {"name": "TSMC", "type": "Akcja (TW)", "sector": "Półprzewodniki"},
    
    # --- ETFS & INDICES ---
    "SPY": {"name": "SPDR S&P 500 ETF", "type": "ETF", "sector": "USA"},
    "VOO": {"name": "Vanguard S&P 500 ETF", "type": "ETF", "sector": "USA"},
    "IWM": {"name": "iShares Russell 2000 ETF", "type": "ETF", "sector": "USA Small Cap"},
    "EFA": {"name": "iShares MSCI EAFE ETF", "type": "ETF", "sector": "Rynki Rozwinięte"},
    "EEM": {"name": "iShares MSCI Emerging Markets ETF", "type": "ETF", "sector": "Rynki Wschodzące"},
    "VWO": {"name": "Vanguard FTSE Emerging Markets ETF", "type": "ETF", "sector": "Rynki Wschodzące"},
    "XLF": {"name": "Financial Select Sector SPDR Fund", "type": "ETF", "sector": "Usługi Finansowe"},
    "XLY": {"name": "Consumer Discretionary Select Sector SPDR Fund", "type": "ETF", "sector": "Dobra Konsumpcyjne"},
    "XLP": {"name": "Consumer Staples Select Sector SPDR Fund", "type": "ETF", "sector": "Dobra Podstawowe"},
    "XLV": {"name": "Health Care Select Sector SPDR Fund", "type": "ETF", "sector": "Ochrona Zdrowia"},
    "XLI": {"name": "Industrial Select Sector SPDR Fund", "type": "ETF", "sector": "Przemysł"},
    "XLU": {"name": "Utilities Select Sector SPDR Fund", "type": "ETF", "sector": "Użyteczność Publiczna"},
    "^GSPC": {"name": "S&P 500 Index", "type": "Indeks", "sector": "USA"},
    "^NDX": {"name": "NASDAQ 100 Index", "type": "Indeks", "sector": "USA"},
    "^DJI": {"name": "Dow Jones Industrial Average", "type": "Indeks", "sector": "USA"},
    "^RUT": {"name": "Russell 2000 Index", "type": "Indeks", "sector": "USA"},
    "^STOXX50E": {"name": "EURO STOXX 50", "type": "Indeks", "sector": "Europa"},
    "^FTSE": {"name": "FTSE 100", "type": "Indeks", "sector": "UK"},
    "^GDAXI": {"name": "DAX", "type": "Indeks", "sector": "Niemcy"},
    "^N225": {"name": "Nikkei 225", "type": "Indeks", "sector": "Japonia"},
    "VGK": {"name": "Vanguard FTSE Europe ETF", "type": "ETF", "sector": "Europa"},
    "VEA": {"name": "Vanguard FTSE Developed Markets ETF", "type": "ETF", "sector": "Rynki Rozwinięte"},
    "VTI": {"name": "Vanguard Total Stock Market ETF", "type": "ETF", "sector": "USA"},
    "VT": {"name": "Vanguard Total World Stock ETF", "type": "ETF", "sector": "Global"},
    "IEMG": {"name": "iShares Core MSCI Emerging Markets ETF", "type": "ETF", "sector": "Rynki Wschodzące"},
    "EWZ": {"name": "iShares MSCI Brazil ETF", "type": "ETF", "sector": "Brazylia"},
    "EWJ": {"name": "iShares MSCI Japan ETF", "type": "ETF", "sector": "Japonia"},
    "EWH": {"name": "iShares MSCI Hong Kong ETF", "type": "ETF", "sector": "Hong Kong"},
    "EWT": {"name": "iShares MSCI Taiwan ETF", "type": "ETF", "sector": "Tajwan"},
    "EWC": {"name": "iShares MSCI Canada ETF", "type": "ETF", "sector": "Kanada"},
    "EWG": {"name": "iShares MSCI Germany ETF", "type": "ETF", "sector": "Niemcy"},
    "EWQ": {"name": "iShares MSCI France ETF", "type": "ETF", "sector": "Francja"},
    "EWI": {"name": "iShares MSCI Italy ETF", "type": "ETF", "sector": "Włochy"},
    "EWL": {"name": "iShares MSCI Switzerland ETF", "type": "ETF", "sector": "Szwajcaria"},
    "HYG": {"name": "iShares iBoxx $ High Yield Corporate Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "LQD": {"name": "iShares iBoxx $ Investment Grade Corporate Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "IVV": {"name": "iShares Core S&P 500 ETF", "type": "ETF", "sector": "USA"},
    "QQQ": {"name": "Invesco QQQ Trust", "type": "ETF", "sector": "USA"},
    "XLK": {"name": "Technology Select Sector SPDR Fund", "type": "ETF", "sector": "Technologia"},
    "XLE": {"name": "Energy Select Sector SPDR Fund", "type": "ETF", "sector": "Energia"},

    # --- COMMODITIES & FUTURES ---
    "GLD": {"name": "SPDR Gold Shares", "type": "ETC", "sector": "Surowce"},
    "SLV": {"name": "iShares Silver Trust", "type": "ETC", "sector": "Surowce"},
    "USO": {"name": "United States Oil Fund", "type": "ETC", "sector": "Surowce"},
    "UNG": {"name": "United States Natural Gas Fund", "type": "ETC", "sector": "Surowce"},
    "TLT": {"name": "iShares 20+ Year Treasury Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "GC=F": {"name": "Złoto (Futures)", "type": "Futures", "sector": "Surowce"},
    "SI=F": {"name": "Srebro (Futures)", "type": "Futures", "sector": "Surowce"},
    "PL=F": {"name": "Platyna (Futures)", "type": "Futures", "sector": "Surowce"},
    "PA=F": {"name": "Pallad (Futures)", "type": "Futures", "sector": "Surowce"},
    "HG=F": {"name": "Miedź (Futures)", "type": "Futures", "sector": "Surowce"},
    "CL=F": {"name": "Ropa WTI (Futures)", "type": "Futures", "sector": "Surowce"},
    "BZ=F": {"name": "Ropa Brent (Futures)", "type": "Futures", "sector": "Surowce"},
    "NG=F": {"name": "Gaz ziemny (Futures)", "type": "Futures", "sector": "Surowce"},
    "HO=F": {"name": "Olej opałowy (Futures)", "type": "Futures", "sector": "Surowce"},
    "RB=F": {"name": "Benzyna RBOB (Futures)", "type": "Futures", "sector": "Surowce"},
    "ZC=F": {"name": "Kukurydza (Futures)", "type": "Futures", "sector": "Surowce"},
    "ZS=F": {"name": "Soja (Futures)", "type": "Futures", "sector": "Surowce"},
    "ZW=F": {"name": "Pszenica (Futures)", "type": "Futures", "sector": "Surowce"},
    "SB=F": {"name": "Cukier (Futures)", "type": "Futures", "sector": "Surowce"},
    "KC=F": {"name": "Kawa (Futures)", "type": "Futures", "sector": "Surowce"},
    "CC=F": {"name": "Kakao (Futures)", "type": "Futures", "sector": "Surowce"},
    "CT=F": {"name": "Bawełna (Futures)", "type": "Futures", "sector": "Surowce"},
    "ZR=F": {"name": "Ryż (Futures)", "type": "Futures", "sector": "Surowce"},
    "PALL": {"name": "Aberdeen Standard Physical Palladium Shares", "type": "ETC", "sector": "Surowce"},
    "PPLT": {"name": "Aberdeen Standard Physical Platinum Shares", "type": "ETC", "sector": "Surowce"},
    "DBA": {"name": "Invesco DB Agriculture Fund", "type": "ETC", "sector": "Surowce"},
    "DBB": {"name": "Invesco DB Base Metals Fund", "type": "ETC", "sector": "Surowce"},
    "DBO": {"name": "Invesco DB Oil Fund", "type": "ETC", "sector": "Surowce"},
    "CORN": {"name": "Teucrium Corn Fund", "type": "ETC", "sector": "Surowce"},
    "SOYB": {"name": "Teucrium Soybean Fund", "type": "ETC", "sector": "Surowce"},
    "WEAT": {"name": "Teucrium Wheat Fund", "type": "ETF", "sector": "Surowce"},
    "IAU": {"name": "iShares Gold Trust", "type": "ETF", "sector": "Surowce"},
    "CPER": {"name": "United States Copper Index Fund", "type": "ETF", "sector": "Surowce"},
    "UGA": {"name": "United States Gasoline Fund", "type": "ETF", "sector": "Surowce"},
    "WOOD": {"name": "iShares Global Timber & Forestry ETF", "type": "ETF", "sector": "Surowce"},
    "JJC": {"name": "iPath Series B Bloomberg Copper Subindex Total Return ETN", "type": "ETN", "sector": "Surowce"},
    "JO": {"name": "iPath Series B Bloomberg Coffee Subindex Total Return ETN", "type": "ETN", "sector": "Surowce"},
    "CANE": {"name": "Teucrium Sugar Fund", "type": "ETF", "sector": "Surowce"},
    "NIB": {"name": "iPath Series B Bloomberg Cocoa Subindex Total Return ETN", "type": "ETN", "sector": "Surowce"},
    "KRBN": {"name": "KraneShares Global Carbon Strategy ETF", "type": "ETF", "sector": "Surowce"},

    # --- CRYPTO ---
    "BTC-USD": {"name": "Bitcoin", "type": "Kryptowaluta", "sector": "Crypto"},
    "ETH-USD": {"name": "Ethereum", "type": "Kryptowaluta", "sector": "Crypto"},
    "XRP-USD": {"name": "XRP", "type": "Kryptowaluta", "sector": "Crypto"},
    "SOL-USD": {"name": "Solana", "type": "Kryptowaluta", "sector": "Crypto"},
    "BCH-USD": {"name": "Bitcoin Cash", "type": "Kryptowaluta", "sector": "Crypto"},
    "LTC-USD": {"name": "Litecoin", "type": "Kryptowaluta", "sector": "Crypto"},
    "ADA-USD": {"name": "Cardano", "type": "Kryptowaluta", "sector": "Crypto"},
    "DOGE-USD": {"name": "Dogecoin", "type": "Kryptowaluta", "sector": "Crypto"},
    "BNB-USD": {"name": "Binance Coin", "type": "Kryptowaluta", "sector": "Crypto"},
    "DOT-USD": {"name": "Polkadot", "type": "Kryptowaluta", "sector": "Crypto"},
    "MATIC-USD": {"name": "Polygon", "type": "Kryptowaluta", "sector": "Crypto"},
    "AVAX-USD": {"name": "Avalanche", "type": "Kryptowaluta", "sector": "Crypto"},
    "LINK-USD": {"name": "Chainlink", "type": "Kryptowaluta", "sector": "Crypto"},
    "UNI-USD": {"name": "Uniswap", "type": "Kryptowaluta", "sector": "Crypto"},

    # --- OTHER / NEW ---
    "PLTR": {"name": "Palantir Technologies", "type": "Akcja (US)", "sector": "IT"},
    "CRWD": {"name": "CrowdStrike", "type": "Akcja (US)", "sector": "Cyberbezpieczeństwo"},
    "PANW": {"name": "Palo Alto Networks", "type": "Akcja (US)", "sector": "Cyberbezpieczeństwo"},
    "SMCI": {"name": "Super Micro Computer", "type": "Akcja (US)", "sector": "IT"},
    "URA": {"name": "Global X Uranium ETF", "type": "ETF", "sector": "Surowce"},
    "IEF": {"name": "iShares 7-10 Year Treasury Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "SHY": {"name": "iShares 1-3 Year Treasury Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "IEI": {"name": "iShares 3-7 Year Treasury Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "BND": {"name": "Vanguard Total Bond Market ETF", "type": "ETF", "sector": "Obligacje"},
    "AGG": {"name": "iShares Core U.S. Aggregate Bond ETF", "type": "ETF", "sector": "Obligacje"},
    "RACE": {"name": "Ferrari", "type": "Akcja (IT)", "sector": "Motoryzacja"},
    "AIR.PA": {"name": "Airbus", "type": "Akcja (FR)", "sector": "Lotnictwo"},
    "SIE.DE": {"name": "Siemens", "type": "Akcja (DE)", "sector": "Przemysł"},
    "JPM": {"name": "JPMorgan Chase", "type": "Akcja (US)", "sector": "Finanse"},
    "JNJ": {"name": "Johnson & Johnson", "type": "Akcja (US)", "sector": "Ochrona Zdrowia"},
    "CVX": {"name": "Chevron", "type": "Akcja (US)", "sector": "Paliwa"},
    "DIS": {"name": "Walt Disney", "type": "Akcja (US)", "sector": "Rozrywka"},
    "NFLX": {"name": "Netflix", "type": "Akcja (US)", "sector": "Media"},
    "GS": {"name": "Goldman Sachs", "type": "Akcja (US)", "sector": "Finanse"},
    "MS": {"name": "Morgan Stanley", "type": "Akcja (US)", "sector": "Finanse"},
    "LVMUY": {"name": "LVMH (ADR)", "type": "Akcja (FR)", "sector": "Dobra luksusowe"},
    "^VIX": {"name": "CBOE Volatility Index", "type": "Indeks", "sector": "Indeks"},
    "DX-Y.NYB": {"name": "US Dollar Index", "type": "Indeks", "sector": "Waluty"},
}

import json
from pathlib import Path

# ... (rest of imports)

# ======================================================
# 10. FAVORITES MANAGEMENT (USER DEFINED)
# ======================================================
_FAVORITES_FILE = Path(__file__).parent / "user_favorites.json"

def _load_favorites() -> List[str]:
    """Loads favorites from JSON file."""
    if _FAVORITES_FILE.exists():
        try:
            with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_favorites(favorites: List[str]) -> None:
    """Saves favorites to JSON file."""
    try:
        with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f)
    except Exception as e:
        print(f"Error saving favorites: {e}")

# Initialize FAVORITES from file or empty list
FAVORITES = _load_favorites()

# If file doesn't exist, initialize with defaults (TECH_GIANTS) to avoid empty list on update
if not FAVORITES and not _FAVORITES_FILE.exists():
    FAVORITES = list(TECH_GIANTS)
    _save_favorites(FAVORITES)

# Helper functions for managing favorites
def add_favorite(symbol: str) -> None:
    """Adds a symbol to favorites and saves to file."""
    if symbol not in FAVORITES:
        FAVORITES.append(symbol)
        _save_favorites(FAVORITES)

def remove_favorite(symbol: str) -> None:
    """Removes a symbol from favorites and saves to file."""
    if symbol in FAVORITES:
        FAVORITES.remove(symbol)
        _save_favorites(FAVORITES)

def get_favorite_descriptions() -> Dict[str, str]:
    """Returns a dictionary of descriptions for current favorites."""
    return {
        symbol: INSTRUMENT_METADATA.get(symbol, {}).get("name", symbol)
        for symbol in FAVORITES
    }

# For backward compatibility (Telegram Bot uses this dict directly)
# Note: This dict won't auto-update if FAVORITES changes unless rebuilt.
# It is recommended to use get_favorite_descriptions() instead.
FAVORITE_DESCRIPTIONS = get_favorite_descriptions()

