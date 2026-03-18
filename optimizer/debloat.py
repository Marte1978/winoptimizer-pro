"""
Módulo de eliminación de bloatware.
Detecta y elimina aplicaciones preinstaladas de Windows no esenciales.
"""
import json
import logging
from typing import Callable, Optional

from .core import PowerShellRunner, RegistryEditor

logger = logging.getLogger("WinOptimizer")

BLOATWARE_APPS: list[dict] = [
    {
        "name": "XboxApp",
        "display": "Xbox",
        "package_name": "Microsoft.XboxApp",
        "description": "Aplicación Xbox principal",
        "category": "xbox",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "XboxGameBar",
        "display": "Xbox Game Bar",
        "package_name": "Microsoft.XboxGamingOverlay",
        "description": "Barra de juegos Xbox (Win+G)",
        "category": "xbox",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "XboxGameOverlay",
        "display": "Xbox Game Overlay",
        "package_name": "Microsoft.XboxGameOverlay",
        "description": "Overlay de juegos Xbox",
        "category": "xbox",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "XboxSpeechToText",
        "display": "Xbox Speech To Text",
        "package_name": "Microsoft.XboxSpeechToTextOverlay",
        "description": "Voz a texto de Xbox",
        "category": "xbox",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "XboxIdentityProvider",
        "display": "Xbox Identity Provider",
        "package_name": "Microsoft.XboxIdentityProvider",
        "description": "Proveedor de identidad Xbox",
        "category": "xbox",
        "risk": "medium",
        "win10": True,
        "win11": True,
    },
    {
        "name": "MicrosoftTeams",
        "display": "Microsoft Teams (Personal)",
        "package_name": "MicrosoftTeams",
        "description": "Teams personal preinstalado (no el corporativo)",
        "category": "communication",
        "risk": "low",
        "win10": False,
        "win11": True,
    },
    {
        "name": "MixedReality",
        "display": "Mixed Reality Portal",
        "package_name": "Microsoft.MixedReality.Portal",
        "description": "Portal de realidad mixta/VR",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Cortana",
        "display": "Cortana",
        "package_name": "Microsoft.549981C3F5F10",
        "description": "Asistente virtual Cortana",
        "category": "ai_features",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Copilot",
        "display": "Windows Copilot",
        "package_name": "Microsoft.Copilot",
        "description": "Copilot IA integrado en Windows",
        "category": "ai_features",
        "risk": "low",
        "win10": False,
        "win11": True,
    },
    {
        "name": "WindowsRecall",
        "display": "Windows Recall",
        "package_name": "MicrosoftWindows.Client.AIX",
        "description": "Función de memoria/captura de pantalla IA",
        "category": "ai_features",
        "risk": "low",
        "win10": False,
        "win11": True,
    },
    {
        "name": "Solitaire",
        "display": "Microsoft Solitaire Collection",
        "package_name": "Microsoft.MicrosoftSolitaireCollection",
        "description": "Colección de juegos de solitario",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Skype",
        "display": "Skype",
        "package_name": "Microsoft.SkypeApp",
        "description": "Skype preinstalado",
        "category": "communication",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Spotify",
        "display": "Spotify (preinstalado)",
        "package_name": "SpotifyAB.SpotifyMusic",
        "description": "Spotify instalado por OEM/Microsoft",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "LinkedIn",
        "display": "LinkedIn",
        "package_name": "Microsoft.LinkedIn",
        "description": "App LinkedIn preinstalada",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "TikTok",
        "display": "TikTok (preinstalado)",
        "package_name": "ByteDance.TikTok",
        "description": "TikTok instalado por OEM",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "DisneyPlus",
        "display": "Disney+ (preinstalado)",
        "package_name": "Disney.37853FC22B2CE",
        "description": "Disney+ instalado por OEM",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Netflix",
        "display": "Netflix (preinstalado)",
        "package_name": "4DF9E0F8.Netflix",
        "description": "Netflix instalado por OEM",
        "category": "misc",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "3DViewer",
        "display": "3D Viewer",
        "package_name": "Microsoft.Microsoft3DViewer",
        "description": "Visor de modelos 3D",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "Paint3D",
        "display": "Paint 3D",
        "package_name": "Microsoft.MSPaint",
        "description": "Paint 3D (distinto del Paint clásico)",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": False,
    },
    {
        "name": "WindowsMaps",
        "display": "Windows Maps",
        "package_name": "Microsoft.WindowsMaps",
        "description": "Aplicación de mapas de Windows",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
    {
        "name": "GrooveMusic",
        "display": "Groove Music",
        "package_name": "Microsoft.ZuneMusic",
        "description": "Reproductor de música Groove",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": False,
    },
    {
        "name": "MoviesTV",
        "display": "Movies & TV",
        "package_name": "Microsoft.ZuneVideo",
        "description": "Reproductor de videos y películas",
        "category": "microsoft_apps",
        "risk": "low",
        "win10": True,
        "win11": True,
    },
]


class DebloatManager:
    """Gestiona la detección y eliminación de bloatware en Windows."""

    def __init__(
        self,
        change_tracker=None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.ps = PowerShellRunner()
        self.editor = RegistryEditor()
        self.tracker = change_tracker
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    def get_installed_apps(self) -> list[dict]:
        """Retorna lista de paquetes Appx instalados en el sistema."""
        self.progress_cb("Obteniendo apps instaladas...", 10)
        ok, out, err = self.ps.run(
            "Get-AppxPackage | Select-Object Name,PackageFullName | ConvertTo-Json -Depth 1",
            timeout=60,
        )
        if not ok or not out.strip():
            logger.warning(f"No se pudo obtener lista de apps: {err}")
            return []
        try:
            data = json.loads(out.strip())
            if isinstance(data, dict):
                data = [data]
            return data if isinstance(data, list) else []
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Get-AppxPackage: {e}")
            return []

    def is_installed(self, package_name: str) -> bool:
        """Verifica si un paquete Appx está instalado."""
        ok, out, _ = self.ps.run(
            f"Get-AppxPackage -Name '*{package_name}*' | Select-Object -ExpandProperty Name",
            timeout=30,
        )
        return ok and bool(out.strip())

    def remove_app(self, app: dict) -> bool:
        """Elimina una app Appx por su package_name."""
        pkg = app["package_name"]
        display = app["display"]
        self.progress_cb(f"Eliminando {display}...", 50)

        ok, out, err = self.ps.run(
            f"Get-AppxPackage -Name '*{pkg}*' | Remove-AppxPackage -ErrorAction SilentlyContinue",
            timeout=60,
        )

        if ok:
            logger.info(f"App eliminada: {display} ({pkg})")
            if self.tracker:
                self.tracker.record(
                    category="debloat",
                    action=f"remove_{app['name']}",
                    description=f"{display} eliminada",
                    revert_command=(
                        f"# Reinstalar desde Microsoft Store: buscar '{display}'"
                    ),
                )
            return True

        logger.warning(f"No se pudo eliminar {display}: {err}")
        return False

    def remove_selected(self, selected_names: list[str]) -> tuple[int, int]:
        """
        Elimina las apps cuyos 'name' estén en selected_names.
        Retorna (exitosas, fallidas).
        """
        apps_to_remove = [a for a in BLOATWARE_APPS if a["name"] in selected_names]
        total = len(apps_to_remove)
        ok_count = 0
        fail_count = 0

        for i, app in enumerate(apps_to_remove):
            pct = int(10 + (i / total) * 85) if total else 95
            self.progress_cb(f"Procesando {app['display']}...", pct)
            try:
                if self.remove_app(app):
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"Error eliminando {app['display']}: {e}")
                fail_count += 1

        self.progress_cb(
            f"Debloat completado: {ok_count} eliminadas, {fail_count} fallos.", 100
        )
        return ok_count, fail_count

    def optimize_all(self, selected_names: Optional[list[str]] = None) -> tuple[int, int]:
        """
        Elimina todas las apps de la lista (o solo las seleccionadas).
        Retorna (exitosas, fallidas).
        """
        names = selected_names or [a["name"] for a in BLOATWARE_APPS]
        return self.remove_selected(names)
