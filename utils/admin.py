"""
Módulo de verificación de privilegios de administrador.
"""
import ctypes
import sys
import subprocess


def is_admin() -> bool:
    """Verifica si el proceso actual tiene privilegios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def request_admin() -> None:
    """Relanza el proceso con privilegios de administrador si no los tiene."""
    if not is_admin():
        # Relanzar con elevación UAC
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


def run_as_admin_check() -> bool:
    """
    Verifica si el script puede ejecutar comandos con privilegios elevados.
    Retorna True si tiene permisos, False si no.
    """
    try:
        result = subprocess.run(
            ["net", "session"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
