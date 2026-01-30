from __future__ import annotations

from typing import Dict, Tuple


# Mapping: Yahoo Ticker -> (TradingView Ticker, Display Name)
_MAPPING: Dict[str, Tuple[str, str]] = {
    # Commodities (Futures)
    "GC=F": ("COMEX:GC1!", "GOLD (Złoto)"),
    "SI=F": ("COMEX:SI1!", "SILVER (Srebro)"),
    "PL=F": ("NYMEX:PL1!", "PLATINUM (Platyna)"),
    "PA=F": ("NYMEX:PA1!", "PALLADIUM (Pallad)"),
    "HG=F": ("COMEX:HG1!", "COPPER (Miedź)"),
    "CL=F": ("NYMEX:CL1!", "OIL.WTI (Ropa WTI)"),
    "BZ=F": ("ICEEUR:B1!", "OIL (Ropa Brent)"),
    "NG=F": ("NYMEX:NG1!", "NATGAS (Gaz Ziemny)"),
    "HO=F": ("NYMEX:HO1!", "HEATINGOIL (Olej Opałowy)"),
    "RB=F": ("NYMEX:RB1!", "GASOLINE (Benzyna)"),
    "ZC=F": ("CBOT:ZC1!", "CORN (Kukurydza)"),
    "ZS=F": ("CBOT:ZS1!", "SOYBEAN (Soja)"),
    "ZW=F": ("CBOT:ZW1!", "WHEAT (Pszenica)"),
    "SB=F": ("ICEUS:SB1!", "SUGAR (Cukier)"),
    "KC=F": ("ICEUS:KC1!", "COFFEE (Kawa)"),
    "CC=F": ("ICEUS:CC1!", "COCOA (Kakao)"),
    "CT=F": ("ICEUS:CT1!", "COTTON (Bawełna)"),
    "ZR=F": ("CBOT:ZR1!", "RICE (Ryż)"),
    
    # Indices
    "^GSPC": ("SP:SPX", "US500 (S&P 500)"),
    "^NDX": ("NASDAQ:NDX", "US100 (Nasdaq 100)"),
    "^DJI": ("DJ:DJI", "US30 (Dow Jones)"),
    "^RUT": ("RUSSELL:RUT", "US2000 (Russell 2000)"),
    "^DAX": ("XETR:DAX", "DE30 (DAX)"),
    "^FTSE": ("FTSE:UKX", "UK100 (FTSE 100)"),
    "^N225": ("TVC:NI225", "JAP225 (Nikkei 225)"),
    "^STOXX50E": ("TVC:SX5E", "EU50 (Euro Stoxx 50)"),
    "^GDAXI": ("XETR:DAX", "DE40 (DAX)"),
    "^VIX": ("TVC:VIX", "VIX (Volatility Index)"),
    "DX-Y.NYB": ("TVC:DXY", "USDX (Dollar Index)"),
    
    # Special Stocks
    "BRK-B": ("NYSE:BRK.B", "BERKSHIRE (Berkshire B)"),
    "BRK-A": ("NYSE:BRK.A", "BERKSHIRE (Berkshire A)"),
    "LVMUY": ("OTC:LVMUY", "LVMH (ADR)"),
}

