"""
Módulo de optimización de red.
Aplica tweaks TCP/IP para reducir latencia y mejorar velocidad de conexión.
"""
import logging
import subprocess
import winreg
from typing import Callable, Optional

from .core import PowerShellRunner, RegistryEditor

logger = logging.getLogger("WinOptimizer")


class NetworkOptimizer:
    """Optimiza la configuración de red de Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.ps = PowerShellRunner()
        self.editor = RegistryEditor()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def disable_nagle_algorithm(self) -> bool:
        """
        Deshabilita el algoritmo de Nagle para reducir latencia en gaming online.
        El algoritmo agrupa paquetes TCP pequeños causando micro-delays de 10-200ms.
        """
        self.progress_cb("Deshabilitando algoritmo de Nagle...", 25)

        # Obtener GUIDs de adaptadores de red activos
        ok, out, _ = self.ps.run(
            "Get-ChildItem -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' "
            "| Select-Object -ExpandProperty PSChildName"
        )

        if not ok or not out.strip():
            logger.warning("No se encontraron adaptadores de red en el registro.")
            return False

        success_count = 0
        guids = [g.strip() for g in out.strip().splitlines() if g.strip()]

        for guid in guids:
            path = rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}"

            # Verificar que el adaptador tiene dirección IP (está activo)
            ip_addr = self.editor.get_value("HKLM", path, "DhcpIPAddress") or \
                      self.editor.get_value("HKLM", path, "IPAddress")

            if not ip_addr or ip_addr in ("0.0.0.0", ""):
                continue  # Adaptador inactivo, omitir

            ok1, _ = self.editor.set_value("HKLM", path, "TcpAckFrequency", 1, winreg.REG_DWORD)
            ok2, _ = self.editor.set_value("HKLM", path, "TcpNoDelay", 1, winreg.REG_DWORD)

            if ok1 or ok2:
                success_count += 1
                logger.debug(f"Nagle deshabilitado en adaptador: {guid}")

        if success_count > 0:
            logger.info(f"Algoritmo de Nagle deshabilitado en {success_count} adaptadores.")
            if self.tracker:
                self.tracker.record(
                    category="network",
                    action="disable_nagle",
                    description=f"Algoritmo de Nagle deshabilitado ({success_count} adaptadores)",
                    revert_command=(
                        "Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | "
                        "ForEach-Object { Remove-ItemProperty -Path $_.PSPath -Name 'TcpAckFrequency','TcpNoDelay' -ErrorAction SilentlyContinue }"
                    ),
                )
            return True

        return False

    def optimize_tcp_settings(self) -> bool:
        """Optimiza configuraciones TCP/IP globales del sistema."""
        self.progress_cb("Optimizando configuraciones TCP...", 50)

        commands = [
            # Habilitar autotuning para mejor throughput
            "netsh int tcp set global autotuninglevel=normal",
            # Habilitar timestamps (mejora retransmisión)
            "netsh int tcp set global timestamps=disabled",
            # Configurar RSS (Receive Side Scaling) para multicore
            "netsh int tcp set global rss=enabled",
            # Habilitar chimney offloading
            "netsh int tcp set global chimney=disabled",  # Deshabilitado por compatibilidad
            # Direct Cache Access
            "netsh int tcp set global dca=enabled",
            # NetDMA
            "netsh int tcp set global netdma=enabled",
            # ECN (Explicit Congestion Notification)
            "netsh int tcp set global ecncapability=enabled",
        ]

        ok_count = 0
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    ok_count += 1
            except Exception:
                pass

        if ok_count > 0:
            logger.info(f"TCP optimizado: {ok_count}/{len(commands)} comandos exitosos.")
            if self.tracker:
                self.tracker.record(
                    category="network",
                    action="optimize_tcp",
                    description=f"Configuraciones TCP optimizadas ({ok_count}/{len(commands)})",
                )
            return True

        return False

    def disable_network_throttling(self) -> bool:
        """Deshabilita el throttling de red en el perfil multimedia."""
        self.progress_cb("Deshabilitando Network Throttling...", 75)

        ok, _ = self.editor.set_value(
            "HKLM",
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
            "NetworkThrottlingIndex",
            0xFFFFFFFF,
            winreg.REG_DWORD,
        )

        if ok:
            logger.info("Network Throttling deshabilitado.")
            if self.tracker:
                self.tracker.record(
                    category="network",
                    action="disable_network_throttling",
                    description="Network Throttling deshabilitado (0xFFFFFFFF)",
                    revert_command=(
                        "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile' "
                        "-Name 'NetworkThrottlingIndex' -Value 10"
                    ),
                )
        return ok

    def flush_dns(self) -> bool:
        """Limpia la caché DNS del sistema."""
        self.progress_cb("Limpiando caché DNS...", 90)
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            ok = result.returncode == 0
            if ok:
                logger.info("Caché DNS limpiada.")
            return ok
        except Exception:
            return False

    def optimize_dns_for_speed(self) -> bool:
        """Cambia el DNS de los adaptadores activos a Cloudflare (1.1.1.1) para mayor velocidad."""
        self.progress_cb("Configurando DNS Cloudflare 1.1.1.1...", 20)

        script = (
            "$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }; "
            "$count = 0; "
            "foreach ($a in $adapters) { "
            "  try { Set-DnsClientServerAddress -InterfaceIndex $a.InterfaceIndex "
            "    -ServerAddresses ('1.1.1.1','1.0.0.1') -ErrorAction Stop; $count++ "
            "  } catch {} "
            "}; "
            "Write-Output \"OK:$count\""
        )
        ok, out, _ = self.ps.run(script)

        if ok and "OK:" in out:
            count = out.strip().split("OK:")[-1].strip()
            logger.info(f"DNS Cloudflare configurado en {count} adaptador(es).")
            if self.tracker:
                self.tracker.record(
                    category="network",
                    action="dns_cloudflare",
                    description=f"DNS cambiado a Cloudflare 1.1.1.1/1.0.0.1 ({count} adaptadores)",
                    revert_command=(
                        "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | "
                        "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex "
                        "-ResetServerAddresses -ErrorAction SilentlyContinue }"
                    ),
                )
            return True
        return False

    def boost_dns_cache(self) -> bool:
        """Aumenta el tamaño y tiempo de vida del caché DNS de Windows."""
        self.progress_cb("Ampliando caché DNS de Windows...", 40)

        base_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
        results = []
        for name, value in [
            ("CacheHashTableBucketSize", 1),
            ("CacheHashTableSize", 384),
            ("MaxCacheEntryTtlLimit", 64000),
            ("MaxSOACacheEntryTtlLimit", 301),
        ]:
            ok, _ = self.editor.set_value("HKLM", base_path, name, value, winreg.REG_DWORD)
            results.append(ok)

        if any(results):
            logger.info("Caché DNS de Windows optimizado.")
            if self.tracker:
                self.tracker.record(
                    category="network",
                    action="boost_dns_cache",
                    description="Caché DNS ampliado para resolución más rápida",
                )
            return True
        return False

    def optimize_all(self) -> tuple[int, int]:
        """Aplica todas las optimizaciones de red."""
        ok_count = 0
        fail_count = 0

        optimizations = [
            (self.disable_nagle_algorithm, "Deshabilitar Nagle"),
            (self.optimize_tcp_settings, "Optimizar TCP"),
            (self.disable_network_throttling, "Deshabilitar Network Throttling"),
            (self.flush_dns, "Limpiar DNS"),
            (self.optimize_dns_for_speed, "DNS Cloudflare"),
            (self.boost_dns_cache, "Boost caché DNS"),
        ]

        for func, name in optimizations:
            try:
                if func():
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"Error en optimización de red '{name}': {e}")
                fail_count += 1

        self.progress_cb(f"✅ Red optimizada: {ok_count} éxitos, {fail_count} fallos.", 100)
        return ok_count, fail_count
