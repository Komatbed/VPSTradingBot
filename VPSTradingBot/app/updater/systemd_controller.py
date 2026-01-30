import subprocess
import logging
import os

logger = logging.getLogger("updater.systemd")

class SystemdController:
    def __init__(self, service_name: str = "tradingbot"):
        self.service_name = service_name

    def _run_command(self, action: str) -> bool:
        """
        Runs systemctl command. Requires sudo permissions for the user.
        """
        try:
            # Check if we are on Linux/Systemd
            if os.name == 'nt':
                logger.warning("Windows detected. Systemd commands skipped.")
                return True

            cmd = ["sudo", "systemctl", action, self.service_name]
            logger.info(f"Executing: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to {action} {self.service_name}: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Systemd error: {e}")
            return False

    def restart(self) -> bool:
        return self._run_command("restart")

    def stop(self) -> bool:
        return self._run_command("stop")

    def start(self) -> bool:
        return self._run_command("start")

    def is_active(self) -> bool:
        if os.name == 'nt':
            return True
        try:
            cmd = ["systemctl", "is-active", self.service_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.strip() == "active"
        except Exception:
            return False
