"""
Módulo de privacidad para WinOptimizer Pro.
Deshabilita telemetría, rastreo y funciones de vigilancia de Microsoft.
"""
import logging
import winreg
from typing import Callable, Optional

from .core import PowerShellRunner, RegistryEditor

logger = logging.getLogger("WinOptimizer")

PRIVACY_TWEAKS: list[dict] = [
    {
        "key": "prv_telemetry",
        "display": "🔇  Deshabilitar Telemetría de Windows",
        "description": "Impide que Windows envíe datos de uso a Microsoft. Reduce tráfico de red y carga del sistema.",
        "risk": "low",
        "method": "disable_telemetry",
        "default": True,
    },
    {
        "key": "prv_advertising_id",
        "display": "🚫  Deshabilitar ID de Publicidad",
        "description": "Desactiva el identificador único que usan las apps para rastrear y mostrar anuncios personalizados.",
        "risk": "low",
        "method": "disable_advertising_id",
        "default": True,
    },
    {
        "key": "prv_activity_history",
        "display": "📋  Deshabilitar Historial de Actividad",
        "description": "Impide que Windows registre las apps y sitios usados para la línea de tiempo.",
        "risk": "low",
        "method": "disable_activity_history",
        "default": True,
    },
    {
        "key": "prv_cortana",
        "display": "🎤  Deshabilitar Cortana y Búsqueda Bing",
        "description": "Desactiva el asistente Cortana y elimina resultados web de Bing en la búsqueda local.",
        "risk": "low",
        "method": "disable_cortana",
        "default": True,
    },
    {
        "key": "prv_copilot",
        "display": "🤖  Deshabilitar Windows Copilot",
        "description": "Desactiva el panel lateral de Copilot en Windows 11. No afecta a Windows 10.",
        "risk": "low",
        "method": "disable_copilot",
        "default": True,
    },
    {
        "key": "prv_recall",
        "display": "📸  Deshabilitar Windows Recall",
        "description": "Desactiva la función de capturas de pantalla continuas de IA (Windows 11 24H2+).",
        "risk": "low",
        "method": "disable_recall",
        "default": True,
    },
    {
        "key": "prv_tailored_experiences",
        "display": "🎯  Deshabilitar Experiencias Personalizadas",
        "description": "Impide que Microsoft use datos de diagnóstico para mostrar sugerencias y publicidad.",
        "risk": "low",
        "method": "disable_tailored_experiences",
        "default": True,
    },
    {
        "key": "prv_location",
        "display": "📍  Deshabilitar Servicios de Ubicación",
        "description": "Bloquea el acceso de las apps al GPS y ubicación del sistema.",
        "risk": "low",
        "method": "disable_location",
        "default": False,
    },
    {
        "key": "prv_feedback",
        "display": "💬  Deshabilitar Solicitudes de Comentarios",
        "description": "Elimina las ventanas emergentes que piden valorar Windows. Reduce interrupciones.",
        "risk": "low",
        "method": "disable_feedback_requests",
        "default": True,
    },
]


