"""
Módulo de limpieza del sistema.
Elimina archivos temporales, caché, logs y componentes obsoletos del sistema.
"""
import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .core import PowerShellRunner

logger = logging.getLogger("WinOptimizer")


class DiskCleaner:
    """Limpia archivos temporales y espacio desperdiciado en disco."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.ps = PowerShellRunner()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def _get_folder_size_mb(self, folder: str) -> float:
        """Calcula el tamaño de una carpeta en MB."""
        total = 0
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except (PermissionError, FileNotFoundError):
                        pass
        except Exception:
            pass
        return round(total / (1024 * 1024), 2)

    def clean_user_temp(self) -> tuple[bool, float]:
        """Limpia la carpeta TEMP del usuario."""
        temp_dir = os.environ.get("TEMP", "")
        if not temp_dir or not os.path.exists(temp_dir):
            return False, 0.0

        size_before = self._get_folder_size_mb(temp_dir)
        self.progress_cb(f"Limpiando TEMP ({size_before:.1f} MB)...", 20)

        deleted = 0
        failed = 0
        for item in Path(temp_dir).iterdir():
            try:
                if item.is_file():
                    item.unlink(missing_ok=True)
                    deleted += 1
                elif item.is_dir():
                    shutil.rmtree(str(item), ignore_errors=True)
                    deleted += 1
            except Exception:
                failed += 1

        freed = size_before - self._get_folder_size_mb(temp_dir)
        logger.info(f"TEMP limpiada: {freed:.1f} MB liberados, {deleted} elementos, {failed} errores")

        if self.tracker:
            self.tracker.record(
                category="cleanup",
                action="clean_user_temp",
                description=f"TEMP usuario limpiada: {freed:.1f} MB liberados",
            )

        return True, freed

    def clean_system_temp(self) -> tuple[bool, float]:
        """Limpia la carpeta TEMP del sistema (C:\\Windows\\Temp)."""
        system_temp = r"C:\Windows\Temp"
        if not os.path.exists(system_temp):
            return False, 0.0

        size_before = self._get_folder_size_mb(system_temp)
        self.progress_cb(f"Limpiando Windows Temp ({size_before:.1f} MB)...", 40)

        ok, _, _ = self.ps.run(
            f'Remove-Item -Path "{system_temp}\\*" -Recurse -Force -ErrorAction SilentlyContinue'
        )

        freed = size_before - self._get_folder_size_mb(system_temp)
        logger.info(f"Windows Temp limpiada: {freed:.1f} MB liberados")

        if self.tracker:
            self.tracker.record(
                category="cleanup",
                action="clean_system_temp",
                description=f"Windows Temp limpiada: {freed:.1f} MB liberados",
            )

        return True, freed

    def clean_recycle_bin(self) -> tuple[bool, float]:
        """Vacía la Papelera de reciclaje."""
        self.progress_cb("Vaciando Papelera de Reciclaje...", 55)

        ok, _, err = self.ps.run(
            "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
        )

        logger.info("Papelera de reciclaje vaciada.")
        if self.tracker:
            self.tracker.record(
                category="cleanup",
                action="empty_recycle_bin",
                description="Papelera de reciclaje vaciada",
            )

        return True, 0.0

    def clean_windows_update_cache(self) -> tuple[bool, float]:
        """Limpia la caché de Windows Update (SoftwareDistribution\\Download)."""
        sw_dist = r"C:\Windows\SoftwareDistribution\Download"
        if not os.path.exists(sw_dist):
            return False, 0.0

        size_before = self._get_folder_size_mb(sw_dist)
        self.progress_cb(f"Limpiando caché de Windows Update ({size_before:.1f} MB)...", 65)

        # Detener Windows Update temporalmente
        self.ps.run("Stop-Service -Name 'wuauserv' -Force -ErrorAction SilentlyContinue")
        self.ps.run("Stop-Service -Name 'bits' -Force -ErrorAction SilentlyContinue")

        ok, _, _ = self.ps.run(
            f'Remove-Item -Path "{sw_dist}\\*" -Recurse -Force -ErrorAction SilentlyContinue'
        )

        # Reiniciar Windows Update
        self.ps.run("Start-Service -Name 'wuauserv' -ErrorAction SilentlyContinue")
        self.ps.run("Start-Service -Name 'bits' -ErrorAction SilentlyContinue")

        freed = size_before - self._get_folder_size_mb(sw_dist)
        logger.info(f"Caché Windows Update limpiada: {freed:.1f} MB liberados")

        if self.tracker:
            self.tracker.record(
                category="cleanup",
                action="clean_wu_cache",
                description=f"Caché Windows Update: {freed:.1f} MB liberados",
            )

        return True, freed

    def run_dism_cleanup(self) -> tuple[bool, str]:
        """
        Ejecuta DISM para limpiar el Component Store (WinSxS).
        Puede tardar varios minutos. Libera 2-15 GB típicamente.
        """
        self.progress_cb("Ejecutando DISM cleanup (puede tardar varios minutos)...", 75)

        ok, out, err = self.ps.run(
            "Dism.exe /Online /Cleanup-Image /StartComponentCleanup 2>&1",
            timeout=600,  # Hasta 10 minutos
        )

        if ok:
            logger.info("DISM cleanup completado exitosamente.")
            msg = "DISM WinSxS cleanup completado."
            if self.tracker:
                self.tracker.record(
                    category="cleanup",
                    action="dism_cleanup",
                    description="DISM WinSxS Component Store limpiado",
                )
        else:
            logger.warning(f"DISM cleanup con advertencia: {err[:200]}")
            msg = f"DISM completado con advertencias: {err[:100]}"

        return ok, msg

    def clean_event_logs(self) -> bool:
        """Limpia los logs de eventos de Windows."""
        self.progress_cb("Limpiando logs de eventos...", 85)

        ok, _, _ = self.ps.run(
            "wevtutil el | ForEach-Object { "
            "  wevtutil cl $_ 2>$null "
            "}"
        )

        if ok:
            logger.info("Logs de eventos limpiados.")
            if self.tracker:
                self.tracker.record(
                    category="cleanup",
                    action="clean_event_logs",
                    description="Logs de eventos de Windows limpiados",
                )

        return ok

    def check_trim_status(self) -> bool:
        """Verifica si TRIM está habilitado para SSDs."""
        try:
            result = subprocess.run(
                ["fsutil", "behavior", "query", "disabledeletenotify"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # DisableDeleteNotify = 0 → TRIM HABILITADO
            return "= 0" in result.stdout
        except Exception:
            return False

    def enable_trim(self) -> bool:
        """Habilita TRIM para SSDs si está deshabilitado."""
        try:
            result = subprocess.run(
                ["fsutil", "behavior", "set", "disabledeletenotify", "0"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ok = result.returncode == 0
            if ok:
                logger.info("TRIM habilitado para SSDs.")
                if self.tracker:
                    self.tracker.record(
                        category="cleanup",
                        action="enable_trim",
                        description="TRIM habilitado para SSDs",
                        revert_command="fsutil behavior set disabledeletenotify 1",
                    )
            return ok
        except Exception:
            return False

    def clean_all(
        self,
        run_dism: bool = False,
        clean_event_logs: bool = False,
    ) -> dict:
        """Ejecuta todas las limpiezas. Retorna un resumen."""
        total_freed = 0.0
        results = {}

        # 1. TEMP usuario
        ok, freed = self.clean_user_temp()
        results["user_temp"] = {"ok": ok, "freed_mb": freed}
        total_freed += freed

        # 2. TEMP sistema
        ok, freed = self.clean_system_temp()
        results["system_temp"] = {"ok": ok, "freed_mb": freed}
        total_freed += freed

        # 3. Papelera
        ok, freed = self.clean_recycle_bin()
        results["recycle_bin"] = {"ok": ok, "freed_mb": freed}

        # 4. Windows Update cache
        ok, freed = self.clean_windows_update_cache()
        results["wu_cache"] = {"ok": ok, "freed_mb": freed}
        total_freed += freed

        # 5. TRIM
        if not self.check_trim_status():
            ok = self.enable_trim()
            results["trim"] = {"ok": ok}
        else:
            results["trim"] = {"ok": True, "note": "Ya habilitado"}

        # 6. DISM (opcional, lento)
        if run_dism:
            ok, msg = self.run_dism_cleanup()
            results["dism"] = {"ok": ok, "message": msg}

        # 7. Event logs (opcional)
        if clean_event_logs:
            ok = self.clean_event_logs()
            results["event_logs"] = {"ok": ok}

        results["total_freed_mb"] = round(total_freed, 2)
        self.progress_cb(
            f"✅ Limpieza completada: {total_freed:.1f} MB liberados.", 100
        )
        return results
