"""
Módulo de compatibilidad: verifica versión de Windows y capacidades del sistema.
"""
import platform
import subprocess
import winreg
from typing import Optional


def get_windows_version() -> dict:
    """Retorna información detallada de la versión de Windows."""
    version_info = platform.version()
    release = platform.release()

    # Leer versión del registro para máxima precisión
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        ) as key:
            current_build = winreg.QueryValueEx(key, "CurrentBuild")[0]
            display_version = _safe_query(key, "DisplayVersion", "")
            product_name = _safe_query(key, "ProductName", release)
    except Exception:
        current_build = "0"
        display_version = ""
        product_name = f"Windows {release}"

    build_number = int(current_build) if current_build.isdigit() else 0

    return {
        "release": release,
        "version": version_info,
        "build": build_number,
        "display_version": display_version,
        "product_name": product_name,
        "is_win10": build_number < 22000,
        "is_win11": build_number >= 22000,
        "is_supported": build_number >= 17763,  # Windows 10 1809 mínimo
    }


def _safe_query(key, name: str, default: str) -> str:
    try:
        return winreg.QueryValueEx(key, name)[0]
    except Exception:
        return default


def check_nvme_support() -> bool:
    """Verifica si hay unidades NVMe instaladas."""
    try:
        result = subprocess.run(
            ["wmic", "diskdrive", "get", "InterfaceType"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "NVMe" in result.stdout or "NVME" in result.stdout.upper()
    except Exception:
        return False


def get_ram_gb() -> float:
    """Retorna la RAM total instalada en GB."""
    try:
        result = subprocess.run(
            ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip().isdigit()]
        if lines:
            return round(int(lines[0]) / (1024 ** 3), 1)
    except Exception:
        pass
    return 0.0


def check_ssd_present() -> bool:
    """Verifica si el sistema tiene al menos un SSD."""
    try:
        result = subprocess.run(
            ["wmic", "diskdrive", "get", "MediaType"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "Solid" in result.stdout or "SSD" in result.stdout.upper()
    except Exception:
        return False


def get_system_summary() -> dict:
    """Retorna un resumen completo de compatibilidad del sistema."""
    win_info = get_windows_version()
    ram = get_ram_gb()
    has_ssd = check_ssd_present()
    has_nvme = check_nvme_support()

    return {
        **win_info,
        "ram_gb": ram,
        "has_ssd": has_ssd,
        "has_nvme": has_nvme,
        "recommended_pagefile_min_mb": int(ram * 1024),
        "recommended_pagefile_max_mb": int(ram * 1024 * 2),
    }
