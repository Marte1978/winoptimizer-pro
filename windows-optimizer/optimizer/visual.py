"""
Módulo de optimización de efectos visuales.
Deshabilita efectos visuales innecesarios para liberar CPU y RAM.
"""
import logging
import winreg
from typing import Callable, Optional

from .core import RegistryEditor, PowerShellRunner

logger = logging.getLogger("WinOptimizer")


class VisualOptimizer:
    """Optimiza los efectos visuales de Windows para máximo rendimiento."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.editor = RegistryEditor()
        self.ps = PowerShellRunner()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def set_performance_mode(self) -> bool:
        """
        Configura Windows para priorizar rendimiento sobre apariencia visual.
        Equivale a Propiedades del sistema → Rendimiento → Ajustar para obtener el mejor rendimiento.
        """
        self.progress_cb("Configurando efectos visuales para máximo rendimiento...", 20)

        # VisualFXSetting: 0=Default, 1=Best appearance, 2=Best performance, 3=Custom
        ok1, _ = self.editor.set_value(
            "HKCU",
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
            "VisualFXSetting",
            2,
            winreg.REG_DWORD,
        )

        # Configuraciones específicas de rendimiento en UserPreferencesMask
        # El bitmask controla cada efecto visual individualmente
        # Valor 90 12 03 80 → máximo rendimiento
        ok2, _ = self.editor.set_value(
            "HKCU",
            r"Control Panel\Desktop",
            "UserPreferencesMask",
            bytes([0x90, 0x12, 0x03, 0x80, 0x10, 0x00, 0x00, 0x00]),
            winreg.REG_BINARY,
        )

        if ok1:
            logger.info("Efectos visuales configurados para máximo rendimiento.")
            if self.tracker:
                self.tracker.record(
                    category="visual",
                    action="visual_performance_mode",
                    description="Efectos visuales: modo rendimiento máximo",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects' "
                        "-Name 'VisualFXSetting' -Value 0"
                    ),
                )
        return ok1

    def disable_window_animations(self) -> bool:
        """Deshabilita animaciones de ventanas (minimizar/maximizar/abrir)."""
        self.progress_cb("Deshabilitando animaciones de ventanas...", 40)

        ok1, _ = self.editor.set_value(
            "HKCU",
            r"Control Panel\Desktop\WindowMetrics",
            "MinAnimate",
            "0",
            winreg.REG_SZ,
        )

        ok2, _ = self.editor.set_value(
            "HKCU",
            r"Control Panel\Desktop",
            "AnimationDuration",
            0,
            winreg.REG_DWORD,
        )

        # Deshabilitar también via SystemParametersInfo
        ok3, _, _ = self.ps.run(
            "Add-Type -TypeDefinition @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class WinAPI {\n"
            "    [DllImport(\"user32.dll\")] "
            "    public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);\n"
            "}\n"
            "'@; [WinAPI]::SystemParametersInfo(0x1003, 0, '0', 3) | Out-Null"
        )

        success = ok1 or ok2
        if success:
            logger.info("Animaciones de ventanas deshabilitadas.")
            if self.tracker:
                self.tracker.record(
                    category="visual",
                    action="disable_animations",
                    description="Animaciones de ventanas deshabilitadas",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop\\WindowMetrics' "
                        "-Name 'MinAnimate' -Value '1'"
                    ),
                )
        return success

    def disable_transparency(self) -> bool:
        """Deshabilita los efectos de transparencia (glassmorphism) de Windows."""
        self.progress_cb("Deshabilitando transparencia del sistema...", 60)

        ok, _ = self.editor.set_value(
            "HKCU",
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "EnableTransparency",
            0,
            winreg.REG_DWORD,
        )

        if ok:
            logger.info("Transparencia del sistema deshabilitada.")
            if self.tracker:
                self.tracker.record(
                    category="visual",
                    action="disable_transparency",
                    description="Efectos de transparencia deshabilitados",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
                        "-Name 'EnableTransparency' -Value 1"
                    ),
                )
        return ok

    def disable_aero_shake(self) -> bool:
        """Deshabilita Aero Shake (sacudir ventana para minimizar otras)."""
        self.progress_cb("Deshabilitando Aero Shake...", 80)

        ok, _ = self.editor.set_value(
            "HKCU",
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "DisallowShaking",
            1,
            winreg.REG_DWORD,
        )

        if ok:
            logger.info("Aero Shake deshabilitado.")
        return ok

    def disable_snap_animation(self) -> bool:
        """Deshabilita la animación de Snap de ventanas."""
        ok, _ = self.editor.set_value(
            "HKCU",
            r"Control Panel\Desktop",
            "WindowArrangementActive",
            "0",
            winreg.REG_SZ,
        )
        return ok

    def optimize_all(self, keep_transparency: bool = False) -> tuple[int, int]:
        """
        Aplica todas las optimizaciones visuales.
        keep_transparency: Si es True, no deshabilita la transparencia.
        """
        ok_count = 0
        fail_count = 0

        ops = [
            self.set_performance_mode,
            self.disable_window_animations,
            self.disable_aero_shake,
            self.disable_snap_animation,
        ]

        if not keep_transparency:
            ops.append(self.disable_transparency)

        for i, func in enumerate(ops):
            pct = int(((i + 1) / len(ops)) * 100)
            try:
                if func():
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"Error en optimización visual: {e}")
                fail_count += 1

        self.progress_cb(f"✅ Efectos visuales optimizados.", 100)
        return ok_count, fail_count
