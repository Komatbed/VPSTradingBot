import os
import sys

# Add app to path
sys.path.append(os.getcwd())

try:
    from app.data.instrument_universe import DEFAULT_INSTRUMENT_UNIVERSE
    print(f"DEFAULT_INSTRUMENT_UNIVERSE length: {len(DEFAULT_INSTRUMENT_UNIVERSE)}")
except Exception as e:
    print(f"Error importing DEFAULT_INSTRUMENT_UNIVERSE: {e}")

try:
    from app.config import Config
    # Simulate Config.from_env() behavior
    data_source = os.getenv("DATA_SOURCE", "yahoo")
    print(f"DATA_SOURCE: {data_source}")

    config = Config.from_env()
    print(f"Config instruments count: {len(config.instruments)}")
    print(f"First 5 instruments: {config.instruments[:5]}")

    if len(config.instruments) == 0:
        print("ERROR: Config loaded 0 instruments!")
    else:
        print("SUCCESS: Config loaded instruments correctly.")
except Exception as e:
    print(f"Error loading Config: {e}")
