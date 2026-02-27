"""
Sistema de logging para WinOptimizer.
Registra todos los cambios aplicados, errores y operaciones de reversión.
"""
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


LOG_DIR = Path(os.environ.get("APPDATA", "C:/Users")) / "WinOptimizer" / "logs"
CHANGES_FILE = LOG_DIR / "changes_history.json"


def setup_logger(name: str = "WinOptimizer") -> logging.Logger:
    """Configura y retorna el logger principal de la aplicación."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # Handler para archivo (debug completo)
    log_file = LOG_DIR / f"optimizer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # Handler para consola (solo info+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class ChangeTracker:
    """Rastrea todos los cambios aplicados para permitir reversión."""

    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._changes: list[dict] = self._load_history()
        self._session_changes: list[dict] = []

    def _load_history(self) -> list[dict]:
        if CHANGES_FILE.exists():
            try:
                with open(CHANGES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def record(
        self,
        category: str,
        action: str,
        description: str,
        revert_command: Optional[str] = None,
        status: str = "success",
    ) -> None:
        """Registra un cambio aplicado."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "action": action,
            "description": description,
            "revert_command": revert_command,
            "status": status,
        }
        self._changes.append(entry)
        self._session_changes.append(entry)
        self._save_history()

    def _save_history(self) -> None:
        try:
            with open(CHANGES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._changes, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_session_changes(self) -> list[dict]:
        """Retorna solo los cambios de la sesión actual."""
        return self._session_changes.copy()

    def get_revertible_changes(self) -> list[dict]:
        """Retorna cambios que tienen comando de reversión."""
        return [c for c in self._session_changes if c.get("revert_command")]

    def clear_session(self) -> None:
        self._session_changes = []

    def get_log_dir(self) -> Path:
        return LOG_DIR
