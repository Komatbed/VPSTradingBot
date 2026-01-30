import logging
import threading
import time
import os
import json
from pathlib import Path
from typing import Optional, Tuple

from app.updater.git_manager import GitManager
from app.updater.file_guard import FileGuard
from app.updater.rollback import RollbackManager
from app.updater.systemd_controller import SystemdController
from app.updater.healthcheck import run_healthcheck

logger = logging.getLogger("updater")

class UpdateManager:
    def __init__(self, service_name: str = "tradingbot"):
        self.git = GitManager()
        self.guard = FileGuard()
        self.rollback_mgr = RollbackManager()
        self.systemd = SystemdController(service_name)
        
        self._lock = threading.Lock()
        self._is_updating = False
        
        # Status file to persist state across restarts
        self.status_file = Path("update_status.json")
        
    def check_for_updates(self) -> Tuple[bool, str]:
        return self.git.check_updates()
        
    def get_status(self) -> str:
        if self._is_updating:
            return "Updating..."
        ver = self.git.get_current_version()
        active = self.systemd.is_active()
        return f"Version: {ver}\nService: {'Active' if active else 'Inactive'}"

    def perform_update(self, chat_id: Optional[str] = None) -> str:
        """
        Main update flow:
        1. Lock
        2. Snapshot
        3. Git Fetch & Reset
        4. Healthcheck
        5. Restart Systemd
        """
        if not self._lock.acquire(blocking=False):
            return "Update already in progress."
            
        try:
            self._is_updating = True
            logger.info("Starting update process...")
            
            # 1. Snapshot
            snapshot = self.rollback_mgr.create_snapshot()
            if not snapshot:
                return "Failed to create snapshot. Update aborted."
            
            # 2. Git Update
            if not self.git.update_hard():
                return "Git update failed."
            
            # 3. Healthcheck (Quick import check)
            import subprocess
            res = subprocess.run(["python", "-m", "app.updater.healthcheck"], capture_output=True)
            if res.returncode != 0:
                logger.error("Healthcheck failed. Rolling back.")
                self.rollback_mgr.restore_snapshot(snapshot)
                return f"Update failed healthcheck: {res.stderr.decode()}"
                
            # 4. Mark update pending (so we know on restart)
            self._write_status("pending_restart", snapshot, chat_id)
            
            # 5. Restart Service
            threading.Thread(target=self._restart_sequence).start()
            
            return "Update successful. System restarting..."
            
        except Exception as e:
            logger.error(f"Update exception: {e}")
            return f"Update error: {e}"
        finally:
            self._is_updating = False
            self._lock.release()

    def _restart_sequence(self):
        """Waits a bit for message to send, then restarts"""
        time.sleep(3)
        self.systemd.restart()

    def rollback(self) -> str:
        snapshot = self.rollback_mgr.get_latest_snapshot()
        if not snapshot:
            return "No snapshot found."
            
        if self.rollback_mgr.restore_snapshot(snapshot):
            threading.Thread(target=self._restart_sequence).start()
            return f"Restored {snapshot}. Restarting..."
        return "Restore failed."

    def _write_status(self, status: str, snapshot: str, chat_id: Optional[str] = None):
        with open(self.status_file, "w") as f:
            json.dump({
                "status": status, 
                "snapshot": snapshot, 
                "time": time.time(),
                "chat_id": chat_id
            }, f)
            
    def check_post_update(self) -> Tuple[Optional[str], Optional[str]]:
        """Called on startup to check if we just updated. Returns (message, chat_id)"""
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    data = json.load(f)
                if data.get("status") == "pending_restart":
                    # We just restarted after update
                    self._write_status("idle", data.get("snapshot"), None)
                    return (f"✅ System updated successfully to {self.git.get_current_version()}", data.get("chat_id"))
            except:
                pass
        return None, None
