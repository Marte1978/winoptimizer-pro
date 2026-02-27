"""
Módulo de optimización del plan de energía.
Configura Windows para máximo rendimiento o equilibrio según el tipo de equipo.
"""
import logging
import subprocess
from typing import Callable, Optional
from .core import PowerShellRunner

logger = logging.getLogger("WinOptimizer")

# GUIDs de planes de energía conocidos
POWER_PLANS = {
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "ultimate_performance": "e9a42b02-d5df-448d-aa00-03f14749eb61",
}


class PowerOptimizer:
    """Optimiza el plan y la configuración de energía de Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.ps = PowerShellRunner()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def get_active_plan(self) -> Optional[str]:
        """Obtiene el GUID del plan de energía activo."""
        try:
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def get_plan_name(self, guid: str) -> str:
        """Retorna el nombre legible de un plan dado su GUID."""
        for name, plan_guid in POWER_PLANS.items():
            if plan_guid.lower() in guid.lower():
                return name.replace("_", " ").title()
        return guid

    def ultimate_performance_exists(self) -> bool:
        """Verifica si el plan Ultimate Performance ya está disponible."""
        try:
            result = subprocess.run(
                ["powercfg", "/list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return POWER_PLANS["ultimate_performance"].lower() in result.stdout.lower()
        except Exception:
            return False

    def enable_ultimate_performance(self) -> bool:
        """Activa el plan de energía Ultimate Performance (oculto por defecto)."""
        self.progress_cb("Verificando plan Ultimate Performance...", 20)

        if not self.ultimate_performance_exists():
            self.progress_cb("Creando plan Ultimate Performance...", 40)
            try:
                result = subprocess.run(
                    [
                        "powercfg",
                        "-duplicatescheme",
                        POWER_PLANS["ultimate_performance"],
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    logger.error(f"Error creando Ultimate Performance: {result.stderr}")
                    return False
            except Exception as e:
                logger.error(f"Exception creando Ultimate Performance: {e}")
                return False

        self.progress_cb("Activando plan Ultimate Performance...", 70)

        try:
            # Primero encontrar el GUID que fue generado
            list_result = subprocess.run(
                ["powercfg", "/list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Buscar la línea con Ultimate Performance
            guid = None
            for line in list_result.stdout.splitlines():
                if "ultimate" in line.lower() or POWER_PLANS["ultimate_performance"].lower() in line.lower():
                    # Extraer GUID de la línea
                    import re
                    match = re.search(
                        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                        line,
                        re.IGNORECASE,
                    )
                    if match:
                        guid = match.group(1)
                        break

            if not guid:
                guid = POWER_PLANS["ultimate_performance"]

            result = subprocess.run(
                ["powercfg", "/setactive", guid],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.progress_cb("✅ Plan Ultimate Performance activado.", 100)
                logger.info("Plan de energía Ultimate Performance activado.")
                if self.tracker:
                    self.tracker.record(
                        category="power",
                        action="ultimate_performance",
                        description="Plan Ultimate Performance activado",
                        revert_command=f"powercfg /setactive {POWER_PLANS['balanced']}",
                    )
                return True
            else:
                logger.error(f"Error activando plan: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Exception activando Ultimate Performance: {e}")
            return False

    def set_processor_state(self, min_pct: int = 100, max_pct: int = 100) -> bool:
        """
        Configura el estado mínimo y máximo del procesador.
        100% deshabilita el escalado dinámico de frecuencia (turbo constante).
        """
        self.progress_cb("Configurando estados del procesador...", 30)

        try:
            # Obtener el plan activo
            active_result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if active_result.returncode != 0:
                return False

            import re
            match = re.search(
                r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                active_result.stdout,
                re.IGNORECASE,
            )
            if not match:
                return False

            plan_guid = match.group(1)

            cmds = [
                # Procesador mínimo AC
                ["powercfg", "/setacvalueindex", plan_guid, "54533251-82be-4824-96c1-47b60b740d00",
                 "893dee8e-2bef-41e0-89c6-b55d0929964c", str(min_pct)],
                # Procesador máximo AC
                ["powercfg", "/setacvalueindex", plan_guid, "54533251-82be-4824-96c1-47b60b740d00",
                 "bc5038f7-23e0-4960-96da-33abaf5935ec", str(max_pct)],
                # Disco duro apagar después de: Nunca
                ["powercfg", "/setacvalueindex", plan_guid, "0012ee47-9041-4b5d-9b77-535fba8b1442",
                 "6738e2c4-e8a5-4a42-b16a-e040e769756e", "0"],
                # Suspensión selectiva USB: deshabilitada
                ["powercfg", "/setacvalueindex", plan_guid, "2a737441-1930-4402-8d77-b2bebba308a3",
                 "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "0"],
            ]

            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, timeout=10)

            # Aplicar el plan
            subprocess.run(
                ["powercfg", "/setactive", plan_guid],
                capture_output=True,
                timeout=10,
            )

            self.progress_cb("✅ Procesador configurado al 100% constante.", 100)
            logger.info(f"Estado del procesador: mín={min_pct}%, máx={max_pct}%")

            if self.tracker:
                self.tracker.record(
                    category="power",
                    action="processor_state",
                    description=f"Procesador: mín={min_pct}%, máx={max_pct}%",
                    revert_command=None,
                )
            return True

        except Exception as e:
            logger.error(f"Error configurando procesador: {e}")
            return False

    def disable_hibernation(self) -> bool:
        """Deshabilita la hibernación (libera espacio = tamaño de RAM en disco)."""
        self.progress_cb("Deshabilitando hibernación...", 50)
        try:
            result = subprocess.run(
                ["powercfg", "/h", "off"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            ok = result.returncode == 0
            if ok:
                logger.info("Hibernación deshabilitada.")
                if self.tracker:
                    self.tracker.record(
                        category="power",
                        action="disable_hibernation",
                        description="Hibernación deshabilitada (libera RAM en disco)",
                        revert_command="powercfg /h on",
                    )
            return ok
        except Exception:
            return False

    def optimize_all(self, is_laptop: bool = False) -> tuple[int, int]:
        """Aplica todas las optimizaciones de energía."""
        ok_count = 0
        fail_count = 0

        # Ultimate Performance (no recomendado para laptops con batería)
        if not is_laptop:
            if self.enable_ultimate_performance():
                ok_count += 1
            else:
                fail_count += 1

            if self.set_processor_state(100, 100):
                ok_count += 1
            else:
                fail_count += 1

            if self.disable_hibernation():
                ok_count += 1
            else:
                fail_count += 1
        else:
            # Para laptops: Plan High Performance (no Ultimate)
            try:
                result = subprocess.run(
                    ["powercfg", "/setactive", POWER_PLANS["high_performance"]],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1

        return ok_count, fail_count
