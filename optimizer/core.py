"""
Motor central de ejecución de optimizaciones.
Provee funciones base para ejecutar comandos PowerShell y modificar el registro.
"""
import subprocess
import winreg
import logging
import sys
from typing import Optional, Union

# Suprimir ventanas de consola al llamar subprocesos desde un exe sin consola
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

logger = logging.getLogger("WinOptimizer")


class PowerShellRunner:
    """Ejecuta comandos PowerShell con manejo de errores robusto."""

    @staticmethod
    def run(command: str, timeout: int = 120) -> tuple[bool, str, str]:
        """
        Ejecuta un comando PowerShell.
        Retorna: (éxito: bool, stdout: str, stderr: str)
        """
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NonInteractive",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-Command", command,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                creationflags=_NO_WINDOW,
            )
            success = result.returncode == 0
            if not success:
                logger.debug(f"PS error (code {result.returncode}): {result.stderr[:500]}")
            return success, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.warning(f"PowerShell timeout: {command[:100]}")
            return False, "", "Timeout al ejecutar comando"
        except Exception as e:
            logger.error(f"Error ejecutando PowerShell: {e}")
            return False, "", str(e)


class RegistryEditor:
    """Edita el registro de Windows con respaldo automático."""

    HIVE_MAP = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKU": winreg.HKEY_USERS,
    }

    @classmethod
    def set_value(
        cls,
        hive: str,
        path: str,
        name: str,
        value: Union[int, str],
        reg_type: int = winreg.REG_DWORD,
    ) -> tuple[bool, Optional[Union[int, str]]]:
        """
        Establece un valor en el registro.
        Retorna: (éxito, valor_anterior)
        """
        hive_key = cls.HIVE_MAP.get(hive.upper())
        if not hive_key:
            return False, None

        old_value = None
        try:
            # Crear la clave si no existe
            key = winreg.CreateKeyEx(
                hive_key, path, 0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            )
            # Leer valor anterior para respaldo
            try:
                old_value, _ = winreg.QueryValueEx(key, name)
            except FileNotFoundError:
                old_value = None

            winreg.SetValueEx(key, name, 0, reg_type, value)
            winreg.CloseKey(key)
            logger.debug(f"Registro: {hive}\\{path}\\{name} = {value} (era: {old_value})")
            return True, old_value
        except PermissionError:
            logger.error(f"Sin permisos para modificar: {hive}\\{path}\\{name}")
            return False, None
        except Exception as e:
            logger.error(f"Error en registro {hive}\\{path}\\{name}: {e}")
            return False, None

    @classmethod
    def get_value(
        cls, hive: str, path: str, name: str
    ) -> Optional[Union[int, str]]:
        """Lee un valor del registro. Retorna None si no existe."""
        hive_key = cls.HIVE_MAP.get(hive.upper())
        if not hive_key:
            return None
        try:
            with winreg.OpenKey(hive_key, path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except Exception:
            return None

    @classmethod
    def delete_value(cls, hive: str, path: str, name: str) -> bool:
        """Elimina un valor del registro."""
        hive_key = cls.HIVE_MAP.get(hive.upper())
        if not hive_key:
            return False
        try:
            with winreg.OpenKey(hive_key, path, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, name)
            return True
        except Exception:
            return False

    @classmethod
    def create_key(cls, hive: str, path: str) -> bool:
        """Crea una clave en el registro si no existe."""
        hive_key = cls.HIVE_MAP.get(hive.upper())
        if not hive_key:
            return False
        try:
            winreg.CreateKeyEx(hive_key, path, 0, winreg.KEY_WRITE)
            return True
        except Exception as e:
            logger.error(f"Error creando clave {hive}\\{path}: {e}")
            return False


class ServiceManager:
    """Gestiona servicios de Windows."""

    @staticmethod
    def get_startup_type(service_name: str) -> Optional[str]:
        """Obtiene el tipo de inicio actual de un servicio."""
        ps = PowerShellRunner()
        ok, out, _ = ps.run(
            f"(Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue).StartType"
        )
        if ok and out.strip():
            return out.strip()
        return None

    @staticmethod
    def set_startup_type(service_name: str, startup_type: str) -> bool:
        """Establece el tipo de inicio de un servicio (Disabled, Manual, Automatic)."""
        ps = PowerShellRunner()
        ok, _, err = ps.run(
            f"Set-Service -Name '{service_name}' -StartupType {startup_type} -ErrorAction Stop"
        )
        if not ok:
            logger.warning(f"No se pudo configurar {service_name}: {err[:200]}")
        return ok

    @staticmethod
    def stop_service(service_name: str) -> bool:
        """Detiene un servicio."""
        ps = PowerShellRunner()
        ok, _, _ = ps.run(
            f"Stop-Service -Name '{service_name}' -Force -ErrorAction SilentlyContinue"
        )
        return ok

    @staticmethod
    def service_exists(service_name: str) -> bool:
        """Verifica si un servicio existe en el sistema."""
        ps = PowerShellRunner()
        ok, out, _ = ps.run(
            f"Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue | "
            f"Select-Object -ExpandProperty Name"
        )
        return ok and service_name.lower() in out.lower()
