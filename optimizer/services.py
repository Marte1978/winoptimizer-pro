"""
Módulo de optimización de servicios de Windows.
Gestiona los servicios que pueden desactivarse de forma segura para mejorar rendimiento.
"""
import logging
from typing import Callable, Optional
from .core import ServiceManager

logger = logging.getLogger("WinOptimizer")

# Lista curada de servicios seguros para deshabilitar
# Formato: (nombre_servicio, descripción, riesgo, categoría)
SAFE_SERVICES_TO_DISABLE: list[dict] = [
    {
        "name": "SysMain",
        "display": "SysMain (Superfetch)",
        "description": "Precarga aplicaciones en RAM. En SSD es innecesario y puede causar alto uso de disco.",
        "risk": "low",
        "category": "performance",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "DoSvc",
        "display": "Delivery Optimization",
        "description": "Comparte partes de actualizaciones con otras PCs en la red. Consume ancho de banda.",
        "risk": "low",
        "category": "network",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "icssvc",
        "display": "Mobile Hotspot",
        "description": "Comparte conexión de Internet como punto de acceso WiFi. Innecesario en desktops.",
        "risk": "low",
        "category": "network",
        "win10": True,
        "win11": True,
        "desktop_only": True,
    },
    {
        "name": "PhoneSvc",
        "display": "Phone Service",
        "description": "Conexión entre PC y smartphone (Phone Link). Innecesario si no usas la app.",
        "risk": "low",
        "category": "connectivity",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "SCardSvr",
        "display": "Smart Card",
        "description": "Gestión de tarjetas inteligentes. Innecesario sin lector de tarjetas.",
        "risk": "low",
        "category": "hardware",
        "win10": True,
        "win11": True,
        "desktop_only": True,
    },
    {
        "name": "ScDeviceEnum",
        "display": "Smart Card Device Enum",
        "description": "Complemento del servicio de tarjetas inteligentes.",
        "risk": "low",
        "category": "hardware",
        "win10": True,
        "win11": True,
        "desktop_only": True,
    },
    {
        "name": "SensrSvc",
        "display": "Sensor Service",
        "description": "GPS, luz ambiental y otros sensores. Innecesario en PCs de escritorio.",
        "risk": "low",
        "category": "hardware",
        "win10": True,
        "win11": True,
        "desktop_only": True,
    },
    {
        "name": "lfsvc",
        "display": "Geolocation Service",
        "description": "Servicios de ubicación GPS. Innecesario en desktops sin GPS.",
        "risk": "low",
        "category": "privacy",
        "win10": True,
        "win11": True,
        "desktop_only": True,
    },
    {
        "name": "bthserv",
        "display": "Bluetooth Support",
        "description": "Soporte Bluetooth. Deshabilitar solo si no usas dispositivos Bluetooth.",
        "risk": "low",
        "category": "hardware",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "WMPNetworkSvc",
        "display": "Windows Media Player Network",
        "description": "Comparte biblioteca multimedia de Windows Media Player en red.",
        "risk": "low",
        "category": "media",
        "win10": True,
        "win11": False,
        "desktop_only": False,
    },
    {
        "name": "RetailDemo",
        "display": "Retail Demo Service",
        "description": "Modo demo para tiendas. Completamente innecesario en equipos personales.",
        "risk": "low",
        "category": "bloatware",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "XblGameSave",
        "display": "Xbox Game Save",
        "description": "Sincronización de guardado de Xbox. Innecesario si no usas Xbox Game Pass.",
        "risk": "low",
        "category": "gaming",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "XblAuthManager",
        "display": "Xbox Live Auth Manager",
        "description": "Autenticación de Xbox Live. Innecesario sin Xbox Game Pass.",
        "risk": "low",
        "category": "gaming",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "XboxNetApiSvc",
        "display": "Xbox Live Networking",
        "description": "Red de Xbox Live. Innecesario sin servicios de Xbox.",
        "risk": "low",
        "category": "gaming",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "diagsvc",
        "display": "Diagnostic Execution Service",
        "description": "Ejecución de scripts de diagnóstico. Puede deshabilitar con seguridad.",
        "risk": "low",
        "category": "diagnostics",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
    {
        "name": "DiagTrack",
        "display": "Connected User Experiences & Telemetry",
        "description": "Telemetría de Microsoft. Envía datos de uso a Microsoft. Impacto de privacidad.",
        "risk": "low",
        "category": "privacy",
        "win10": True,
        "win11": True,
        "desktop_only": False,
    },
]


class ServicesOptimizer:
    """Optimizador de servicios de Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.svc_mgr = ServiceManager()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def get_available_services(self, is_win11: bool = False) -> list[dict]:
        """Retorna servicios disponibles filtrando por versión de Windows."""
        return [
            s for s in SAFE_SERVICES_TO_DISABLE
            if (is_win11 and s["win11"]) or (not is_win11 and s["win10"])
        ]

    def get_current_status(self, service_name: str) -> str:
        """Obtiene el estado actual del tipo de inicio de un servicio."""
        return self.svc_mgr.get_startup_type(service_name) or "Unknown"

    def disable_service(self, service: dict) -> bool:
        """Deshabilita un servicio y registra el cambio."""
        name = service["name"]
        display = service["display"]

        if not self.svc_mgr.service_exists(name):
            logger.debug(f"Servicio no encontrado: {name}")
            return False

        # Registrar el estado actual para reversión
        original_type = self.svc_mgr.get_startup_type(name)

        # Detener el servicio
        self.svc_mgr.stop_service(name)

        # Deshabilitar el inicio automático
        ok = self.svc_mgr.set_startup_type(name, "Disabled")

        if ok:
            logger.info(f"Servicio deshabilitado: {display} (era: {original_type})")
            if self.tracker:
                self.tracker.record(
                    category="services",
                    action=f"disable_{name}",
                    description=f"Deshabilitado: {display}",
                    revert_command=(
                        f"Set-Service -Name '{name}' -StartupType {original_type or 'Manual'}"
                    ),
                )
        return ok

    def enable_service(self, service_name: str, startup_type: str = "Manual") -> bool:
        """Reactiva un servicio previamente deshabilitado."""
        ok = self.svc_mgr.set_startup_type(service_name, startup_type)
        if ok:
            logger.info(f"Servicio reactivado: {service_name} → {startup_type}")
        return ok

    def optimize_all(
        self,
        selected_services: Optional[list[str]] = None,
        is_win11: bool = False,
    ) -> tuple[int, int]:
        """
        Deshabilita todos los servicios seleccionados.
        Retorna (exitosos, fallidos).
        """
        services = self.get_available_services(is_win11)
        if selected_services is not None:
            services = [s for s in services if s["name"] in selected_services]

        total = len(services)
        ok_count = 0
        fail_count = 0

        for i, svc in enumerate(services):
            pct = int(((i + 1) / total) * 100) if total > 0 else 100
            self.progress_cb(f"Procesando servicio: {svc['display']}...", pct)

            if self.disable_service(svc):
                ok_count += 1
            else:
                fail_count += 1

        return ok_count, fail_count
