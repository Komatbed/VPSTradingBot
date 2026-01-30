import os
import shutil
import glob
import logging
from pathlib import Path

logger = logging.getLogger("updater.guard")

class FileGuard:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)

    def cleanup_cache(self):
        """Clears cache/ directory"""
        self._clean_dir(self.root / "cache")

    def cleanup_backtests(self):
        """Clears backtests/ directory"""
        self._clean_dir(self.root / "backtests")
    
    def cleanup_ml(self):
        """Clears ml_models/ directory"""
        # Assuming ml/models based on previous context
        self._clean_dir(self.root / "app" / "ml" / "models")

    def _clean_dir(self, path: Path):
        if not path.exists():
            return
        logger.info(f"Cleaning {path}...")
        try:
            for item in path.glob("*"):
                if item.is_file() and item.name != ".gitkeep":
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        except Exception as e:
            logger.error(f"Failed to clean {path}: {e}")

    def verify_permissions(self) -> bool:
        """Check if we have write access to critical dirs"""
        return os.access(self.root, os.W_OK)
