"""
Agente Supabase para WinOptimizer Pro.
Conecta el exe local con el dashboard SaaS:
  1. Recolecta métricas del sistema via PerformanceMonitor
  2. Envía telemetría a /api/telemetry → obtiene log_id
  3. Solicita diagnóstico IA a /api/diagnose
  4. Retorna el plan de optimización al caller

Requiere: pip install requests psutil
"""
import hashlib
import json
import logging
import platform
import subprocess
import time
import uuid
from typing import Optional
import requests
import psutil

from optimizer.performance_monitor import PerformanceMonitor, PerformanceSnapshot

logger = logging.getLogger("WinOptimizer.SupabaseAgent")

# ─── Configuración ────────────────────────────────────────────────────────────
SAAS_BASE_URL = "https://win-optimizer-saas.vercel.app"
REQUEST_TIMEOUT = 30  # segundos


def _get_hardware_hash() -> str:
    """Genera un hash único y estable para este hardware (no cambia con el SO)."""
    try:
        cpu = platform.processor() or "unknown_cpu"
        machine = platform.machine() or "unknown_machine"
        node = platform.node() or str(uuid.getnode())
        raw = f"{cpu}-{machine}-{node}"
        return hashlib.sha256(raw.encode()).hexdigest()
    except Exception:
        return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()


def _get_storage_type() -> str:
    """Detecta si el disco C: es SSD, NVMe o HDD via PowerShell."""
    try:
        result = subprocess.run(
            [
                "powershell.exe", "-NonInteractive", "-NoProfile",
                "-Command",
                "Get-PhysicalDisk | Where-Object {$_.DeviceId -eq 0} | Select-Object -ExpandProperty MediaType",
            ],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
        )
        media = result.stdout.strip().upper()
        if "NVM" in media or "NVME" in media:
            return "NVMe"
        if "SSD" in media or "SOLID" in media:
            return "SSD"
        return "HDD"
    except Exception:
        return "HDD"


def _get_device_specs() -> dict:
    """Recopila especificaciones del hardware."""
    try:
        cpu_name = platform.processor() or "Unknown CPU"
        ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        storage_type = _get_storage_type()

        disk = psutil.disk_usage("C:\\")
        storage_gb = round(disk.total / (1024 ** 3), 0)

        os_name = f"{platform.system()} {platform.release()} {platform.version()}"

        return {
            "cpu": cpu_name,
            "ram_gb": ram_gb,
            "storage_type": storage_type,
            "storage_gb": int(storage_gb),
            "os": os_name,
        }
    except Exception as e:
        logger.warning(f"No se pudieron obtener specs: {e}")
        return {}


def _get_disk_latency_ms() -> float:
    """Mide latencia del disco C: con una lectura pequeña."""
    try:
        test_file = "C:\\Windows\\System32\\ntoskrnl.exe"
        start = time.perf_counter()
        with open(test_file, "rb") as f:
            f.read(4096)
        return round((time.perf_counter() - start) * 1000, 2)
    except Exception:
        return 0.0


def _get_page_faults_per_sec() -> float:
    """Obtiene page faults por segundo del sistema via WMI."""
    try:
        result = subprocess.run(
            [
                "powershell.exe", "-NonInteractive", "-NoProfile",
                "-Command",
                "(Get-Counter '\\Memory\\Page Faults/sec').CounterSamples.CookedValue",
            ],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
        )
        return round(float(result.stdout.strip()), 2)
    except Exception:
        return 0.0


def _snapshot_to_metrics(snap: PerformanceSnapshot) -> dict:
    """Convierte PerformanceSnapshot al formato que espera /api/telemetry."""
    disk_latency = _get_disk_latency_ms()
    page_faults = _get_page_faults_per_sec()

    mem = psutil.virtual_memory()
    ram_available_gb = round(mem.available / (1024 ** 3), 2)

    top_processes = []
    for p in snap.top_processes[:10]:
        top_processes.append({
            "name": p.get("name", "unknown"),
            "pid": p.get("pid", 0),
            "cpu_percent": round(p.get("cpu_percent", 0.0), 2),
            "ram_mb": round(p.get("ram_mb", 0.0), 1),
            "page_faults": 0,  # No disponible sin WMI avanzado
        })

    uptime_seconds = time.time() - psutil.boot_time()

    return {
        "cpu_percent": round(snap.cpu_percent, 2),
        "ram_used_gb": snap.ram_used_gb,
        "ram_total_gb": snap.ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "disk_latency_ms": disk_latency,
        "disk_read_speed_mbps": snap.disk_read_mbps,
        "disk_write_speed_mbps": snap.disk_write_mbps,
        "top_processes": top_processes,
        "page_faults_per_sec": page_faults,
        "uptime_hours": round(uptime_seconds / 3600, 1),
    }


