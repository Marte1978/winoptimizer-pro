"""
Monitor de rendimiento en tiempo real para WinOptimizer Pro.
Usa psutil para obtener métricas de CPU, RAM, Disco y Red.
"""
import threading
import time
from typing import Callable, Optional
from dataclasses import dataclass, field


@dataclass
class PerformanceSnapshot:
    cpu_percent: float = 0.0
    cpu_freq_mhz: float = 0.0
    cpu_cores_logical: int = 0
    cpu_per_core: list[float] = field(default_factory=list)
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    ram_percent: float = 0.0
    disk_read_mbps: float = 0.0
    disk_write_mbps: float = 0.0
    net_sent_mbps: float = 0.0
    net_recv_mbps: float = 0.0
    top_processes: list[dict] = field(default_factory=list)


class PerformanceMonitor:
    """Monitor de rendimiento continuo. Actualiza métricas cada `interval` segundos."""

    def __init__(self, interval: float = 2.0, on_update: Optional[Callable[[PerformanceSnapshot], None]] = None):
        self._interval = interval
        self._on_update = on_update
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_disk_io = None
        self._last_net_io = None
        self._last_time = None
        self._psutil_available = False
        self._load_psutil()

    def _load_psutil(self) -> None:
        try:
            import psutil  # noqa: F401
            self._psutil_available = True
        except ImportError:
            self._psutil_available = False

    def start(self) -> None:
        if self._running or not self._psutil_available:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def get_snapshot(self) -> PerformanceSnapshot:
        """Obtiene una instantánea actual sin polling continuo."""
        if not self._psutil_available:
            return PerformanceSnapshot()
        return self._collect()

    def _loop(self) -> None:
        while self._running:
            try:
                snap = self._collect()
                if self._on_update:
                    self._on_update(snap)
            except Exception:
                pass
            time.sleep(self._interval)

    def _collect(self) -> PerformanceSnapshot:
        import psutil

        snap = PerformanceSnapshot()

        # CPU
        snap.cpu_percent = psutil.cpu_percent(interval=None)
        snap.cpu_cores_logical = psutil.cpu_count(logical=True) or 0
        try:
            freq = psutil.cpu_freq()
            snap.cpu_freq_mhz = freq.current if freq else 0.0
        except Exception:
            snap.cpu_freq_mhz = 0.0
        try:
            snap.cpu_per_core = psutil.cpu_percent(percpu=True) or []
        except Exception:
            snap.cpu_per_core = []

        # RAM
        mem = psutil.virtual_memory()
        snap.ram_total_gb = round(mem.total / (1024 ** 3), 1)
        snap.ram_used_gb = round(mem.used / (1024 ** 3), 1)
        snap.ram_percent = mem.percent

        # Disco (velocidad diferencial)
        now = time.time()
        try:
            disk_io = psutil.disk_io_counters()
            if self._last_disk_io and self._last_time:
                dt = now - self._last_time
                if dt > 0:
                    snap.disk_read_mbps = round(
                        (disk_io.read_bytes - self._last_disk_io.read_bytes) / (1024 ** 2) / dt, 2
                    )
                    snap.disk_write_mbps = round(
                        (disk_io.write_bytes - self._last_disk_io.write_bytes) / (1024 ** 2) / dt, 2
                    )
            self._last_disk_io = disk_io
        except Exception:
            pass

        # Red (velocidad diferencial)
        try:
            net_io = psutil.net_io_counters()
            if self._last_net_io and self._last_time:
                dt = now - self._last_time
                if dt > 0:
                    snap.net_sent_mbps = round(
                        (net_io.bytes_sent - self._last_net_io.bytes_sent) / (1024 ** 2) / dt, 2
                    )
                    snap.net_recv_mbps = round(
                        (net_io.bytes_recv - self._last_net_io.bytes_recv) / (1024 ** 2) / dt, 2
                    )
            self._last_net_io = net_io
        except Exception:
            pass

        self._last_time = now

        # Top 5 procesos por CPU
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    info = p.info
                    ram_mb = round(info["memory_info"].rss / (1024 ** 2), 1) if info["memory_info"] else 0
                    procs.append({
                        "name": info["name"] or "?",
                        "cpu": info["cpu_percent"] or 0.0,
                        "ram_mb": ram_mb,
                    })
                except Exception:
                    pass
            snap.top_processes = sorted(procs, key=lambda x: x["cpu"], reverse=True)[:5]
        except Exception:
            snap.top_processes = []

        return snap

    @property
    def is_available(self) -> bool:
        return self._psutil_available
