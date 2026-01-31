import unittest
import importlib

class TestBasicImports(unittest.TestCase):

    def test_import_main(self):
        try:
            import app.main
        except ImportError as e:
            self.fail(f"Failed to import app.main: {e}")

    def test_import_config(self):
        try:
            import app.config
        except ImportError as e:
            self.fail(f"Failed to import app.config: {e}")

    def test_import_data_engine(self):
        try:
            import app.data.data_engine
        except ImportError as e:
            self.fail(f"Failed to import app.data.data_engine: {e}")

    def test_import_strategy_engine(self):
        try:
            import app.strategy.engine
        except ImportError as e:
            self.fail(f"Failed to import app.strategy.engine: {e}")

if __name__ == "__main__":
    unittest.main()
