from typing import Dict

# Templates for different regimes
REGIME_TEMPLATES = {
    "LATE CYCLE / SOFT LANDING": {
        "description": (
            "The economy is slowing but growing. Inflation is sticky but not spiraling. "
            "Central banks are cautious. This is a stock-picker's market."
        ),
        "behavior": (
            "• **Equities:** Bifurcated. Quality Growth (Tech) acts defensive. Small caps struggle with rates.\n"
            "• **Bonds:** Volatile. Not a perfect hedge yet due to fiscal deficits.\n"
            "• **Commodities:** Mixed. Gold is a fiscal hedge. Oil is range-bound.\n"
            "• **Crypto:** High-beta liquidity proxy. Sensitive to 'higher for longer' fears."
        ),
        "baskets": {
            "Fiscal Hedge": ["GC=F", "BTC-USD", "SLV"],
            "Quality Growth": ["QQQ", "SOXX", "CIBR"], # Using ETFs generally available
            "Yield & Carry": ["SHY", "LQD"],
            "Anti-Fragile": ["^VIX", "USD"] # VIX and Cash
        },
        "caution": (
            "• Don't assume the first rate cut is bullish (it often signals recession).\n"
            "• Beware of 'Zombie Companies' with high debt.\n"
            "• Long-end bonds (TLT) face supply pressure."
        )
    },
    "REFLATION / OVERHEATING": {
        "description": (
            "Growth is accelerating, and inflation is rising again. "
            "Central banks may need to hike or hold rates high."
        ),
        "behavior": (
            "• **Equities:** Cyclicals outperform (Energy, Industrials, Banks).\n"
            "• **Bonds:** Bear market. Yields rise. Avoid duration.\n"
            "• **Commodities:** Bull market. Oil, Copper, Ags rally.\n"
            "• **Crypto:** Usually bullish as risk-on returns."
        ),
        "baskets": {
            "Inflation Hedge": ["DBC", "XLE", "COPX"],
            "Cyclical Value": ["XLF", "XLI", "IWM"],
            "Short Duration": ["SHY", "BIL"],
        },
        "caution": (
            "• Tech/Growth may lag due to higher discount rates.\n"
            "• Long bonds are dangerous.\n"
            "• Watch for Central Bank panic."
        )
    },
    "RECESSION / HARD LANDING": {
        "description": (
            "Growth collapses, unemployment rises. Deflation fears take over. "
            "Central banks cut rates aggressively."
        ),
        "behavior": (
            "• **Equities:** Bear market. Earnings collapse.\n"
            "• **Bonds:** Bull market. TLT is the king.\n"
            "• **Commodities:** Crash (demand destruction). Gold may hold as safety.\n"
            "• **Crypto:** Crash initially (liquidity shock), then maybe recovery."
        ),
        "baskets": {
            "Safety": ["TLT", "IEF", "GOVT"],
            "Defensive Equity": ["XLP", "XLV", "WMT"],
            "Cash": ["USD", "SHY"]
        },
        "caution": (
            "• Don't buy the dip too early.\n"
            "• Credit spreads widen (High Yield bonds crash).\n"
            "• Cash is king until the Fed pivots hard."
        )
    },
    "STAGFLATION": {
        "description": (
            "Worst of both worlds: Low growth + High inflation. "
            "Central banks are trapped."
        ),
        "behavior": (
            "• **Equities:** Real struggle. P/E compression + Earnings drop.\n"
            "• **Bonds:** Losers (inflation hurts coupons).\n"
            "• **Commodities:** The only winner (Energy, Food, Metals).\n"
            "• **Crypto:** Wildcard (Store of value vs Risk-off)."
        ),
        "baskets": {
            "Hard Assets": ["GLD", "SLV", "USO", "DBC"],
            "Value/Resources": ["XLE", "XME"],
            "Short Bonds": ["SHY"]
        },
        "caution": (
            "• Traditional 60/40 portfolio fails.\n"
            "• Avoid consumer discretionary (XLY).\n"
            "• Cash loses purchasing power."
        )
    },
    "TRANSITIONAL / MIXED SIGNALS": {
        "description": (
            "Indicators are conflicting. Market is seeking direction. "
            "Volatility clusters are likely."
        ),
        "behavior": (
            "• **Equities:** Range-bound or rotation-heavy.\n"
            "• **Bonds:** Range-bound.\n"
            "• **Commodities:** Idiosyncratic moves.\n"
            "• **Crypto:** Range-bound."
        ),
        "baskets": {
            "Diversified": ["VT", "BND"],
            "Quality": ["USMV", "QUAL"],
            "Alpha": ["Managed Futures", "Market Neutral"]
        },
        "caution": (
            "• Don't commit large size.\n"
            "• Wait for trend confirmation.\n"
            "• Preserve capital."
        )
    }
}

MACRO_DRIVERS = [
    "Sticky Disinflation (The 'Last Mile' Problem)",
    "Fiscal Dominance & Debt Issuance",
    "Geopolitical Fragmentation (Tariffs/Wars)",
    "AI CapEx Cycle (Tech Divergence)",
    "Central Bank Divergence (Fed vs ECB/BOJ)"
]

HISTORICAL_CONTEXT = {
    "LATE CYCLE / SOFT LANDING": "Parallel: 1995-1998 (Soft Landing -> Bubble) or 2006 (Late Cycle).",
    "REFLATION": "Parallel: 1970s Stop-Start or 2004-2006.",
    "RECESSION": "Parallel: 2008 or 2001 or 2020.",
    "STAGFLATION": "Parallel: 1973-1974 or late 1970s.",
    "TRANSITIONAL / MIXED SIGNALS": "Current state is highly unique due to post-COVID distortions."
}
