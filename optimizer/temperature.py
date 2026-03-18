import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .core import PowerShellRunner

logger = logging.getLogger("WinOptimizer")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ThermalSnapshot:
    cpu_temp: Optional[float]
    gpu_temp: Optional[float]
    cpu_usage: float
    is_throttling: bool
    throttle_reason: str
    performance_state: str  # "Normal", "Throttled", "Critical"


class TemperatureMonitor:

    def __init__(self, interval: float = 3.0, on_update: Callable = None):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.on_update = on_update
        self.is_available = True

    # ------------------------------------------------------------------
    # Temperature readers
    # ------------------------------------------------------------------

    def get_cpu_temp(self) -> Optional[float]:
        cmd = (
            "$t = Get-WmiObject MSAcpi_ThermalZoneTemperature "
            "-Namespace root/wmi -ErrorAction SilentlyContinue "
            "| Select-Object -First 1; "
            "if ($t) { [math]::Round(($t.CurrentTemperature - 2732) / 10.0, 1) } "
            "else { Write-Output 'N/A' }"
        )
        ok, out, _ = PowerShellRunner.run(cmd, timeout=15)
        if not ok:
            return None
        val = out.strip()
        if val == "N/A" or not val:
            return None
        try:
            return float(val)
        except ValueError:
            return None

    def get_gpu_temp(self) -> Optional[float]:
        cmd = (
            "$gpu = Get-WmiObject -Namespace root/OpenHardwareMonitor "
            "-Class Sensor -ErrorAction SilentlyContinue "
            "| Where-Object {$_.SensorType -eq 'Temperature' -and $_.Name -like '*GPU*'} "
            "| Select-Object -First 1; "
            "if ($gpu) { $gpu.Value } else { Write-Output 'N/A' }"
        )
        ok, out, _ = PowerShellRunner.run(cmd, timeout=15)
        if not ok:
            return None
        val = out.strip()
        if val == "N/A" or not val:
            return None
        try:
            return float(val)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Throttling detection
    # ------------------------------------------------------------------

    def detect_throttling(self) -> tuple[bool, str]:
        cmd = (
            "$perf = Get-WmiObject -Class Win32_Processor "
            "-ErrorAction SilentlyContinue | Select-Object -First 1; "
            "$maxClock = $perf.MaxClockSpeed; "
            "$curClock = (Get-WmiObject -Namespace root/cimv2 "
            "-Class Win32_PerfFormattedData_Counters_ProcessorInformation "
            "-ErrorAction SilentlyContinue | Select-Object -First 1)"
            ".PercentofMaximumFrequency; "
            "Write-Output \"$maxClock|$curClock\""
        )
        ok, out, _ = PowerShellRunner.run(cmd, timeout=20)
        if not ok:
            return False, ""

        parts = out.strip().split("|")
        if len(parts) != 2:
            return False, ""

        try:
            max_clock = float(parts[0])
            pct_of_max = float(parts[1])
        except (ValueError, TypeError):
            return False, ""

        if max_clock <= 0:
            return False, ""

        if pct_of_max < 80.0:
            reason = (
                f"Frecuencia al {pct_of_max:.0f}% del máximo "
                f"({max_clock:.0f} MHz base)"
            )
            return True, reason

        return False, ""

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def get_snapshot(self) -> dict:
        cpu_temp = self.get_cpu_temp()
        gpu_temp = self.get_gpu_temp()
        is_throttling, throttle_reason = self.detect_throttling()

        cpu_usage = 0.0
        if PSUTIL_AVAILABLE:
            try:
                cpu_usage = psutil.cpu_percent(interval=0.5)
            except Exception:
                pass

        # Determine performance state
        if cpu_temp is not None and cpu_temp > 90:
            performance_state = "Critical"
        elif is_throttling or (cpu_temp is not None and cpu_temp > 80):
            performance_state = "Throttled"
        else:
            performance_state = "Normal"

        snapshot = {
            "cpu_temp": cpu_temp,
            "gpu_temp": gpu_temp,
            "cpu_usage": cpu_usage,
            "is_throttling": is_throttling,
            "throttle_reason": throttle_reason,
            "performance_state": performance_state,
        }
        return snapshot

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ThermalMonitor"
        )
        self._thread.start()
        logger.debug("TemperatureMonitor started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval + 2)
        self._thread = None
        logger.debug("TemperatureMonitor stopped")

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                snapshot = self.get_snapshot()
                if self.on_update:
                    self.on_update(snapshot)
            except Exception as exc:
                logger.warning("TemperatureMonitor error: %s", exc)
            time.sleep(self.interval)

    # ------------------------------------------------------------------
    # Advice
    # ------------------------------------------------------------------

    def get_thermal_advice(self, snapshot: dict) -> str:
        cpu_temp = snapshot.get("cpu_temp")
        is_throttling = snapshot.get("is_throttling", False)

        if cpu_temp is not None:
            if cpu_temp > 90:
                return "⚠️ CPU en zona crítica. Limpia el ventilador."
            if cpu_temp > 80:
                return "🔶 Temperatura alta. Considera pasta térmica."

        if is_throttling:
            return "⚡ Throttling activo. El CPU reduce velocidad por temperatura."

        return "✅ Temperatura normal."