# Mapping for Polish stocks: Ticker -> (XTB Symbol, Polish Name)
_POLISH_NAMES: Dict[str, Tuple[str, str]] = {
    "PKO.WA": ("PKO", "PKO BP"),
    "SPL.WA": ("SPL", "Santander Bank Polska"),
    "ALR.WA": ("ALR", "Alior Bank"),
    "MBK.WA": ("MBK", "mBank"),
    "JSW.WA": ("JSW", "JSW"),
    "LPP.WA": ("LPP", "LPP"),
    "PGE.WA": ("PGE", "PGE"),
    "TPE.WA": ("TPE", "Tauron"),
    "CCC.WA": ("CCC", "CCC"),
    "CPS.WA": ("CPS", "Cyfrowy Polsat"),
    "OPL.WA": ("OPL", "Orange Polska"),
    "ACP.WA": ("ACP", "Asseco Poland"),
    "BHW.WA": ("BHW", "Citi Handlowy"),
    "ING.WA": ("ING", "ING Bank Śląski"),
    "BOS.WA": ("BOS", "BOŚ Bank"),
    "ENA.WA": ("ENA", "Enea"),
    "ENG.WA": ("ENG", "Energa"),
    "KER.WA": ("KER", "Kernel"),
    "TXT.WA": ("TXT", "Text SA"),
    "MAB.WA": ("MAB", "Mabion"),
    "MRC.WA": ("MRC", "Mercator"),
    "PKP.WA": ("PKP", "PKP Cargo"),
    "TEN.WA": ("TEN", "Ten Square Games"),
    "PLW.WA": ("PLW", "PlayWay"),
    "DNP.WA": ("DNP", "Dino"),
    "ATT.WA": ("ATT", "Atende"),
    "STP.WA": ("STP", "Stalprodukt"),
    "CIG.WA": ("CIG", "CI Games"),
    "KTY.WA": ("KTY", "Grupa Kęty"),
    "MLP.WA": ("MLP", "MLP Group"),
    "ERB.WA": ("ERB", "Erbud"),
    "GPW.WA": ("GPW", "Giełda Papierów Wartościowych"),
    "SLV.WA": ("SLV", "Selvita"),
    "PXM.WA": ("PXM", "Polimex"),
    "MFO.WA": ("MFO", "MFO"),
    "AMC.WA": ("AMC", "Amica"),
    "KGH.WA": ("KGH", "KGHM Polska Miedź"),
    "PEO.WA": ("PEO", "Bank Pekao"),
    "PZU.WA": ("PZU", "PZU"),
    "KRU.WA": ("KRU", "Kruk"),
    "MIL.WA": ("MIL", "Bank Millennium"),
    "XTB.WA": ("XTB", "XTB"),
    "ALE.WA": ("ALE", "Allegro"),

    "CDR.WA": ("CDR", "CD Projekt"),
    "ETFBW20TR.WA": ("ETFBW20", "ETF WIG20"),
}


def to_tradingview_symbol(symbol: str) -> str:
    """Returns a TradingView-compatible ticker."""
    if symbol in _MAPPING:
        return _MAPPING[symbol][0]
        
    if symbol.endswith(".WA"):
        base = symbol[:-3]
        return f"GPW:{base}"

    if symbol.endswith(".DE"):
        base = symbol[:-3]
        return f"XETR:{base}"

    if symbol.endswith(".SW"):
        base = symbol[:-3]
        return f"SIX:{base}"

    if symbol.endswith(".PA"):
        base = symbol[:-3]
        return f"EURONEXT:{base}"
        
    if symbol.endswith("-USD"):
        base = symbol.split("-")[0]
        return f"BINANCE:{base}USDT"
        
    if symbol.endswith("=X"):
        base = symbol.replace("=X", "")
        return f"FX:{base}"
        
    if "_" in symbol:
        base = symbol.replace("_", "")
        return f"FX:{base}"
        
    return symbol


def get_display_name(symbol: str) -> str:
    """Returns a more intuitive display name."""
    if symbol in _MAPPING:
        return _MAPPING[symbol][1]
    
    # Check specific Polish stocks mapping
    if symbol in _POLISH_NAMES:
        xtb, name = _POLISH_NAMES[symbol]
        return f"{xtb} ({name})"
        
    if symbol.endswith(".WA"):
        base = symbol.replace(".WA", "")
        # Fallback if not in explicit list
        return f"{base} ({base} PL)"
        
    if symbol.endswith("-USD"):
        base = symbol.replace("-USD", "")
        return f"{base} ({base} Crypto)"
        
    if symbol.endswith("=X"):
        base = symbol.replace("=X", "")
        return f"{base} ({base} Forex)"
        
    return symbol


def get_tv_link(symbol: str) -> str:
    """Returns a full TradingView chart link."""
    tv_symbol = to_tradingview_symbol(symbol)
    return f"https://www.tradingview.com/chart/?symbol={tv_symbol}"