class SupabaseAgent:
    """
    Agente que conecta WinOptimizer Pro con el dashboard SaaS.

    Uso básico:
        agent = SupabaseAgent(user_token="jwt_del_usuario")
        result = agent.run_diagnostic()
        if result:
            plan = result["plan"]
    """

    def __init__(self, user_token: str, device_name: Optional[str] = None):
        self.user_token = user_token
        self.device_name = device_name or platform.node()
        self.hardware_hash = _get_hardware_hash()
        self._monitor = PerformanceMonitor(interval=2.0)
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "WinOptimizerPro/1.0",
        })

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Hace POST al SaaS API con manejo de errores."""
        url = f"{SAAS_BASE_URL}{endpoint}"
        try:
            resp = self._session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 402:
                logger.warning("Créditos insuficientes para esta operación.")
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            logger.error(f"No se pudo conectar a {url}. ¿Hay conexión a internet?")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al conectar con {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {resp.status_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al llamar API: {e}")
            return None

    def collect_metrics(self) -> dict:
        """Recolecta métricas actuales del sistema."""
        logger.info("Recolectando métricas del sistema...")
        # Calentar el monitor para tener datos de velocidad de disco
        self._monitor.start()
        time.sleep(3)
        snap = self._monitor.get_snapshot()
        self._monitor.stop()
        return _snapshot_to_metrics(snap)

    def send_telemetry(self, metrics: dict) -> Optional[str]:
        """
        Envía métricas al SaaS y devuelve el log_id.
        Consume 1 crédito.
        """
        logger.info("Enviando telemetría al dashboard SaaS...")
        specs = _get_device_specs()

        payload = {
            "hardware_hash": self.hardware_hash,
            "device_name": self.device_name,
            "specs": specs,
            "metrics": metrics,
            "user_token": self.user_token,
        }

        result = self._post("/api/telemetry", payload)
        if not result:
            return None

        log_id = result.get("log_id")
        credits_remaining = result.get("credits_remaining", "?")
        logger.info(f"Telemetría registrada. Log ID: {log_id} | Créditos restantes: {credits_remaining}")
        return log_id

    def request_diagnosis(self, log_id: str) -> Optional[dict]:
        """
        Solicita diagnóstico IA para el log_id dado.
        Devuelve el plan de optimización o None si falla.
        """
        logger.info(f"Solicitando diagnóstico IA para log: {log_id}")
        payload = {
            "log_id": log_id,
            "user_token": self.user_token,
        }

        result = self._post("/api/diagnose", payload)
        if not result:
            return None

        plan = result.get("plan")
        logger.info(f"Diagnóstico recibido: {plan.get('summary', 'Sin resumen') if plan else 'Sin plan'}")
        return plan

    def run_diagnostic(self) -> Optional[dict]:
        """
        Flujo completo: recolecta métricas → envía telemetría → obtiene diagnóstico IA.

        Returns:
            dict con 'plan' y 'log_id', o None si algo falla.
        """
        try:
            metrics = self.collect_metrics()
            log_id = self.send_telemetry(metrics)
            if not log_id:
                return None

            plan = self.request_diagnosis(log_id)
            if not plan:
                return None

            return {"plan": plan, "log_id": log_id, "metrics": metrics}

        except Exception as e:
            logger.error(f"Error en diagnóstico completo: {e}")
            return None

    def send_jobs(
        self,
        log_id: str,
        applied_jobs: list[dict],
        metrics_after: Optional[dict] = None,
    ) -> bool:
        """
        Sincroniza los trabajos realizados con el dashboard SaaS.

        Args:
            log_id: ID del log obtenido en run_diagnostic().
            applied_jobs: Lista de entradas del ChangeTracker.
            metrics_after: Métricas del sistema tras la optimización (opcional).

        Returns:
            True si la sincronización fue exitosa.
        """
        if not applied_jobs:
            logger.warning("send_jobs: lista de trabajos vacía, nada que sincronizar.")
            return False

        logger.info(f"Sincronizando {len(applied_jobs)} trabajos con el dashboard (log: {log_id})...")

        payload: dict = {
            "log_id": log_id,
            "user_token": self.user_token,
            "applied_jobs": applied_jobs,
        }
        if metrics_after:
            payload["metrics_after"] = metrics_after

        result = self._post("/api/jobs", payload)
        if not result:
            logger.error("No se pudo sincronizar los trabajos con el dashboard.")
            return False

        synced = result.get("jobs_synced", 0)
        success = result.get("jobs_success", 0)
        errors = result.get("jobs_error", 0)
        score_after = result.get("score_after")
        logger.info(
            f"Trabajos sincronizados: {synced} total | {success} exitosos | {errors} con error"
            + (f" | Score después: {score_after}" if score_after is not None else "")
        )
        return True

    def print_plan(self, plan: dict) -> None:
        """Imprime el plan de optimización en consola (útil para debug)."""
        print("\n" + "=" * 60)
        print("  PLAN DE OPTIMIZACIÓN — WinOptimizer Pro IA")
        print("=" * 60)
        print(f"  Score del sistema: {plan.get('score', '?')}/100")
        print(f"  Resumen: {plan.get('summary', '')}")
        print("-" * 60)
        for i, step in enumerate(plan.get("steps", []), 1):
            risk = step.get("risk_level", "?").upper()
            cost = step.get("credits_cost", 1)
            print(f"\n  Paso {i}: {step.get('action', '')}")
            print(f"  Riesgo: {risk} | Costo: {cost} crédito(s)")
            print(f"  Justificación: {step.get('justification', '')}")
            if step.get("command"):
                print(f"  Comando: {step['command']}")
        print("=" * 60 + "\n")
