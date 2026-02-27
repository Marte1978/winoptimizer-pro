"""
Módulo de tweaks del registro de Windows.
Aplica optimizaciones probadas de rendimiento, gaming y respuesta del sistema.
"""
import winreg
import logging
from typing import Callable, Optional

from .core import RegistryEditor, PowerShellRunner

logger = logging.getLogger("WinOptimizer")


# Definición completa de tweaks del registro
# Formato: dict con toda la información necesaria para aplicar y revertir
REGISTRY_TWEAKS: list[dict] = [
    # ─── RENDIMIENTO GENERAL ─────────────────────────────────────────────────
    {
        "id": "power_throttling",
        "name": "Deshabilitar Power Throttling",
        "description": "Impide que Windows reduzca la frecuencia del CPU en procesos de fondo. Mejora 5-10% en cargas intensivas.",
        "category": "performance",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
        "name_key": "PowerThrottlingOff",
        "value": 1,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 0,
    },
    {
        "id": "kill_service_timeout",
        "name": "Reducir tiempo de cierre del sistema",
        "description": "Reduce el tiempo de espera al apagar de 5000ms a 2000ms. El sistema se apaga ~3 segundos más rápido.",
        "category": "performance",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SYSTEM\CurrentControlSet\Control",
        "name_key": "WaitToKillServiceTimeout",
        "value": "2000",
        "reg_type": winreg.REG_SZ,
        "revert_value": "5000",
    },
    {
        "id": "startup_delay",
        "name": "Eliminar delay artificial de inicio",
        "description": "Elimina el delay de 10 segundos que Windows impone a programas de inicio. Arranque más rápido.",
        "category": "startup",
        "risk": "low",
        "hive": "HKCU",
        "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
        "name_key": "StartupDelayInMSec",
        "value": 0,
        "reg_type": winreg.REG_DWORD,
        "revert_value": None,  # No existía; eliminar al revertir
    },
    {
        "id": "menu_show_delay",
        "name": "Reducir delay del menú contextual",
        "description": "Reduce el tiempo de aparición del menú clic derecho de 400ms a 200ms.",
        "category": "ui",
        "risk": "low",
        "hive": "HKCU",
        "path": r"Control Panel\Desktop",
        "name_key": "MenuShowDelay",
        "value": "200",
        "reg_type": winreg.REG_SZ,
        "revert_value": "400",
    },
    # ─── GAMING / MULTIMEDIA ──────────────────────────────────────────────────
    {
        "id": "mmcss_responsiveness",
        "name": "Optimizar SystemResponsiveness (MMCSS)",
        "description": "Aumenta el tiempo de CPU asignado al juego/app activo. Mejora FPS y fluidez.",
        "category": "gaming",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
        "name_key": "SystemResponsiveness",
        "value": 10,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 20,
    },
    {
        "id": "games_gpu_priority",
        "name": "Prioridad GPU para juegos",
        "description": "Asigna máxima prioridad de GPU/CPU al juego activo en el perfil MMCSS de juegos.",
        "category": "gaming",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
        "name_key": "GPU Priority",
        "value": 8,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 2,
    },
    {
        "id": "games_cpu_priority",
        "name": "Prioridad CPU para juegos",
        "description": "Establece prioridad de CPU alta para procesos de juegos en el perfil MMCSS.",
        "category": "gaming",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
        "name_key": "Priority",
        "value": 6,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 2,
    },
    {
        "id": "gamedvr_disable",
        "name": "Deshabilitar GameDVR / Xbox Game Bar Capture",
        "description": "Elimina el overhead de grabación en segundo plano. Puede mejorar FPS en juegos (+2-5%).",
        "category": "gaming",
        "risk": "low",
        "hive": "HKCU",
        "path": r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
        "name_key": "AppCaptureEnabled",
        "value": 0,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 1,
    },
    {
        "id": "gamedvr_policy",
        "name": "Política de GameDVR deshabilitada",
        "description": "Deshabilita GameDVR a nivel de políticas del sistema para efecto completo.",
        "category": "gaming",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
        "name_key": "AllowGameDVR",
        "value": 0,
        "reg_type": winreg.REG_DWORD,
        "revert_value": None,
    },
    {
        "id": "hags_enable",
        "name": "Habilitar Hardware-Accelerated GPU Scheduling (HAGS)",
        "description": "Mejora la consistencia de frametimes y reduce 1% lows. Requiere GPU compatible (GTX 1000+ / RX 5000+).",
        "category": "gaming",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
        "name_key": "HwSchMode",
        "value": 2,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 1,
    },
    # ─── RED / LATENCIA ───────────────────────────────────────────────────────
    {
        "id": "network_throttling",
        "name": "Deshabilitar Network Throttling",
        "description": "Elimina la limitación de ancho de banda para aplicaciones multimedia y gaming.",
        "category": "network",
        "risk": "low",
        "hive": "HKLM",
        "path": r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
        "name_key": "NetworkThrottlingIndex",
        "value": 0xFFFFFFFF,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 10,
    },
    # ─── VISUAL / UI ──────────────────────────────────────────────────────────
    {
        "id": "visual_effects_performance",
        "name": "Optimizar efectos visuales para rendimiento",
        "description": "Configura Windows para priorizar rendimiento sobre efectos visuales. Ahorra 1-3% CPU.",
        "category": "visual",
        "risk": "low",
        "hive": "HKCU",
        "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
        "name_key": "VisualFXSetting",
        "value": 2,
        "reg_type": winreg.REG_DWORD,
        "revert_value": 0,
    },
    {
        "id": "disable_animations",
        "name": "Deshabilitar animaciones de ventanas",
        "description": "Elimina las animaciones de minimizar/maximizar ventanas. Interfaz más responsiva.",
        "category": "visual",
        "risk": "low",
        "hive": "HKCU",
        "path": r"Control Panel\Desktop\WindowMetrics",
        "name_key": "MinAnimate",
        "value": "0",
        "reg_type": winreg.REG_SZ,
        "revert_value": "1",
    },
]


