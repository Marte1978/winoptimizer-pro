"""
Módulo de backup y restauración.
Crea puntos de restauración del sistema y respalda configuraciones antes de modificarlas.
"""
import winreg
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .core import PowerShellRunner

logger = logging.getLogger("WinOptimizer")

BACKUP_DIR = Path(
    __import__("os").environ.get("APPDATA", "C:/Users")
) / "WinOptimizer" / "backups"


class BackupManager:
    """Gestiona la creación de puntos de restauración y respaldos del registro."""

    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self.ps = PowerShellRunner()
        self.progress_cb = progress_callback or (lambda msg, pct: None)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def create_restore_point(self, description: str = "WinOptimizer Backup") -> bool:
        """
        Crea un punto de restauración del sistema.
        Requiere que el Servicio de Instantáneas de Volumen esté activo.
        """
        self.progress_cb("Habilitando Protección del Sistema...", 10)

        # Habilitar protección del sistema en C:
        enable_cmd = (
            "Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue; "
            "vssadmin list shadowstorage | Out-Null"
        )
        self.ps.run(enable_cmd)

        self.progress_cb(f"Creando punto de restauración: '{description}'...", 30)

        # Crear punto de restauración
        create_cmd = (
            f"Checkpoint-Computer -Description '{description}' "
            f"-RestorePointType MODIFY_SETTINGS -ErrorAction Stop"
        )
        ok, out, err = self.ps.run(create_cmd, timeout=180)

        if ok:
            self.progress_cb("✅ Punto de restauración creado exitosamente.", 100)
            logger.info(f"Punto de restauración creado: {description}")
            return True
        else:
            # Algunos sistemas tienen un límite de 1 punto por 24 horas
            if "wait" in err.lower() or "24" in err:
                logger.warning("Ya existe un punto de restauración reciente (< 24h).")
                self.progress_cb("⚠️ Ya hay un punto de restauración reciente (< 24h).", 100)
                return True  # Aceptable: ya hay protección
            logger.error(f"Error creando punto de restauración: {err[:300]}")
            self.progress_cb(f"❌ Error: {err[:100]}", 100)
            return False

    def backup_registry_keys(self, keys: list[dict]) -> dict:
        """
        Respalda valores del registro antes de modificarlos.
        keys: lista de {'hive': str, 'path': str, 'name': str}
        Retorna: dict con los valores originales.
        """
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
            "entries": [],
        }

        for key_info in keys:
            hive = key_info.get("hive", "HKLM")
            path = key_info.get("path", "")
            name = key_info.get("name", "")

            hive_map = {
                "HKLM": winreg.HKEY_LOCAL_MACHINE,
                "HKCU": winreg.HKEY_CURRENT_USER,
            }
            hive_key = hive_map.get(hive)
            if not hive_key:
                continue

            try:
                with winreg.OpenKey(hive_key, path) as k:
                    value, reg_type = winreg.QueryValueEx(k, name)
                    backup_data["entries"].append({
                        "hive": hive,
                        "path": path,
                        "name": name,
                        "value": value,
                        "reg_type": reg_type,
                        "existed": True,
                    })
            except FileNotFoundError:
                backup_data["entries"].append({
                    "hive": hive,
                    "path": path,
                    "name": name,
                    "value": None,
                    "reg_type": None,
                    "existed": False,
                })
            except Exception as e:
                logger.warning(f"No se pudo respaldar {hive}\\{path}\\{name}: {e}")

        # Guardar en archivo
        backup_file = BACKUP_DIR / f"registry_backup_{self._session_id}.json"
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Registro respaldado en: {backup_file}")
        except Exception as e:
            logger.error(f"Error guardando respaldo del registro: {e}")

        return backup_data

    def restore_registry_from_backup(self, backup_data: dict) -> tuple[int, int]:
        """
        Restaura los valores del registro desde un respaldo.
        Retorna: (exitosos, fallidos)
        """
        entries = backup_data.get("entries", [])
        ok_count = 0
        fail_count = 0

        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }

        for entry in entries:
            hive_key = hive_map.get(entry.get("hive", ""))
            if not hive_key:
                continue

            path = entry["path"]
            name = entry["name"]

            try:
                if not entry["existed"]:
                    # Eliminar el valor si no existía antes
                    try:
                        with winreg.OpenKey(hive_key, path, 0, winreg.KEY_WRITE) as k:
                            winreg.DeleteValue(k, name)
                    except FileNotFoundError:
                        pass
                    ok_count += 1
                else:
                    # Restaurar al valor original
                    with winreg.OpenKey(hive_key, path, 0, winreg.KEY_WRITE) as k:
                        winreg.SetValueEx(k, name, 0, entry["reg_type"], entry["value"])
                    ok_count += 1
            except Exception as e:
                logger.error(f"Error restaurando {entry['hive']}\\{path}\\{name}: {e}")
                fail_count += 1

        return ok_count, fail_count

    def load_latest_backup(self) -> Optional[dict]:
        """Carga el respaldo más reciente de la sesión actual."""
        backup_file = BACKUP_DIR / f"registry_backup_{self._session_id}.json"
        if backup_file.exists():
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def list_restore_points(self) -> list[dict]:
        """Lista los puntos de restauración disponibles."""
        ok, out, _ = self.ps.run(
            "Get-ComputerRestorePoint | Select-Object -Property Description,CreationTime | "
            "ConvertTo-Json -Compress"
        )
        if ok and out.strip():
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                return data
            except Exception:
                pass
        return []

    def get_backup_dir(self) -> Path:
        return BACKUP_DIR
