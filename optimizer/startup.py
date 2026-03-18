"""
startup.py — WinOptimizerPro 9
Gestión de programas de inicio de Windows.
"""

import json
import winreg
import subprocess
import logging
from typing import Optional

from .core import PowerShellRunner, RegistryEditor

logger = logging.getLogger(__name__)

HKCU_RUN_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
HKLM_RUN_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
HKCU_DISABLED_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run_Disabled"
HKLM_DISABLED_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run_Disabled"


class StartupManager:
    """Gestiona los programas que se inician automáticamente con Windows."""

    def __init__(self) -> None:
        self._tracker: list[dict] = []

    # ------------------------------------------------------------------
    # Métodos públicos principales
    # ------------------------------------------------------------------

    def get_startup_items(self) -> list[dict]:
        """Retorna todos los ítems de inicio combinando registro y PowerShell.

        Cada ítem: {name, command, enabled, location, publisher}
        """
        items: list[dict] = []
        seen: set[str] = set()

        for item in self.get_startup_items_registry():
            key = f"{item['name']}|{item['location']}"
            if key not in seen:
                seen.add(key)
                items.append(item)

        for item in self.get_startup_items_powershell():
            key = f"{item['name']}|{item['location']}"
            if key not in seen:
                seen.add(key)
                items.append(item)

        return items

    def get_startup_items_registry(self) -> list[dict]:
        """Lee ítems de inicio directamente desde el registro HKCU y HKLM."""
        items: list[dict] = []

        sources = [
            (winreg.HKEY_CURRENT_USER, HKCU_RUN_PATH, "HKCU_Run", True),
            (winreg.HKEY_LOCAL_MACHINE, HKLM_RUN_PATH, "HKLM_Run", True),
            (winreg.HKEY_CURRENT_USER, HKCU_DISABLED_PATH, "HKCU_Run", False),
            (winreg.HKEY_LOCAL_MACHINE, HKLM_DISABLED_PATH, "HKLM_Run", False),
        ]

        for hive, path, location, enabled in sources:
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
            except OSError:
                continue

            try:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                        items.append({
                            "name": name,
                            "command": value,
                            "enabled": enabled,
                            "location": location,
                            "publisher": self._get_publisher(value),
                        })
                        index += 1
                    except OSError:
                        break
            finally:
                winreg.CloseKey(key)

        return items

    def get_startup_items_powershell(self) -> list[dict]:
        """Obtiene ítems de inicio via CIM (Win32_StartupCommand)."""
        cmd = (
            "Get-CimInstance Win32_StartupCommand "
            "| Select-Object Name, Command, Location, User "
            "| ConvertTo-Json -Depth 2"
        )
        success, stdout, stderr = PowerShellRunner.run(cmd, timeout=30)

        if not success or not stdout.strip():
            logger.warning("PowerShell startup query falló: %s", stderr)
            return []

        try:
            raw = json.loads(stdout)
        except json.JSONDecodeError as exc:
            logger.warning("JSON inválido en startup PS: %s", exc)
            return []

        if isinstance(raw, dict):
            raw = [raw]

        items: list[dict] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            location_raw = (entry.get("Location") or "").lower()
            location = self._map_ps_location(location_raw)
            command = entry.get("Command") or ""
            items.append({
                "name": entry.get("Name") or "",
                "command": command,
                "enabled": True,
                "location": location,
                "publisher": self._get_publisher(command),
            })

        return items

    def disable_item(self, name: str, location: str) -> bool:
        """Deshabilita un ítem de inicio moviéndolo a la clave _Disabled.

        Args:
            name: Nombre del valor en el registro.
            location: "HKCU_Run" o "HKLM_Run".

        Returns:
            True si la operación fue exitosa.
        """
        hive, src_path, dst_path = self._resolve_paths(location)
        if hive is None:
            logger.error("Ubicación no soportada para disable: %s", location)
            return False

        try:
            src_key = winreg.OpenKey(hive, src_path, 0, winreg.KEY_READ)
            value, reg_type = winreg.QueryValueEx(src_key, name)
            winreg.CloseKey(src_key)
        except OSError as exc:
            logger.error("No se pudo leer '%s' de %s: %s", name, src_path, exc)
            return False

        try:
            dst_key = winreg.CreateKey(hive, dst_path)
            winreg.SetValueEx(dst_key, name, 0, reg_type, value)
            winreg.CloseKey(dst_key)
        except OSError as exc:
            logger.error("No se pudo escribir en _Disabled: %s", exc)
            return False

        try:
            del_key = winreg.OpenKey(hive, src_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(del_key, name)
            winreg.CloseKey(del_key)
        except OSError as exc:
            logger.warning("No se eliminó el original '%s': %s", name, exc)

        self._tracker.append({"action": "disable", "name": name, "location": location})
        logger.info("Ítem deshabilitado: %s (%s)", name, location)
        return True

    def enable_item(self, name: str, location: str) -> bool:
        """Rehabilita un ítem de inicio desde la clave _Disabled.

        Args:
            name: Nombre del valor en el registro.
            location: "HKCU_Run" o "HKLM_Run".

        Returns:
            True si la operación fue exitosa.
        """
        hive, run_path, disabled_path = self._resolve_paths(location)
        if hive is None:
            logger.error("Ubicación no soportada para enable: %s", location)
            return False

        try:
            src_key = winreg.OpenKey(hive, disabled_path, 0, winreg.KEY_READ)
            value, reg_type = winreg.QueryValueEx(src_key, name)
            winreg.CloseKey(src_key)
        except OSError as exc:
            logger.error("No se pudo leer '%s' de _Disabled: %s", name, exc)
            return False

        try:
            dst_key = winreg.OpenKey(hive, run_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(dst_key, name, 0, reg_type, value)
            winreg.CloseKey(dst_key)
        except OSError as exc:
            logger.error("No se pudo restaurar '%s' en Run: %s", name, exc)
            return False

        try:
            del_key = winreg.OpenKey(hive, disabled_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(del_key, name)
            winreg.CloseKey(del_key)
        except OSError as exc:
            logger.warning("No se eliminó de _Disabled '%s': %s", name, exc)

        self._tracker.append({"action": "enable", "name": name, "location": location})
        logger.info("Ítem habilitado: %s (%s)", name, location)
        return True

    def get_startup_impact(self, name: str) -> str:
        """Retorna el impacto de inicio de un programa: Alto, Medio, Bajo o Desconocido."""
        cmd = (
            f'Get-StartupApps | Where-Object {{$_.AppName -like "*{name}*"}} '
            "| Select-Object StartupImpact | ConvertTo-Json -Depth 1"
        )
        success, stdout, _ = PowerShellRunner.run(cmd, timeout=20)

        if not success or not stdout.strip():
            return "Desconocido"

        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                data = data[0] if data else {}
            impact_raw = str(data.get("StartupImpact", "")).lower()
        except (json.JSONDecodeError, IndexError):
            return "Desconocido"

        mapping = {"high": "Alto", "medium": "Medio", "low": "Bajo", "none": "Bajo"}
        return mapping.get(impact_raw, "Desconocido")

    def open_task_manager_startup(self) -> None:
        """Abre el Administrador de tareas en la pestaña de inicio."""
        subprocess.Popen(["taskmgr.exe", "/7"])

    # ------------------------------------------------------------------
    # Métodos privados auxiliares
    # ------------------------------------------------------------------

    def _resolve_paths(
        self, location: str
    ) -> tuple[Optional[int], str, str]:
        """Retorna (hive, run_path, disabled_path) según location."""
        if location == "HKCU_Run":
            return winreg.HKEY_CURRENT_USER, HKCU_RUN_PATH, HKCU_DISABLED_PATH
        if location == "HKLM_Run":
            return winreg.HKEY_LOCAL_MACHINE, HKLM_RUN_PATH, HKLM_DISABLED_PATH
        return None, "", ""

    def _get_publisher(self, command: str) -> str:
        """Extrae el publisher del ejecutable usando FileVersionInfo vía PowerShell."""
        if not command:
            return ""

        exe = command.strip().strip('"').split('"')[0].split()[0]
        if not exe.lower().endswith(".exe"):
            return ""

        cmd = (
            f'(Get-Item "{exe}" -ErrorAction SilentlyContinue)'
            ".VersionInfo.CompanyName"
        )
        success, stdout, _ = PowerShellRunner.run(cmd, timeout=10)
        if success and stdout.strip():
            return stdout.strip()
        return ""

    def _map_ps_location(self, location_raw: str) -> str:
        """Normaliza el campo Location de CIM a las constantes internas."""
        if "hkcu" in location_raw or "current_user" in location_raw:
            return "HKCU_Run"
        if "hklm" in location_raw or "local_machine" in location_raw:
            return "HKLM_Run"
        if "startup" in location_raw:
            return "Startup_Folder"
        if "task" in location_raw or "scheduler" in location_raw:
            return "Task_Scheduler"
        return "HKLM_Run"
