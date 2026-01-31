import tarfile
import os
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("updater.rollback")

class RollbackManager:
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    def create_snapshot(self) -> str:
        """Creates a .tar.gz snapshot of the current directory (excluding backups)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.backup_dir / f"backup_{timestamp}.tar.gz"
        
        logger.info(f"Creating snapshot: {filename}")
        try:
            with tarfile.open(filename, "w:gz") as tar:
                # Add everything in current dir, exclude .git and backups
                for item in os.listdir("."):
                    if item in [".git", "backups", ".venv", "__pycache__"]:
                        continue
                    tar.add(item)
            return str(filename)
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return ""

    def restore_snapshot(self, snapshot_path: str) -> bool:
        """Restores files from snapshot"""
        if not os.path.exists(snapshot_path):
            logger.error("Snapshot not found")
            return False
            
        logger.info(f"Restoring from {snapshot_path}...")
        try:
            with tarfile.open(snapshot_path, "r:gz") as tar:
                tar.extractall(path=".")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def get_latest_snapshot(self) -> str:
        files = sorted(self.backup_dir.glob("backup_*.tar.gz"), key=os.path.getmtime, reverse=True)
        return str(files[0]) if files else ""