class RegistryOptimizer:
    """Aplica tweaks del registro para optimizar Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.editor = RegistryEditor()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def get_tweaks(self, category: Optional[str] = None) -> list[dict]:
        """Retorna tweaks filtrados por categoría."""
        if category:
            return [t for t in REGISTRY_TWEAKS if t["category"] == category]
        return REGISTRY_TWEAKS.copy()

    def apply_tweak(self, tweak: dict) -> bool:
        """Aplica un tweak del registro y registra el cambio."""
        hive = tweak["hive"]
        path = tweak["path"]
        name = tweak["name_key"]
        value = tweak["value"]
        reg_type = tweak["reg_type"]

        # Asegurar que la clave padre existe
        self.editor.create_key(hive, path)

        # Aplicar el cambio
        ok, old_value = self.editor.set_value(hive, path, name, value, reg_type)

        if ok:
            logger.info(f"Registry tweak aplicado: {tweak['name']}")
            if self.tracker:
                # Construir comando de reversión
                if tweak.get("revert_value") is not None:
                    rev_val = tweak["revert_value"]
                    rev_cmd = f"Set-ItemProperty -Path 'Registry::{hive}\\{path}' -Name '{name}' -Value {rev_val}"
                else:
                    rev_cmd = f"Remove-ItemProperty -Path 'Registry::{hive}\\{path}' -Name '{name}' -ErrorAction SilentlyContinue"

                self.tracker.record(
                    category="registry",
                    action=f"tweak_{tweak['id']}",
                    description=f"Registry: {tweak['name']}",
                    revert_command=rev_cmd,
                )
        else:
            logger.warning(f"No se pudo aplicar tweak: {tweak['name']}")

        return ok

    def revert_tweak(self, tweak: dict) -> bool:
        """Revierte un tweak al valor original."""
        hive = tweak["hive"]
        path = tweak["path"]
        name = tweak["name_key"]
        revert_value = tweak.get("revert_value")

        if revert_value is None:
            # El valor no existía antes, eliminarlo
            ok = self.editor.delete_value(hive, path, name)
            if ok:
                logger.info(f"Registry tweak revertido (eliminado): {tweak['name']}")
            return ok
        else:
            reg_type = tweak["reg_type"]
            ok, _ = self.editor.set_value(hive, path, name, revert_value, reg_type)
            if ok:
                logger.info(f"Registry tweak revertido: {tweak['name']} → {revert_value}")
            return ok

    def apply_all(
        self, selected_ids: Optional[list[str]] = None
    ) -> tuple[int, int]:
        """
        Aplica todos los tweaks seleccionados.
        Retorna (exitosos, fallidos).
        """
        tweaks = REGISTRY_TWEAKS
        if selected_ids is not None:
            tweaks = [t for t in tweaks if t["id"] in selected_ids]

        total = len(tweaks)
        ok_count = 0
        fail_count = 0

        for i, tweak in enumerate(tweaks):
            pct = int(((i + 1) / total) * 100) if total > 0 else 100
            self.progress_cb(f"Aplicando: {tweak['name']}...", pct)

            if self.apply_tweak(tweak):
                ok_count += 1
            else:
                fail_count += 1

        return ok_count, fail_count

    def revert_all(self, selected_ids: Optional[list[str]] = None) -> tuple[int, int]:
        """Revierte todos los tweaks seleccionados."""
        tweaks = REGISTRY_TWEAKS
        if selected_ids is not None:
            tweaks = [t for t in tweaks if t["id"] in selected_ids]

        ok_count = 0
        fail_count = 0

        for tweak in tweaks:
            if self.revert_tweak(tweak):
                ok_count += 1
            else:
                fail_count += 1

        return ok_count, fail_count

    def get_registry_keys_for_backup(self) -> list[dict]:
        """Retorna las claves de registro que serán modificadas, para respaldar."""
        return [
            {"hive": t["hive"], "path": t["path"], "name": t["name_key"]}
            for t in REGISTRY_TWEAKS
        ]
