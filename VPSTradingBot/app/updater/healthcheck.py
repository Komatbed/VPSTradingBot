import logging
import sys
import importlib

logger = logging.getLogger("updater.health")

def run_healthcheck() -> bool:
    """
    Verifies that the application can import core modules and connect to config.
    """
    logger.info("Running post-update healthcheck...")
    try:
        # Check Config
        from app.config import Config
        Config.from_env()
        
        # Check Imports
        importlib.import_module("app.main")
        importlib.import_module("app.telegram_bot.bot")
        
        logger.info("Healthcheck PASSED")
        return True
    except Exception as e:
        logger.error(f"Healthcheck FAILED: {e}")
        return False

if __name__ == "__main__":
    if run_healthcheck():
        sys.exit(0)
    else:
        sys.exit(1)