class PrivacyOptimizer:
    """Gestiona tweaks de privacidad y anti-rastreo de Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.ps = PowerShellRunner()
        self.editor = RegistryEditor()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def disable_telemetry(self) -> bool:
        """Deshabilita telemetría de Windows y detiene el servicio DiagTrack."""
        self.progress_cb("Deshabilitando telemetría...", 10)
        ok1, _ = self.editor.set_value(
            "HKLM",
            r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            "AllowTelemetry",
            0,
            winreg.REG_DWORD,
        )
        ok2, _, _ = self.ps.run("Set-Service DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue")
        success = ok1 or ok2
        if success:
            logger.info("Telemetría de Windows deshabilitada.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_telemetry",
                    description="Telemetría deshabilitada (AllowTelemetry=0, DiagTrack disabled)",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' "
                        "-Name AllowTelemetry -Value 3; Set-Service DiagTrack -StartupType Automatic"
                    ),
                )
        return success

    def disable_advertising_id(self) -> bool:
        """Desactiva el ID de publicidad por usuario."""
        self.progress_cb("Deshabilitando ID de publicidad...", 20)
        ok, _ = self.editor.set_value(
            "HKCU",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            "Enabled",
            0,
            winreg.REG_DWORD,
        )
        if ok:
            logger.info("ID de publicidad deshabilitado.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_advertising_id",
                    description="ID de publicidad deshabilitado",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo' "
                        "-Name Enabled -Value 1"
                    ),
                )
        return ok

    def disable_activity_history(self) -> bool:
        """Deshabilita el historial de actividad y la línea de tiempo."""
        self.progress_cb("Deshabilitando historial de actividad...", 30)
        path = r"SOFTWARE\Policies\Microsoft\Windows\System"
        ok1, _ = self.editor.set_value("HKLM", path, "EnableActivityFeed", 0, winreg.REG_DWORD)
        ok2, _ = self.editor.set_value("HKLM", path, "PublishUserActivities", 0, winreg.REG_DWORD)
        success = ok1 or ok2
        if success:
            logger.info("Historial de actividad deshabilitado.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_activity_history",
                    description="Historial de actividad deshabilitado",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' "
                        "-Name EnableActivityFeed -Value 1; "
                        "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' "
                        "-Name PublishUserActivities -Value 1"
                    ),
                )
        return success

    def disable_cortana(self) -> bool:
        """Deshabilita Cortana y búsqueda Bing integrada."""
        self.progress_cb("Deshabilitando Cortana...", 40)
        ok1, _ = self.editor.set_value(
            "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "AllowCortana", 0, winreg.REG_DWORD
        )
        path_search = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search"
        ok2, _ = self.editor.set_value("HKCU", path_search, "BingSearchEnabled", 0, winreg.REG_DWORD)
        ok3, _ = self.editor.set_value("HKCU", path_search, "CortanaConsent", 0, winreg.REG_DWORD)
        success = ok1 or ok2 or ok3
        if success:
            logger.info("Cortana y búsqueda Bing deshabilitados.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_cortana",
                    description="Cortana y Bing deshabilitados",
                    revert_command=(
                        "Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' "
                        "-Name AllowCortana -ErrorAction SilentlyContinue"
                    ),
                )
        return success

    def disable_copilot(self) -> bool:
        """Deshabilita Windows Copilot (Windows 11)."""
        self.progress_cb("Deshabilitando Windows Copilot...", 50)
        ok1, _ = self.editor.set_value(
            "HKCU", r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1, winreg.REG_DWORD
        )
        ok2, _ = self.editor.set_value(
            "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1, winreg.REG_DWORD
        )
        success = ok1 or ok2
        if success:
            logger.info("Windows Copilot deshabilitado.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_copilot",
                    description="Windows Copilot deshabilitado (HKCU + HKLM)",
                    revert_command=(
                        "Remove-ItemProperty -Path 'HKCU:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' "
                        "-Name TurnOffWindowsCopilot -ErrorAction SilentlyContinue; "
                        "Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' "
                        "-Name TurnOffWindowsCopilot -ErrorAction SilentlyContinue"
                    ),
                )
        return success

    def disable_recall(self) -> bool:
        """Deshabilita Windows Recall (Windows 11 24H2+)."""
        self.progress_cb("Deshabilitando Windows Recall...", 60)
        ok1, _ = self.editor.set_value(
            "HKLM", r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", 1, winreg.REG_DWORD
        )
        ok2, _, _ = self.ps.run(
            'Disable-WindowsOptionalFeature -Online -FeatureName "Recall" -NoRestart -ErrorAction SilentlyContinue'
        )
        success = ok1 or ok2
        if success:
            logger.info("Windows Recall deshabilitado.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_recall",
                    description="Windows Recall deshabilitado (registro + feature)",
                    revert_command=(
                        "Remove-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' "
                        "-Name DisableAIDataAnalysis -ErrorAction SilentlyContinue"
                    ),
                )
        return success

    def disable_tailored_experiences(self) -> bool:
        """Deshabilita experiencias personalizadas basadas en datos de diagnóstico."""
        self.progress_cb("Deshabilitando experiencias personalizadas...", 70)
        ok, _ = self.editor.set_value(
            "HKCU",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
            "TailoredExperiencesWithDiagnosticDataEnabled",
            0,
            winreg.REG_DWORD,
        )
        if ok:
            logger.info("Experiencias personalizadas deshabilitadas.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_tailored_experiences",
                    description="Experiencias personalizadas con datos de diagnóstico deshabilitadas",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Privacy' "
                        "-Name TailoredExperiencesWithDiagnosticDataEnabled -Value 1"
                    ),
                )
        return ok

    def disable_location(self) -> bool:
        """Bloquea acceso de apps a la ubicación del sistema."""
        self.progress_cb("Deshabilitando servicios de ubicación...", 80)
        path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
        ok, _ = self.editor.set_value("HKLM", path, "Value", "Deny", winreg.REG_SZ)
        if ok:
            logger.info("Servicios de ubicación deshabilitados.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_location",
                    description="Acceso a ubicación bloqueado (Deny)",
                    revert_command=(
                        "Set-ItemProperty -Path "
                        "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location' "
                        "-Name Value -Value Allow"
                    ),
                )
        return ok

    def disable_feedback_requests(self) -> bool:
        """Elimina las ventanas emergentes de solicitudes de comentarios de Windows."""
        self.progress_cb("Deshabilitando solicitudes de comentarios...", 90)
        ok1, _ = self.editor.set_value(
            "HKCU", r"SOFTWARE\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0, winreg.REG_DWORD
        )
        ok2, _ = self.editor.set_value(
            "HKLM",
            r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            "DoNotShowFeedbackNotifications",
            1,
            winreg.REG_DWORD,
        )
        success = ok1 or ok2
        if success:
            logger.info("Solicitudes de comentarios deshabilitadas.")
            if self.tracker:
                self.tracker.record(
                    category="privacy",
                    action="disable_feedback_requests",
                    description="Solicitudes de comentarios de Windows deshabilitadas",
                    revert_command=(
                        "Remove-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Siuf\\Rules' "
                        "-Name NumberOfSIUFInPeriod -ErrorAction SilentlyContinue"
                    ),
                )
        return success

    def optimize_all(self, selected: list[str] = None) -> tuple[int, int]:
        """
        Aplica todos los tweaks de privacidad o solo los seleccionados.
        Retorna (exitosos, fallidos).
        """
        tweaks = PRIVACY_TWEAKS
        if selected is not None:
            tweaks = [t for t in PRIVACY_TWEAKS if t["key"] in selected]

        total = len(tweaks)
        ok_count = 0
        fail_count = 0

        for i, tweak in enumerate(tweaks):
            pct = int((i / total) * 100) if total > 0 else 0
            self.progress_cb(f"Aplicando: {tweak['display']}...", pct)
            method = getattr(self, tweak["method"], None)
            if method is None:
                logger.warning(f"Método no encontrado: {tweak['method']}")
                fail_count += 1
                continue
            try:
                result = method()
                if result:
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception as exc:
                logger.error(f"Error aplicando {tweak['key']}: {exc}")
                fail_count += 1

        self.progress_cb("Privacidad optimizada.", 100)
        logger.info(f"Privacy optimize_all: {ok_count} OK / {fail_count} fallidos.")
        return ok_count, fail_count
