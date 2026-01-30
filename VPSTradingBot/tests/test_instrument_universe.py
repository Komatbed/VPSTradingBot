import unittest
from app.data.instrument_universe import INSTRUMENT_METADATA

class TestInstrumentUniverse(unittest.TestCase):

    def test_metadata_structure(self):
        self.assertTrue(len(INSTRUMENT_METADATA) > 0, "Metadata should not be empty")
        
        for ticker, data in INSTRUMENT_METADATA.items():
            self.assertIsInstance(ticker, str, f"Ticker {ticker} should be a string")
            self.assertIsInstance(data, dict, f"Data for {ticker} should be a dict")
            
            # Check required fields
            self.assertIn("name", data, f"Missing 'name' for {ticker}")
            self.assertIn("type", data, f"Missing 'type' for {ticker}")
            self.assertIn("sector", data, f"Missing 'sector' for {ticker}")
            
            # Check types
            self.assertIsInstance(data["name"], str)
            self.assertIsInstance(data["type"], str)
            # Sector can be None or string? Based on code seen earlier, it seems to be string.
            self.assertIsInstance(data["sector"], str)

    def test_tickers_format(self):
        # Basic sanity check for tickers
        for ticker in INSTRUMENT_METADATA.keys():
            self.assertTrue(len(ticker) > 0)
            self.assertTrue(ticker.strip() == ticker)

if __name__ == "__main__":
    unittest.main()
