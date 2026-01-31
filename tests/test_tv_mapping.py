import unittest
from app.data.tradingview_mapping import to_tradingview_symbol

class TestTradingViewMapping(unittest.TestCase):
    def test_commodities(self):
        self.assertEqual(to_tradingview_symbol("GC=F"), "COMEX:GC1!")
        self.assertEqual(to_tradingview_symbol("CL=F"), "NYMEX:CL1!")

    def test_polish_stocks(self):
        self.assertEqual(to_tradingview_symbol("PKO.WA"), "GPW:PKO")
        self.assertEqual(to_tradingview_symbol("CDR.WA"), "GPW:CDR")

    def test_european_stocks(self):
        self.assertEqual(to_tradingview_symbol("SAP.DE"), "XETR:SAP")
        self.assertEqual(to_tradingview_symbol("NESN.SW"), "SIX:NESN")
        self.assertEqual(to_tradingview_symbol("MC.PA"), "EURONEXT:MC")

    def test_crypto(self):
        self.assertEqual(to_tradingview_symbol("BTC-USD"), "BINANCE:BTCUSDT")
        self.assertEqual(to_tradingview_symbol("ETH-USD"), "BINANCE:ETHUSDT")

    def test_us_stocks(self):
        self.assertEqual(to_tradingview_symbol("AAPL"), "AAPL")
        self.assertEqual(to_tradingview_symbol("MSFT"), "MSFT")

    def test_indices(self):
        self.assertEqual(to_tradingview_symbol("^GSPC"), "SP:SPX")
        self.assertEqual(to_tradingview_symbol("^GDAXI"), "XETR:DAX")
        self.assertEqual(to_tradingview_symbol("^VIX"), "TVC:VIX")
        self.assertEqual(to_tradingview_symbol("DX-Y.NYB"), "TVC:DXY")

    def test_special_stocks(self):
        self.assertEqual(to_tradingview_symbol("LVMUY"), "OTC:LVMUY")
        self.assertEqual(to_tradingview_symbol("^NDX"), "NASDAQ:NDX")

if __name__ == "__main__":
    unittest.main()