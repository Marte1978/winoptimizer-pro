import logging
import json
from typing import Callable, Optional
from .core import PowerShellRunner

logger = logging.getLogger("WinOptimizer")

TASK_PREFIX = "WinOptimizer_"
TASK_CLEANUP_WEEKLY = "WinOptimizer_WeeklyCleanup"
TASK_CLEANUP_MONTHLY = "WinOptimizer_MonthlyCleanup"


class AutoCleanScheduler:
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback

    def _notify(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)
        logger.info(message)

    def create_weekly_task(self, day: str = "Sunday", time: str = "03:00") -> bool:
        self._notify(f"Creando tarea semanal ({day} {time})...")
        cmd = (
            '$action = New-ScheduledTaskAction -Execute "PowerShell.exe" '
            '-Argument "-NonInteractive -WindowStyle Hidden -Command '
            '`"Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue; '
            'Clear-RecycleBin -Force -ErrorAction SilentlyContinue`""; '
            f'$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek {day} -At {time}; '
            '$settings = New-ScheduledTaskSettingsSet -RunOnlyIfIdle:$false -StartWhenAvailable:$true; '
            '$principal = New-ScheduledTaskPrincipal -RunLevel Highest -LogonType S4U -UserId "SYSTEM"; '
            f'Register-ScheduledTask -TaskName "{TASK_CLEANUP_WEEKLY}" '
            '-Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force'
        )
        ok, stdout, stderr = PowerShellRunner.run(cmd)
        if ok:
            self._notify("Tarea semanal creada correctamente.")
        else:
            logger.error(f"Error al crear tarea semanal: {stderr}")
        return ok

    def create_monthly_task(self, day_of_month: int = 1, time: str = "04:00") -> bool:
        self._notify(f"Creando tarea mensual (día {day_of_month} a las {time})...")
        clean_script = (
            "Remove-Item '$env:TEMP\\*' -Recurse -Force -EA SilentlyContinue; "
            "ipconfig /flushdns; "
            "Remove-Item 'C:\\Windows\\Prefetch\\*' -Force -EA SilentlyContinue; "
            "wevtutil el | ForEach-Object { wevtutil cl $_ 2>$null }"
        )
        cmd = (
            f'$action = New-ScheduledTaskAction -Execute "PowerShell.exe" '
            f'-Argument "-NonInteractive -WindowStyle Hidden -Command `"{clean_script}`""; '
            f'$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth {day_of_month} -At {time}; '
            '$settings = New-ScheduledTaskSettingsSet -RunOnlyIfIdle:$false -StartWhenAvailable:$true; '
            '$principal = New-ScheduledTaskPrincipal -RunLevel Highest -LogonType S4U -UserId "SYSTEM"; '
            f'Register-ScheduledTask -TaskName "{TASK_CLEANUP_MONTHLY}" '
            '-Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force'
        )
        ok, stdout, stderr = PowerShellRunner.run(cmd)
        if ok:
            self._notify("Tarea mensual creada correctamente.")
        else:
            logger.error(f"Error al crear tarea mensual: {stderr}")
        return ok

    def get_scheduled_tasks(self) -> list[dict]:
        cmd = (
            "Get-ScheduledTask -TaskPath '\\' | "
            "Where-Object {$_.TaskName -like 'WinOptimizer_*'} | "
            "Select-Object TaskName,State,"
            "@{N='NextRun';E={(Get-ScheduledTaskInfo $_.TaskName -ErrorAction SilentlyContinue).NextRunTime}} | "
            "ConvertTo-Json"
        )
        ok, stdout, stderr = PowerShellRunner.run(cmd)
        if not ok or not stdout.strip():
            return []
        try:
            raw = json.loads(stdout.strip())
            if isinstance(raw, dict):
                raw = [raw]
            results = []
            for item in raw:
                next_run = item.get("NextRun")
                if isinstance(next_run, dict):
                    next_run = next_run.get("value", "N/A")
                results.append({
                    "name": item.get("TaskName", ""),
                    "state": item.get("State", ""),
                    "next_run": str(next_run) if next_run else "N/A",
                })
            return results
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error(f"Error al parsear tareas programadas: {exc}")
            return []

    def remove_task(self, task_name: str) -> bool:
        self._notify(f"Eliminando tarea: {task_name}...")
        cmd = (
            f'Unregister-ScheduledTask -TaskName "{task_name}" '
            '-Confirm:$false -ErrorAction SilentlyContinue'
        )
        ok, stdout, stderr = PowerShellRunner.run(cmd)
        if ok:
            self._notify(f"Tarea '{task_name}' eliminada.")
        else:
            logger.error(f"Error al eliminar '{task_name}': {stderr}")
        return ok

    def run_cleanup_now(self, progress_cb: Optional[Callable] = None) -> tuple[int, int]:
        cb = progress_cb or self.progress_callback
        steps = [
            ("Limpiando carpeta TEMP...",
             "Remove-Item -Path \"$env:TEMP\\*\" -Recurse -Force -ErrorAction SilentlyContinue"),
            ("Vaciando Papelera de reciclaje...",
             "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"),
            ("Limpiando caché DNS...",
             "ipconfig /flushdns"),
            ("Limpiando Prefetch...",
             "Remove-Item -Path 'C:\\Windows\\Prefetch\\*' -Force -ErrorAction SilentlyContinue"),
            ("Limpiando Event Logs...",
             "wevtutil el | ForEach-Object { wevtutil cl $_ 2>$null }"),
        ]
        ok_count = 0
        fail_count = 0
        for message, cmd in steps:
            if cb:
                cb(message)
            logger.info(message)
            success, _, stderr = PowerShellRunner.run(cmd, timeout=60)
            if success:
                ok_count += 1
            else:
                fail_count += 1
                logger.warning(f"Fallo en paso '{message}': {stderr}")
        self._notify(f"Limpieza completada: {ok_count} OK, {fail_count} errores.")
        return ok_count, fail_count

    def is_task_registered(self, task_name: str) -> bool:
        cmd = (
            f"$t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
            "if ($t) { 'true' } else { 'false' }"
        )
        ok, stdout, _ = PowerShellRunner.run(cmd)
        return ok and stdout.strip().lower() == "true"

    def get_task_status(self) -> dict:
        tasks = self.get_scheduled_tasks()
        weekly_next = "N/A"
        monthly_next = "N/A"
        weekly_exists = False
        monthly_exists = False
        for task in tasks:
            if task["name"] == TASK_CLEANUP_WEEKLY:
                weekly_exists = True
                weekly_next = task["next_run"]
            elif task["name"] == TASK_CLEANUP_MONTHLY:
                monthly_exists = True
                monthly_next = task["next_run"]
        return {
            "weekly_exists": weekly_exists,
            "monthly_exists": monthly_exists,
            "weekly_next_run": weekly_next,
            "monthly_next_run": monthly_next,
        }
