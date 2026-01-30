import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


def setup_logging() -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_path = logs_dir / f"{date_str}_system.log"
    
    # RotatingFileHandler: max 3MB, keep 3 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, 
        maxBytes=3 * 1024 * 1024,  # 3MB
        backupCount=3, 
        encoding="utf-8"
    )
    
    # Rotating Error Handler: max 5MB, keep 5 backups
    error_log_path = logs_dir / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)

    # StreamHandler: Only WARNING+ to prevent bloating bot_error.log (if stderr redirected)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)

    handlers = [
        file_handler,
        error_handler,
        stream_handler,
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )

