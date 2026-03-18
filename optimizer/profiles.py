import logging
import winreg
from typing import Callable, Optional
from .core import PowerShellRunner, RegistryEditor

logger = logging.getLogger("WinOptimizer")

PROFILES = {
    "gaming": {
        "name": "🎮  Gaming",
        "description": "Máximo rendimiento: CPU al 100%, prioridad a juegos, sin throttling de red",
        "color": "#ef4444",
        "icon": "🎮",
    },
    "work": {
        "name": "💼  Trabajo",
        "description": "Equilibrado: rendimiento normal, bajo consumo de energía",
        "color": "#3b82f6",
        "icon": "💼",
    },
    "laptop": {
        "name": "🔋  Batería",
        "description": "Máximo ahorro: CPU limitado al 80%, Bluetooth off, pantalla eficiente",
        "color": "#10b981",
        "icon": "🔋",
    },
}

_MULTIMEDIA_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
_GAMES_PATH = _MULTIMEDIA_PATH + r"\Tasks\Games"
_PRIORITY_PATH = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
_GAMEDVR_USER = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
_GAMEDVR_POLICY = r"SOFTWARE\Policies\Microsoft\Windows\GameDVR"


class ProfilesManager:
    def __init__(
        self,
        change_tracker: Optional[object] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.change_tracker = change_tracker
        self.progress_callback = progress_callback

    def _log(self, msg: str) -> None:
        logger.info(msg)
        if self.progress_callback:
            self.progress_callback(msg)

    def _reg(self, hive, path: str, name: str, value: int, reg_type=winreg.REG_DWORD) -> bool:
        ok, _ = RegistryEditor.set_value(hive, path, name, value, reg_type)
        return ok

    # ------------------------------------------------------------------
    def apply_gaming_profile(self) -> tuple[int, int]:
        ok = fail = 0

        # 1. Power plan Ultimate Performance
        self._log("Aplicando plan de energía: Ultimate Performance...")
        success, _, _ = PowerShellRunner.run(
            "powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        )
        if not success:
            success, _, _ = PowerShellRunner.run(
                "powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
            )
        (ok if success else fail) and None
        if success:
            ok += 1
        else:
            fail += 1

        # 2. CPU priority para juegos
        self._log("Configurando SystemResponsiveness = 0...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _MULTIMEDIA_PATH, "SystemResponsiveness", 0):
            ok += 1
        else:
            fail += 1

        # 3. GPU priority en Tasks\Games
        self._log("Configurando prioridad GPU para juegos...")
        games_tweaks = [("GPU Priority", 8), ("Priority", 6), ("SFIO Rate", 4)]
        for name, val in games_tweaks:
            if self._reg(winreg.HKEY_LOCAL_MACHINE, _GAMES_PATH, name, val):
                ok += 1
            else:
                fail += 1

        # 4. Deshabilitar Xbox Game DVR
        self._log("Deshabilitando Xbox Game DVR...")
        if self._reg(winreg.HKEY_CURRENT_USER, _GAMEDVR_USER, "AppCaptureEnabled", 0):
            ok += 1
        else:
            fail += 1
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _GAMEDVR_POLICY, "AllowGameDVR", 0):
            ok += 1
        else:
            fail += 1

        # 5. Network Throttling OFF
        self._log("Desactivando throttling de red...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _MULTIMEDIA_PATH, "NetworkThrottlingIndex", 0xFFFFFFFF):
            ok += 1
        else:
            fail += 1

        # 6. Foreground priority
        self._log("Ajustando prioridad de foreground (Win32PrioritySeparation = 38)...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _PRIORITY_PATH, "Win32PrioritySeparation", 38):
            ok += 1
        else:
            fail += 1

        self._log(f"Perfil Gaming aplicado: {ok} OK, {fail} errores.")
        return ok, fail

    # ------------------------------------------------------------------
    def apply_work_profile(self) -> tuple[int, int]:
        ok = fail = 0

        # 1. Power plan Balanced
        self._log("Aplicando plan de energía: Balanced...")
        success, _, _ = PowerShellRunner.run(
            "powercfg -setactive 381b4222-f694-41f0-9685-ff5bb260df2e"
        )
        if success:
            ok += 1
        else:
            fail += 1

        # 2. SystemResponsiveness default
        self._log("Restaurando SystemResponsiveness = 20...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _MULTIMEDIA_PATH, "SystemResponsiveness", 20):
            ok += 1
        else:
            fail += 1

        # 3. Win32PrioritySeparation default
        self._log("Restaurando Win32PrioritySeparation = 2...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _PRIORITY_PATH, "Win32PrioritySeparation", 2):
            ok += 1
        else:
            fail += 1

        # 4. Restaurar Game DVR a default (habilitar)
        self._log("Restaurando Game DVR a valores por defecto...")
        if self._reg(winreg.HKEY_CURRENT_USER, _GAMEDVR_USER, "AppCaptureEnabled", 1):
            ok += 1
        else:
            fail += 1

        # 5. NetworkThrottlingIndex default
        self._log("Restaurando NetworkThrottlingIndex = 10...")
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _MULTIMEDIA_PATH, "NetworkThrottlingIndex", 10):
            ok += 1
        else:
            fail += 1

        self._log(f"Perfil Trabajo aplicado: {ok} OK, {fail} errores.")
        return ok, fail

    # ------------------------------------------------------------------
    def apply_laptop_profile(self) -> tuple[int, int]:
        ok = fail = 0

        # 1. Power plan Power Saver
        self._log("Aplicando plan de energía: Power Saver...")
        success, _, _ = PowerShellRunner.run(
            "powercfg -setactive a1841308-3541-4fab-bc81-f71556f20b4a"
        )
        if success:
            ok += 1
        else:
            fail += 1

        # 2. Reducir brillo
        self._log("Intentando reducir brillo de pantalla...")
        success, _, _ = PowerShellRunner.run(
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, 40)"
        )
        if success:
            ok += 1
        else:
            fail += 1

        # 3. Deshabilitar Bluetooth
        self._log("Deshabilitando servicio Bluetooth...")
        success, _, _ = PowerShellRunner.run(
            "Set-Service bthserv -StartupType Disabled -ErrorAction SilentlyContinue"
        )
        if success:
            ok += 1
        else:
            fail += 1

        # 4. Reducir efectos visuales via registro
        self._log("Reduciendo efectos visuales...")
        _explorer_adv = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        if self._reg(winreg.HKEY_LOCAL_MACHINE, _explorer_adv, "ListviewAlphaSelect", 0):
            ok += 1
        else:
            fail += 1

        # 5. CPU throttle min 5%, max AC 80%, max DC 60%
        self._log("Configurando límites de CPU para ahorro de batería...")
        cpu_cmds = [
            "powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 5",
            "powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 80",
            "powercfg /setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 60",
            "powercfg /S SCHEME_CURRENT",
        ]
        for cmd in cpu_cmds:
            success, _, _ = PowerShellRunner.run(cmd)
            if success:
                ok += 1
            else:
                fail += 1

        self._log(f"Perfil Laptop/Batería aplicado: {ok} OK, {fail} errores.")
        return ok, fail

    # ------------------------------------------------------------------
    def get_current_power_plan(self) -> str:
        success, stdout, _ = PowerShellRunner.run("powercfg /getactivescheme")
        if not success or not stdout:
            return "Desconocido"
        # Output: "Power Scheme GUID: <guid>  (<nombre>)"
        line = stdout.strip().splitlines()[0] if stdout.strip() else ""
        if "(" in line and ")" in line:
            return line[line.rfind("(") + 1 : line.rfind(")")]
        return line or "Desconocido"

    def get_active_profile_name(self) -> str:
        plan = self.get_current_power_plan().lower()
        if "ultimate" in plan or "8c5e7fda" in plan:
            return "Gaming"
        if "balanced" in plan or "381b4222" in plan:
            return "Trabajo"
        if "power saver" in plan or "a1841308" in plan or "saver" in plan:
            return "Laptop"
        return "Personalizado"
