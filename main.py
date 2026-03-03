"""
WinOptimizer Pro v1.0
Optimizador de rendimiento para Windows 10 y Windows 11.

Desarrollado con SaaS Factory V3 methodology.
Stack: Python 3.10+ | CustomTkinter | PowerShell Engine
"""
import sys
import os

# Fix SSL certifi path when running as PyInstaller onefile bundle
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _cert = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")
    if os.path.isfile(_cert):
        os.environ["SSL_CERT_FILE"] = _cert
        os.environ["REQUESTS_CA_BUNDLE"] = _cert

import threading
import logging
from datetime import datetime
from typing import Optional

# Verificar Python 3.10+
if sys.version_info < (3, 10):
    import tkinter as tk
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror("Error", "WinOptimizer Pro requiere Python 3.10 o superior.")
    sys.exit(1)

import customtkinter as ctk
from tkinter import messagebox

# Configurar CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Imports locales
from utils.admin import is_admin, request_admin
from utils.logger import setup_logger, ChangeTracker
from utils.compatibility import get_system_summary
from optimizer.backup import BackupManager
from optimizer.services import ServicesOptimizer, SAFE_SERVICES_TO_DISABLE
from optimizer.registry import RegistryOptimizer, REGISTRY_TWEAKS
from optimizer.power import PowerOptimizer
from optimizer.cleanup import DiskCleaner
from optimizer.network import NetworkOptimizer
from optimizer.visual import VisualOptimizer
from optimizer.ai_assistant import AIAssistant
from optimizer.performance_monitor import PerformanceMonitor, PerformanceSnapshot
from optimizer.supabase_agent import SupabaseAgent, SessionExpiredError, InsufficientCreditsError

logger = setup_logger("WinOptimizer")

# ─── Constantes de diseño ────────────────────────────────────────────────────
COLOR_BG = "#0f0f0f"
COLOR_CARD = "#1a1a2e"
COLOR_ACCENT = "#00d4aa"
COLOR_ACCENT2 = "#3b82f6"
COLOR_DANGER = "#ef4444"
COLOR_WARNING = "#f59e0b"
COLOR_SUCCESS = "#10b981"
COLOR_TEXT = "#e2e8f0"
COLOR_MUTED = "#94a3b8"
COLOR_BORDER = "#2d3748"
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_HEADING = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 9)
FONT_CODE = ("Consolas", 10)

APP_VERSION = "1.0.0"
APP_NAME = "WinOptimizer Pro"


class WinOptimizerApp(ctk.CTk):
    """Aplicación principal del optimizador de Windows."""

    def __init__(self):
        super().__init__()

        # Inicializar componentes
        self.tracker = ChangeTracker()
        self.system_info = get_system_summary()
        self.is_laptop = self._detect_laptop()
        self._current_section = "dashboard"
        self._optimization_running = False
        self._backup_created = False
        self._backup_data: Optional[dict] = None
        self._progress_var = ctk.DoubleVar(value=0)
        self._status_var = ctk.StringVar(value="Listo")
        self._checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self._section_frames: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        # SaaS connection
        self._saas_token: Optional[str] = None
        self._saas_agent: Optional[SupabaseAgent] = None
        self._saas_email: str = ""
        self._saas_last_log_id: Optional[str] = None  # log_id del último diagnóstico

        # Monitor de rendimiento
        self._perf_monitor = PerformanceMonitor(interval=2.0, on_update=self._on_perf_update)
        self._perf_widgets: dict = {}  # widgets de la sección monitor
        self._activity_log: list[dict] = []  # registro de actividad en tiempo real

        # Inicializar optimizadores
        def make_progress(msg, pct):
            self._update_progress(msg, pct)

        self.backup_mgr = BackupManager(progress_callback=make_progress)
        self.svc_opt = ServicesOptimizer(self.tracker, make_progress)
        self.reg_opt = RegistryOptimizer(self.tracker, make_progress)
        self.pwr_opt = PowerOptimizer(self.tracker, make_progress)
        self.clean_opt = DiskCleaner(self.tracker, make_progress)
        self.net_opt = NetworkOptimizer(self.tracker, make_progress)
        self.vis_opt = VisualOptimizer(self.tracker, make_progress)
        self.ai_assistant = AIAssistant()

        # Configurar ventana
        self._setup_window()
        self._build_ui()
        self._show_section("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Limpia recursos antes de cerrar."""
        self._perf_monitor.stop()
        self.destroy()

    def _detect_laptop(self) -> bool:
        """Detecta si el equipo es una laptop."""
        try:
            from optimizer.core import PowerShellRunner
            ps = PowerShellRunner()
            ok, out, _ = ps.run(
                "(Get-WmiObject -Class Win32_Battery -ErrorAction SilentlyContinue) -ne $null"
            )
            return ok and "True" in out
        except Exception:
            return False

    def _setup_window(self) -> None:
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x720")
        self.minsize(960, 640)
        self.configure(fg_color=COLOR_BG)

        # Centrar en pantalla
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

        # Icono
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

    def _build_ui(self) -> None:
        """Construye toda la interfaz de usuario."""
        # Layout principal: sidebar + contenido
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        self._build_status_bar()

    # ─── SIDEBAR ─────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, fg_color="#111827", width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(0, weight=1)

        # Contenedor scrollable para todo el contenido del sidebar
        scroll_frame = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="#111827",
            corner_radius=0,
            scrollbar_button_color="#4a5568",
            scrollbar_button_hover_color=COLOR_ACCENT,
            scrollbar_fg_color="#1a202c",
        )
        scroll_frame.grid(row=0, column=0, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Logo / título
        logo_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(20, 8), sticky="ew")

        ctk.CTkLabel(
            logo_frame,
            text="⚡ WinOptimizer",
            font=("Segoe UI", 16, "bold"),
            text_color=COLOR_ACCENT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame,
            text=f"Pro v{APP_VERSION}",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(anchor="w")

        # Sistema info rápida
        win_ver = self.system_info.get("product_name", "Windows")
        ram = self.system_info.get("ram_gb", 0)
        build = self.system_info.get("build", 0)
        info_frame = ctk.CTkFrame(scroll_frame, fg_color="#1f2937", corner_radius=8)
        info_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(
            info_frame,
            text=f"🖥  {win_ver}",
            font=FONT_SMALL,
            text_color=COLOR_TEXT,
            wraplength=180,
        ).pack(anchor="w", padx=10, pady=(6, 2))
        ctk.CTkLabel(
            info_frame,
            text=f"🔧 Build {build}  |  💾 {ram} GB RAM",
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=10, pady=(0, 6))

        if self.is_laptop:
            ctk.CTkLabel(
                info_frame,
                text="💻 Laptop detectada",
                font=FONT_SMALL,
                text_color=COLOR_WARNING,
            ).pack(anchor="w", padx=10, pady=(0, 6))

        # Separador
        ctk.CTkFrame(scroll_frame, height=1, fg_color=COLOR_BORDER).grid(
            row=2, column=0, padx=12, pady=4, sticky="ew"
        )

        # Navegación
        nav_items = [
            ("dashboard", "🏠  Dashboard", "Vista general del sistema"),
            ("monitor", "📊  Monitor", "Rendimiento en tiempo real"),
            ("diagnostics", "🔍  Diagnóstico", "Análisis completo del sistema"),
            ("activity", "⚡  Actividad", "Optimizaciones aplicadas"),
            ("services", "⚙️  Servicios", "Gestionar servicios de Windows"),
            ("registry", "🔧  Registro", "Tweaks del registro"),
            ("power", "⚡  Energía", "Plan de energía y CPU"),
            ("cleanup", "🧹  Limpieza", "Archivos temporales y caché"),
            ("network", "🌐  Red", "Optimización de red y TCP"),
            ("visual", "👁  Visual", "Efectos visuales"),
            ("log", "📋  Historial", "Historial de cambios"),
            ("ai", "🤖  Asistente IA", "Recomendaciones con inteligencia artificial"),
        ]

        nav_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        nav_frame.grid(row=3, column=0, padx=8, pady=4, sticky="ew")

        for i, (section_id, label, tooltip) in enumerate(nav_items):
            btn = ctk.CTkButton(
                nav_frame,
                text=label,
                font=FONT_BODY,
                fg_color="transparent",
                hover_color="#1f2937",
                text_color=COLOR_MUTED,
                anchor="w",
                height=36,
                corner_radius=6,
                command=lambda s=section_id: self._show_section(s),
            )
            btn.grid(row=i, column=0, padx=4, pady=2, sticky="ew")
            nav_frame.grid_columnconfigure(0, weight=1)
            self._nav_buttons[section_id] = btn

        # Botones de acción en la parte inferior
        ctk.CTkFrame(scroll_frame, height=1, fg_color=COLOR_BORDER).grid(
            row=4, column=0, padx=12, pady=4, sticky="ew"
        )

        action_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        action_frame.grid(row=5, column=0, padx=8, pady=8, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        # Botón Backup
        ctk.CTkButton(
            action_frame,
            text="🛡  Crear Backup",
            font=FONT_BODY,
            fg_color="#1e3a5f",
            hover_color="#1e4d7b",
            text_color=COLOR_TEXT,
            height=36,
            command=self._create_backup_thread,
        ).grid(row=0, column=0, padx=4, pady=3, sticky="ew")

        # Botón Aplicar Todo
        self._apply_btn = ctk.CTkButton(
            action_frame,
            text="🚀  Aplicar Todo",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#00b894",
            text_color="#000000",
            height=42,
            command=self._apply_all_thread,
        )
        self._apply_btn.grid(row=1, column=0, padx=4, pady=3, sticky="ew")

        # Botón Revertir
        ctk.CTkButton(
            action_frame,
            text="↩  Revertir Cambios",
            font=FONT_BODY,
            fg_color="#7c2d12",
            hover_color="#991b1b",
            text_color=COLOR_TEXT,
            height=36,
            command=self._revert_changes_thread,
        ).grid(row=2, column=0, padx=4, pady=(3, 16), sticky="ew")

    # ─── ÁREA PRINCIPAL ───────────────────────────────────────────────────────

    def _build_main_area(self) -> None:
        self._main_frame = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self._main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._main_frame.grid_columnconfigure(0, weight=1)
        self._main_frame.grid_rowconfigure(1, weight=1)

        # Header con título de sección
        self._header_frame = ctk.CTkFrame(
            self._main_frame, fg_color="#111827", height=60, corner_radius=0
        )
        self._header_frame.grid(row=0, column=0, sticky="ew")
        self._header_frame.grid_propagate(False)

        self._section_title = ctk.CTkLabel(
            self._header_frame,
            text="Dashboard",
            font=FONT_TITLE,
            text_color=COLOR_TEXT,
        )
        self._section_title.pack(side="left", padx=24, pady=10)

        # Contenedor de secciones (stack de frames)
        self._content_area = ctk.CTkFrame(
            self._main_frame, fg_color=COLOR_BG, corner_radius=0
        )
        self._content_area.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._content_area.grid_columnconfigure(0, weight=1)
        self._content_area.grid_rowconfigure(0, weight=1)

        # Construir todas las secciones
        self._build_dashboard()
        self._build_monitor_section()
        self._build_diagnostics_section()
        self._build_activity_section()
        self._build_services_section()
        self._build_registry_section()
        self._build_power_section()
        self._build_cleanup_section()
        self._build_network_section()
        self._build_visual_section()
        self._build_log_section()
        self._build_ai_section()

        # Habilitar scroll con rueda del ratón en todas las secciones (fix Windows)
        self.after(200, self._setup_all_mousewheel)

    def _build_status_bar(self) -> None:
        """Barra de estado inferior con barra de progreso."""
        status_bar = ctk.CTkFrame(self, fg_color="#111827", height=50, corner_radius=0)
        status_bar.grid(row=1, column=1, sticky="ew")
        status_bar.grid_propagate(False)
        status_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            status_bar,
            textvariable=self._status_var,
            font=FONT_BODY,
            text_color=COLOR_MUTED,
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        self._progress_bar = ctk.CTkProgressBar(
            status_bar,
            variable=self._progress_var,
            progress_color=COLOR_ACCENT,
            fg_color=COLOR_BORDER,
            width=300,
        )
        self._progress_bar.grid(row=0, column=1, padx=16, sticky="e")
        self._progress_bar.set(0)

    # ─── SECCIONES ────────────────────────────────────────────────────────────

    def _make_section_frame(self, name: str) -> ctk.CTkScrollableFrame:
        """Crea un frame de sección scrollable."""
        frame = ctk.CTkScrollableFrame(
            self._content_area,
            fg_color=COLOR_BG,
            scrollbar_button_color="#4a5568",
            scrollbar_button_hover_color=COLOR_ACCENT,
            corner_radius=0,
        )
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        self._section_frames[name] = frame
        return frame

    def _bind_mousewheel(self, scroll_frame: ctk.CTkScrollableFrame) -> None:
        """Enlaza el scroll de la rueda del ratón a todos los hijos (fix Windows)."""
        canvas = getattr(scroll_frame, "_parent_canvas", None)
        if canvas is None:
            return

        def _on_wheel(event):
            canvas.yview_scroll(-int(event.delta / 120), "units")

        def _bind_recursive(widget):
            try:
                widget.bind("<MouseWheel>", _on_wheel, add="+")
            except Exception:
                pass
            for child in widget.winfo_children():
                _bind_recursive(child)

        _bind_recursive(scroll_frame)

    def _setup_all_mousewheel(self) -> None:
        """Aplica el binding de mousewheel a todas las secciones."""
        for frame in self._section_frames.values():
            self._bind_mousewheel(frame)

    def _build_dashboard(self) -> None:
        frame = self._make_section_frame("dashboard")

        # Título de bienvenida
        welcome = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=12)
        welcome.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        ctk.CTkLabel(
            welcome,
            text=f"⚡ Bienvenido a {APP_NAME}",
            font=FONT_TITLE,
            text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            welcome,
            text=(
                "Optimiza tu PC con Windows en un solo clic. "
                "Siempre crea un punto de restauración antes de aplicar cambios."
            ),
            font=FONT_BODY,
            text_color=COLOR_MUTED,
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # Tarjetas de información del sistema
        cards_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cards_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cards_data = [
            ("🖥", "Sistema", self.system_info.get("product_name", "Windows"), COLOR_ACCENT2),
            ("💾", "RAM Total", f"{self.system_info.get('ram_gb', 0)} GB", COLOR_ACCENT),
            ("💿", "SSD", "Detectado" if self.system_info.get("has_ssd") else "HDD", COLOR_SUCCESS),
            ("🏗", "Build", str(self.system_info.get("build", 0)), COLOR_WARNING),
        ]

        for col, (icon, title, value, color) in enumerate(cards_data):
            card = ctk.CTkFrame(cards_frame, fg_color=COLOR_CARD, corner_radius=10)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="ew")

            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 24)).pack(pady=(12, 4))
            ctk.CTkLabel(card, text=title, font=FONT_SMALL, text_color=COLOR_MUTED).pack()
            ctk.CTkLabel(card, text=value, font=("Segoe UI", 12, "bold"),
                        text_color=color, wraplength=150).pack(pady=(0, 12))

        # Advertencias / recomendaciones
        warn_frame = ctk.CTkFrame(frame, fg_color="#1a1a0a", corner_radius=10,
                                   border_width=1, border_color=COLOR_WARNING)
        warn_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(
            warn_frame,
            text="⚠️  Recomendaciones antes de optimizar:",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_WARNING,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        warnings = [
            "1. Haz clic en '🛡 Crear Backup' para crear un punto de restauración del sistema.",
            "2. Cierra todas las aplicaciones importantes antes de aplicar cambios.",
            "3. Revisa cada sección y desmarca las optimizaciones que no desees aplicar.",
            "4. Reinicia el equipo después de aplicar las optimizaciones para que surtan efecto.",
        ]
        if self.is_laptop:
            warnings.append(
                "5. ⚡ Laptop detectada: el plan 'Ultimate Performance' NO se aplicará "
                "(consume más batería). Se usará 'High Performance'."
            )

        for w_text in warnings:
            ctk.CTkLabel(
                warn_frame,
                text=w_text,
                font=FONT_BODY,
                text_color=COLOR_TEXT,
                wraplength=680,
                justify="left",
            ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkLabel(warn_frame, text="").pack(pady=4)  # Espaciado inferior

        # Resumen de optimizaciones disponibles
        summary_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        summary_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(
            summary_frame,
            text="📊 Optimizaciones Disponibles",
            font=FONT_HEADING,
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(12, 8))

        summary_items = [
            ("⚙️  Servicios", f"{len(SAFE_SERVICES_TO_DISABLE)} servicios innecesarios a deshabilitar"),
            ("🔧  Registro", f"{len(REGISTRY_TWEAKS)} tweaks de rendimiento y gaming"),
            ("⚡  Energía", "Plan Ultimate Performance + configuración CPU"),
            ("🧹  Limpieza", "Temporales, caché Windows Update, WinSxS"),
            ("🌐  Red", "Algoritmo de Nagle, TCP, Network Throttling"),
            ("👁   Visual", "Animaciones, transparencia, efectos visuales"),
        ]

        for icon_text, desc in summary_items:
            row = ctk.CTkFrame(summary_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=icon_text, font=FONT_BODY, text_color=COLOR_ACCENT,
                        width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=desc, font=FONT_BODY, text_color=COLOR_MUTED,
                        anchor="w").pack(side="left", padx=8)

        ctk.CTkLabel(summary_frame, text="").pack(pady=4)

        # ── Conectar con Dashboard SaaS ──────────────────────────────────────
        saas_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=12,
                                  border_width=1, border_color="#00d4aa")
        saas_card.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        saas_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            saas_card,
            text="☁  Dashboard SaaS — Diagnóstico con IA",
            font=FONT_HEADING, text_color=COLOR_ACCENT,
        ).grid(row=0, column=0, columnspan=3, padx=16, pady=(14, 4), sticky="w")

        ctk.CTkLabel(
            saas_card,
            text="Conecta tu cuenta para enviar métricas y ver resultados en el dashboard web.",
            font=FONT_BODY, text_color=COLOR_MUTED,
        ).grid(row=1, column=0, columnspan=3, padx=16, pady=(0, 10), sticky="w")

        # Fila email
        ctk.CTkLabel(saas_card, text="Email:", font=FONT_BODY,
                     text_color=COLOR_TEXT, width=65, anchor="w",
                     ).grid(row=2, column=0, padx=(16, 4), pady=4, sticky="w")
        self._saas_email_var = ctk.StringVar()
        ctk.CTkEntry(saas_card, textvariable=self._saas_email_var,
                     font=FONT_BODY, fg_color="#0d1117", text_color=COLOR_TEXT,
                     border_color=COLOR_BORDER, placeholder_text="tu@email.com",
                     height=34,
                     ).grid(row=2, column=1, padx=4, pady=4, sticky="ew")

        # Fila password
        ctk.CTkLabel(saas_card, text="Clave:", font=FONT_BODY,
                     text_color=COLOR_TEXT, width=65, anchor="w",
                     ).grid(row=3, column=0, padx=(16, 4), pady=4, sticky="w")
        self._saas_pass_var = ctk.StringVar()
        ctk.CTkEntry(saas_card, textvariable=self._saas_pass_var,
                     font=FONT_BODY, fg_color="#0d1117", text_color=COLOR_TEXT,
                     border_color=COLOR_BORDER, placeholder_text="contraseña",
                     show="*", height=34,
                     ).grid(row=3, column=1, padx=4, pady=4, sticky="ew")

        # Botones
        btn_row = ctk.CTkFrame(saas_card, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=3, padx=16, pady=(8, 4), sticky="ew")

        self._saas_connect_btn = ctk.CTkButton(
            btn_row, text="Conectar", font=FONT_BODY,
            fg_color=COLOR_ACCENT2, hover_color="#2563eb",
            text_color=COLOR_TEXT, width=110, height=36,
            command=self._saas_login,
        )
        self._saas_connect_btn.pack(side="left", padx=(0, 8))

        self._saas_diag_btn = ctk.CTkButton(
            btn_row, text="Enviar Diagnóstico IA",
            font=FONT_BODY, fg_color=COLOR_ACCENT, hover_color="#00b894",
            text_color="#000000", width=180, height=36,
            state="disabled", command=self._saas_diagnose,
        )
        self._saas_diag_btn.pack(side="left", padx=(0, 8))

        self._saas_sync_btn = ctk.CTkButton(
            btn_row, text="Sincronizar Trabajos",
            font=FONT_BODY, fg_color="#7c3aed", hover_color="#6d28d9",
            text_color=COLOR_TEXT, width=175, height=36,
            state="disabled", command=self._saas_sync_jobs,
        )
        self._saas_sync_btn.pack(side="left")

        self._saas_status_lbl = ctk.CTkLabel(
            saas_card, text="No conectado",
            font=FONT_SMALL, text_color=COLOR_MUTED,
        )
        self._saas_status_lbl.grid(row=5, column=0, columnspan=3,
                                    padx=16, pady=(4, 14), sticky="w")


    def _build_services_section(self) -> None:
        frame = self._make_section_frame("services")

        ctk.CTkLabel(
            frame,
            text=(
                "Selecciona los servicios que deseas deshabilitar. "
                "Todos los servicios listados son seguros de deshabilitar según el uso de tu PC."
            ),
            font=FONT_BODY,
            text_color=COLOR_MUTED,
            wraplength=700,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        is_win11 = self.system_info.get("is_win11", False)
        services = self.svc_opt.get_available_services(is_win11)

        # Agrupar por categoría
        categories: dict[str, list] = {}
        for svc in services:
            cat = svc.get("category", "other")
            categories.setdefault(cat, []).append(svc)

        CAT_NAMES = {
            "performance": "🚀 Rendimiento",
            "network": "🌐 Red",
            "hardware": "🔌 Hardware",
            "connectivity": "📡 Conectividad",
            "privacy": "🔒 Privacidad",
            "media": "🎵 Multimedia",
            "bloatware": "🗑  Bloatware",
            "gaming": "🎮 Gaming",
            "diagnostics": "🔍 Diagnóstico",
        }

        row_idx = 1
        for cat, svcs in categories.items():
            cat_name = CAT_NAMES.get(cat, cat.title())
            cat_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            cat_frame.grid(row=row_idx, column=0, padx=20, pady=6, sticky="ew")
            cat_frame.grid_columnconfigure(0, weight=1)
            row_idx += 1

            ctk.CTkLabel(
                cat_frame, text=cat_name, font=FONT_HEADING, text_color=COLOR_TEXT
            ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

            for j, svc in enumerate(svcs):
                svc_row = ctk.CTkFrame(cat_frame, fg_color="transparent")
                svc_row.grid(row=j + 1, column=0, padx=16, pady=3, sticky="ew")
                svc_row.grid_columnconfigure(1, weight=1)

                cb_var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(
                    svc_row,
                    text="",
                    variable=cb_var,
                    checkbox_width=18,
                    checkbox_height=18,
                    checkmark_color="#000000",
                    fg_color=COLOR_ACCENT,
                    border_color=COLOR_BORDER,
                )
                cb.grid(row=0, column=0, padx=(0, 8))
                self._checkboxes[f"svc_{svc['name']}"] = cb

                ctk.CTkLabel(
                    svc_row,
                    text=svc["display"],
                    font=("Segoe UI", 11, "bold"),
                    text_color=COLOR_TEXT,
                    anchor="w",
                ).grid(row=0, column=1, sticky="w")

                risk_colors = {"low": COLOR_SUCCESS, "medium": COLOR_WARNING, "high": COLOR_DANGER}
                risk_text = {"low": "Riesgo bajo", "medium": "Riesgo medio", "high": "Riesgo alto"}
                risk_lvl = svc.get("risk", "low")
                ctk.CTkLabel(
                    svc_row,
                    text=risk_text.get(risk_lvl, ""),
                    font=FONT_SMALL,
                    text_color=risk_colors.get(risk_lvl, COLOR_MUTED),
                ).grid(row=0, column=2, padx=8)

                ctk.CTkLabel(
                    svc_row,
                    text=svc["description"],
                    font=FONT_SMALL,
                    text_color=COLOR_MUTED,
                    anchor="w",
                    wraplength=500,
                ).grid(row=1, column=1, columnspan=2, sticky="w")

            ctk.CTkLabel(cat_frame, text="").grid(row=row_idx + 100, padx=0, pady=4)

    def _build_registry_section(self) -> None:
        frame = self._make_section_frame("registry")

        ctk.CTkLabel(
            frame,
            text=(
                "Tweaks del registro de Windows. Cada cambio tiene una descripción clara, "
                "nivel de riesgo y puede revertirse. Un punto de restauración se creará automáticamente."
            ),
            font=FONT_BODY,
            text_color=COLOR_MUTED,
            wraplength=700,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        categories: dict[str, list] = {}
        for tweak in REGISTRY_TWEAKS:
            cat = tweak.get("category", "other")
            categories.setdefault(cat, []).append(tweak)

        CAT_NAMES = {
            "performance": "🚀 Rendimiento General",
            "startup": "⚡ Inicio del Sistema",
            "gaming": "🎮 Gaming y Multimedia",
            "network": "🌐 Red",
            "visual": "👁  Visual",
            "ui": "🖥  Interfaz de Usuario",
        }

        row_idx = 1
        for cat, tweaks in categories.items():
            cat_name = CAT_NAMES.get(cat, cat.title())
            cat_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            cat_frame.grid(row=row_idx, column=0, padx=20, pady=6, sticky="ew")
            cat_frame.grid_columnconfigure(0, weight=1)
            row_idx += 1

            ctk.CTkLabel(
                cat_frame, text=cat_name, font=FONT_HEADING, text_color=COLOR_TEXT
            ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

            for j, tweak in enumerate(tweaks):
                t_row = ctk.CTkFrame(cat_frame, fg_color="transparent")
                t_row.grid(row=j + 1, column=0, padx=16, pady=4, sticky="ew")
                t_row.grid_columnconfigure(1, weight=1)

                cb_var = ctk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(
                    t_row, text="", variable=cb_var,
                    checkbox_width=18, checkbox_height=18,
                    checkmark_color="#000000", fg_color=COLOR_ACCENT,
                    border_color=COLOR_BORDER,
                )
                cb.grid(row=0, column=0, padx=(0, 8))
                self._checkboxes[f"reg_{tweak['id']}"] = cb

                ctk.CTkLabel(
                    t_row, text=tweak["name"],
                    font=("Segoe UI", 11, "bold"), text_color=COLOR_TEXT, anchor="w",
                ).grid(row=0, column=1, sticky="w")

                risk_colors = {"low": COLOR_SUCCESS, "medium": COLOR_WARNING}
                ctk.CTkLabel(
                    t_row,
                    text=f"Riesgo {tweak.get('risk', 'bajo')}",
                    font=FONT_SMALL,
                    text_color=risk_colors.get(tweak.get("risk", "low"), COLOR_MUTED),
                ).grid(row=0, column=2, padx=8)

                ctk.CTkLabel(
                    t_row, text=tweak["description"],
                    font=FONT_SMALL, text_color=COLOR_MUTED, anchor="w", wraplength=550,
                ).grid(row=1, column=1, columnspan=2, sticky="w")

                # Mostrar la ruta del registro
                reg_path = f"{tweak['hive']}\\{tweak['path']}\\{tweak['name_key']} = {tweak['value']}"
                ctk.CTkLabel(
                    t_row, text=reg_path,
                    font=FONT_CODE, text_color="#64748b", anchor="w", wraplength=550,
                ).grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 4))

            ctk.CTkLabel(cat_frame, text="").grid(row=999, padx=0, pady=4)

    def _build_power_section(self) -> None:
        frame = self._make_section_frame("power")

        info_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        info_frame.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")

        ctk.CTkLabel(
            info_frame, text="⚡ Plan de Energía y CPU",
            font=FONT_HEADING, text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        laptop_note = " (para laptops se usará High Performance)" if self.is_laptop else ""
        ctk.CTkLabel(
            info_frame,
            text=(
                f"Configura Windows para máximo rendimiento{laptop_note}. "
                "Habilita el plan Ultimate Performance (oculto por defecto en Windows), "
                "configura el procesador al 100% y optimiza las opciones de energía."
            ),
            font=FONT_BODY, text_color=COLOR_MUTED, wraplength=700,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        options = [
            ("pwr_ultimate", "⚡ Plan Ultimate Performance",
             "Activa el plan de energía más agresivo de Windows. Elimina micro-latencias del CPU.",
             not self.is_laptop),
            ("pwr_processor", "🔥 Procesador al 100% constante",
             "Configura el estado mínimo/máximo del procesador al 100%. Sin throttling de frecuencia.",
             not self.is_laptop),
            ("pwr_hibernation", "💤 Deshabilitar hibernación",
             "Libera espacio en disco equivalente al tamaño de tu RAM. En SSD mejora el rendimiento.",
             not self.is_laptop),
        ]

        for row_i, (key, title, desc, default) in enumerate(options):
            opt_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            opt_frame.grid(row=row_i + 1, column=0, padx=20, pady=6, sticky="ew")
            opt_frame.grid_columnconfigure(1, weight=1)

            cb_var = ctk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(
                opt_frame, text="", variable=cb_var,
                checkbox_width=20, checkbox_height=20,
                checkmark_color="#000000", fg_color=COLOR_ACCENT,
                border_color=COLOR_BORDER,
            )
            cb.grid(row=0, column=0, padx=16, pady=16)
            self._checkboxes[key] = cb

            ctk.CTkLabel(
                opt_frame, text=title, font=("Segoe UI", 12, "bold"), text_color=COLOR_TEXT
            ).grid(row=0, column=1, padx=8, pady=(12, 4), sticky="w")
            ctk.CTkLabel(
                opt_frame, text=desc, font=FONT_BODY, text_color=COLOR_MUTED, wraplength=600
            ).grid(row=1, column=1, padx=8, pady=(0, 12), sticky="w")

            if self.is_laptop and not default:
                ctk.CTkLabel(
                    opt_frame,
                    text="⚠️ No recomendado para laptops con batería",
                    font=FONT_SMALL, text_color=COLOR_WARNING,
                ).grid(row=2, column=1, padx=8, pady=(0, 8), sticky="w")

    def _build_cleanup_section(self) -> None:
        frame = self._make_section_frame("cleanup")

        options = [
            ("clean_user_temp", "🗂  Limpiar carpeta TEMP del usuario",
             "Elimina archivos temporales de aplicaciones en %TEMP%", True),
            ("clean_system_temp", "🗂  Limpiar Windows\\Temp",
             "Elimina archivos temporales del sistema operativo", True),
            ("clean_recycle_bin", "🗑  Vaciar Papelera de Reciclaje",
             "Vacía la Papelera de todos los usuarios", True),
            ("clean_wu_cache", "🔄  Limpiar caché de Windows Update",
             "Elimina archivos de actualización descargados pero no instalados. Puede liberar varios GB.", True),
            ("clean_trim", "💿  Verificar/Habilitar TRIM (SSD)",
             "Verifica que TRIM está habilitado en SSDs para mantener el rendimiento", True),
            ("clean_dism", "⚙️  Limpiar WinSxS con DISM",
             "Limpia el Component Store de Windows. Puede liberar 2-15 GB. LENTO (5-10 min).", False),
            ("clean_event_logs", "📋  Limpiar logs de eventos",
             "Elimina los logs del Visor de Eventos de Windows", False),
        ]

        ctk.CTkLabel(
            frame, text="Selecciona qué limpiar. Las opciones lentas están desactivadas por defecto.",
            font=FONT_BODY, text_color=COLOR_MUTED, wraplength=700,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        for row_i, (key, title, desc, default) in enumerate(options):
            opt_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            opt_frame.grid(row=row_i + 1, column=0, padx=20, pady=6, sticky="ew")
            opt_frame.grid_columnconfigure(1, weight=1)

            cb_var = ctk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(
                opt_frame, text="", variable=cb_var,
                checkbox_width=20, checkbox_height=20,
                checkmark_color="#000000", fg_color=COLOR_ACCENT,
                border_color=COLOR_BORDER,
            )
            cb.grid(row=0, column=0, padx=16, pady=14)
            self._checkboxes[key] = cb

            ctk.CTkLabel(
                opt_frame, text=title, font=("Segoe UI", 12, "bold"), text_color=COLOR_TEXT
            ).grid(row=0, column=1, padx=8, pady=(12, 4), sticky="w")
            ctk.CTkLabel(
                opt_frame, text=desc, font=FONT_BODY, text_color=COLOR_MUTED, wraplength=600
            ).grid(row=1, column=1, padx=8, pady=(0, 12), sticky="w")

    def _build_network_section(self) -> None:
        frame = self._make_section_frame("network")

        options = [
            ("net_nagle", "🎮  Deshabilitar Algoritmo de Nagle",
             "Reduce latencia en juegos online y aplicaciones de tiempo real. Puede ahorrar 10-200ms de latencia.", True),
            ("net_tcp", "📡  Optimizar configuraciones TCP",
             "Ajusta parámetros TCP/IP para mejor throughput y menor latencia. Incluye RSS, autotuning.", True),
            ("net_throttling", "🚫  Deshabilitar Network Throttling",
             "Elimina la limitación de ancho de banda que Windows impone a apps multimedia.", True),
            ("net_dns", "🔄  Limpiar caché DNS",
             "Limpia la caché DNS del sistema para resolver IPs actualizadas.", True),
        ]

        ctk.CTkLabel(
            frame,
            text="Optimizaciones de red para reducir latencia y mejorar velocidad de conexión.",
            font=FONT_BODY, text_color=COLOR_MUTED, wraplength=700,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        for row_i, (key, title, desc, default) in enumerate(options):
            opt_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            opt_frame.grid(row=row_i + 1, column=0, padx=20, pady=6, sticky="ew")
            opt_frame.grid_columnconfigure(1, weight=1)

            cb_var = ctk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(
                opt_frame, text="", variable=cb_var,
                checkbox_width=20, checkbox_height=20,
                checkmark_color="#000000", fg_color=COLOR_ACCENT,
                border_color=COLOR_BORDER,
            )
            cb.grid(row=0, column=0, padx=16, pady=14)
            self._checkboxes[key] = cb

            ctk.CTkLabel(
                opt_frame, text=title, font=("Segoe UI", 12, "bold"), text_color=COLOR_TEXT
            ).grid(row=0, column=1, padx=8, pady=(12, 4), sticky="w")
            ctk.CTkLabel(
                opt_frame, text=desc, font=FONT_BODY, text_color=COLOR_MUTED, wraplength=600
            ).grid(row=1, column=1, padx=8, pady=(0, 12), sticky="w")

    def _build_visual_section(self) -> None:
        frame = self._make_section_frame("visual")

        ctk.CTkLabel(
            frame,
            text="Deshabilitar efectos visuales libera CPU y RAM. Ideal para PCs con recursos limitados.",
            font=FONT_BODY, text_color=COLOR_MUTED, wraplength=700,
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        options = [
            ("vis_performance", "🚀  Modo Rendimiento Visual",
             "Configura VisualFXSetting = 2 (mejor rendimiento). Desactiva sombras, efectos, etc.", True),
            ("vis_animations", "🎬  Deshabilitar animaciones de ventanas",
             "Elimina las animaciones de minimizar/maximizar. Interfaz inmediatamente más rápida.", True),
            ("vis_transparency", "🔮  Deshabilitar transparencia del sistema",
             "Elimina los efectos de cristal/transparencia de la barra de tareas y menús.", False),
            ("vis_aero_shake", "🪟  Deshabilitar Aero Shake",
             "Deshabilita la función de sacudir una ventana para minimizar las demás.", True),
        ]

        for row_i, (key, title, desc, default) in enumerate(options):
            opt_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            opt_frame.grid(row=row_i + 1, column=0, padx=20, pady=6, sticky="ew")
            opt_frame.grid_columnconfigure(1, weight=1)

            cb_var = ctk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(
                opt_frame, text="", variable=cb_var,
                checkbox_width=20, checkbox_height=20,
                checkmark_color="#000000", fg_color=COLOR_ACCENT,
                border_color=COLOR_BORDER,
            )
            cb.grid(row=0, column=0, padx=16, pady=14)
            self._checkboxes[key] = cb

            ctk.CTkLabel(
                opt_frame, text=title, font=("Segoe UI", 12, "bold"), text_color=COLOR_TEXT
            ).grid(row=0, column=1, padx=8, pady=(12, 4), sticky="w")
            ctk.CTkLabel(
                opt_frame, text=desc, font=FONT_BODY, text_color=COLOR_MUTED, wraplength=600
            ).grid(row=1, column=1, padx=8, pady=(0, 12), sticky="w")

    # ─── MONITOR DE RENDIMIENTO ───────────────────────────────────────────────

    def _build_monitor_section(self) -> None:
        frame = self._make_section_frame("monitor")
        frame.grid_columnconfigure(0, weight=1)

        if not self._perf_monitor.is_available:
            card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
            card.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
            ctk.CTkLabel(
                card,
                text="⚠️  psutil no instalado",
                font=FONT_HEADING, text_color=COLOR_WARNING,
            ).pack(padx=20, pady=(16, 4))
            ctk.CTkLabel(
                card,
                text="Instala psutil para activar el monitor:\n\npip install psutil",
                font=FONT_CODE, text_color=COLOR_MUTED,
            ).pack(padx=20, pady=(0, 16))
            return

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        hdr.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="📊 Monitor de Rendimiento en Tiempo Real",
            font=FONT_HEADING, text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(
            hdr, text="Actualiza cada 2 segundos automáticamente.",
            font=FONT_SMALL, text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # ── Fila superior: CPU y RAM ────────────────────────────────────────
        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.grid(row=1, column=0, padx=20, pady=4, sticky="ew")
        top_row.grid_columnconfigure((0, 1), weight=1)

        cpu_card = self._make_metric_card(top_row, col=0, icon="🖥", title="CPU")
        ram_card = self._make_metric_card(top_row, col=1, icon="💾", title="RAM")

        self._perf_widgets["cpu_bar"] = self._add_gauge(cpu_card, "Uso CPU", COLOR_ACCENT)
        self._perf_widgets["cpu_label"] = self._add_gauge_label(cpu_card)
        self._perf_widgets["cpu_freq"] = self._add_sub_label(cpu_card, "Frecuencia: --")
        self._perf_widgets["cpu_cores"] = self._add_sub_label(cpu_card, "Núcleos: --")

        self._perf_widgets["ram_bar"] = self._add_gauge(ram_card, "Uso RAM", COLOR_ACCENT2)
        self._perf_widgets["ram_label"] = self._add_gauge_label(ram_card)
        self._perf_widgets["ram_detail"] = self._add_sub_label(ram_card, "-- / -- GB")

        # ── Fila media: Disco y Red ─────────────────────────────────────────
        mid_row = ctk.CTkFrame(frame, fg_color="transparent")
        mid_row.grid(row=2, column=0, padx=20, pady=4, sticky="ew")
        mid_row.grid_columnconfigure((0, 1), weight=1)

        disk_card = self._make_metric_card(mid_row, col=0, icon="💿", title="Disco")
        net_card = self._make_metric_card(mid_row, col=1, icon="🌐", title="Red")

        self._perf_widgets["disk_read"] = self._add_sub_label(disk_card, "Lectura:  -- MB/s")
        self._perf_widgets["disk_write"] = self._add_sub_label(disk_card, "Escritura: -- MB/s")

        self._perf_widgets["net_recv"] = self._add_sub_label(net_card, "Descarga: -- MB/s")
        self._perf_widgets["net_sent"] = self._add_sub_label(net_card, "Subida:   -- MB/s")

        # ── Tabla de procesos top ───────────────────────────────────────────
        proc_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        proc_card.grid(row=3, column=0, padx=20, pady=(4, 16), sticky="ew")
        proc_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            proc_card, text="🔝  Procesos con Mayor Consumo de CPU",
            font=("Segoe UI", 12, "bold"), text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(10, 6))

        self._perf_widgets["proc_frame"] = ctk.CTkFrame(proc_card, fg_color="transparent")
        self._perf_widgets["proc_frame"].pack(fill="x", padx=16, pady=(0, 12))
        self._perf_widgets["proc_labels"] = []
        for _ in range(5):
            lbl = ctk.CTkLabel(
                self._perf_widgets["proc_frame"],
                text="—",
                font=FONT_CODE,
                text_color=COLOR_MUTED,
                anchor="w",
            )
            lbl.pack(fill="x", pady=1)
            self._perf_widgets["proc_labels"].append(lbl)

    def _make_metric_card(self, parent, col: int, icon: str, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(title_row, text=f"{icon}  {title}",
                     font=("Segoe UI", 13, "bold"), text_color=COLOR_TEXT).pack(anchor="w")
        return card

    def _add_gauge(self, parent, label: str, color: str) -> ctk.CTkProgressBar:
        bar = ctk.CTkProgressBar(parent, progress_color=color, fg_color=COLOR_BORDER, height=14, corner_radius=6)
        bar.pack(fill="x", padx=16, pady=(0, 2))
        bar.set(0)
        return bar

    def _add_gauge_label(self, parent) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(parent, text="0%", font=("Segoe UI", 20, "bold"), text_color=COLOR_ACCENT)
        lbl.pack(anchor="w", padx=16, pady=(0, 4))
        return lbl

    def _add_sub_label(self, parent, text: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(parent, text=text, font=FONT_SMALL, text_color=COLOR_MUTED, anchor="w")
        lbl.pack(anchor="w", padx=16, pady=2)
        return lbl

    def _on_perf_update(self, snap: PerformanceSnapshot) -> None:
        """Callback llamado por PerformanceMonitor cada 2s. Actualiza widgets (thread-safe)."""
        def _update():
            if self._current_section != "monitor":
                return
            w = self._perf_widgets
            if not w:
                return
            try:
                # CPU
                cpu_pct = snap.cpu_percent
                color_cpu = COLOR_DANGER if cpu_pct > 80 else COLOR_WARNING if cpu_pct > 50 else COLOR_ACCENT
                w["cpu_bar"].set(cpu_pct / 100)
                w["cpu_bar"].configure(progress_color=color_cpu)
                w["cpu_label"].configure(text=f"{cpu_pct:.0f}%", text_color=color_cpu)
                freq_text = f"Frecuencia: {snap.cpu_freq_mhz:.0f} MHz" if snap.cpu_freq_mhz else "Frecuencia: --"
                w["cpu_freq"].configure(text=freq_text)
                w["cpu_cores"].configure(text=f"Nucleos logicos: {snap.cpu_cores_logical}")

                # RAM
                ram_pct = snap.ram_percent
                color_ram = COLOR_DANGER if ram_pct > 85 else COLOR_WARNING if ram_pct > 60 else COLOR_ACCENT2
                w["ram_bar"].set(ram_pct / 100)
                w["ram_bar"].configure(progress_color=color_ram)
                w["ram_label"].configure(text=f"{ram_pct:.0f}%", text_color=color_ram)
                w["ram_detail"].configure(text=f"{snap.ram_used_gb} / {snap.ram_total_gb} GB en uso")

                # Disco
                w["disk_read"].configure(text=f"Lectura:   {snap.disk_read_mbps:.2f} MB/s")
                w["disk_write"].configure(text=f"Escritura: {snap.disk_write_mbps:.2f} MB/s")

                # Red
                w["net_recv"].configure(text=f"Descarga: {snap.net_recv_mbps:.2f} MB/s")
                w["net_sent"].configure(text=f"Subida:   {snap.net_sent_mbps:.2f} MB/s")

                # Procesos
                for i, lbl in enumerate(w["proc_labels"]):
                    if i < len(snap.top_processes):
                        p = snap.top_processes[i]
                        name = p["name"][:28].ljust(28)
                        lbl.configure(
                            text=f"{i+1}. {name}  CPU: {p['cpu']:5.1f}%   RAM: {p['ram_mb']:6.1f} MB",
                            text_color=COLOR_TEXT,
                        )
                    else:
                        lbl.configure(text="—", text_color=COLOR_MUTED)
            except Exception:
                pass
        self.after(0, _update)

    # ─── PANEL DE ACTIVIDAD ───────────────────────────────────────────────────

    def _build_activity_section(self) -> None:
        frame = self._make_section_frame("activity")
        frame.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        hdr.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(12, 8))
        title_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_row, text="⚡ Panel de Optimizaciones",
            font=FONT_HEADING, text_color=COLOR_ACCENT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            title_row, text="🔄 Actualizar",
            font=FONT_SMALL, fg_color=COLOR_ACCENT2, hover_color="#2563eb",
            text_color=COLOR_TEXT, width=110, height=28,
            command=self._refresh_activity,
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            title_row, text="🗑 Limpiar sesión",
            font=FONT_SMALL, fg_color="#374151", hover_color="#4b5563",
            text_color=COLOR_TEXT, width=120, height=28,
            command=self._clear_activity,
        ).grid(row=0, column=2, padx=4)

        # ── Estadísticas rápidas ─────────────────────────────────────────────
        self._activity_stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._activity_stats_frame.grid(row=1, column=0, padx=20, pady=4, sticky="ew")
        self._activity_stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._activity_stat_cards: list[ctk.CTkLabel] = []
        for col, (icon, label) in enumerate([
            ("✅", "Exitosas"), ("❌", "Con error"), ("📂", "Categorías"), ("🕐", "Ultima optimiz.")
        ]):
            card = ctk.CTkFrame(self._activity_stats_frame, fg_color=COLOR_CARD, corner_radius=8)
            card.grid(row=0, column=col, padx=5, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 20)).pack(pady=(8, 2))
            val_lbl = ctk.CTkLabel(card, text="—", font=("Segoe UI", 16, "bold"), text_color=COLOR_TEXT)
            val_lbl.pack()
            ctk.CTkLabel(card, text=label, font=FONT_SMALL, text_color=COLOR_MUTED).pack(pady=(0, 8))
            self._activity_stat_cards.append(val_lbl)

        # ── Filtros ──────────────────────────────────────────────────────────
        filter_row = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=8)
        filter_row.grid(row=2, column=0, padx=20, pady=4, sticky="ew")

        ctk.CTkLabel(
            filter_row, text="Filtrar por categoría:",
            font=FONT_SMALL, text_color=COLOR_MUTED,
        ).pack(side="left", padx=(16, 8), pady=8)

        self._activity_filter = ctk.StringVar(value="Todas")
        self._activity_filter_menu = ctk.CTkOptionMenu(
            filter_row,
            variable=self._activity_filter,
            values=["Todas", "services", "registry", "power", "cleanup", "network", "visual"],
            font=FONT_SMALL,
            fg_color=COLOR_BORDER,
            button_color=COLOR_ACCENT2,
            text_color=COLOR_TEXT,
            width=160,
            command=lambda _: self._refresh_activity(),
        )
        self._activity_filter_menu.pack(side="left", padx=4, pady=8)

        self._activity_show_errors = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            filter_row, text="Solo errores",
            variable=self._activity_show_errors,
            font=FONT_SMALL, text_color=COLOR_MUTED,
            checkbox_width=18, checkbox_height=18,
            fg_color=COLOR_DANGER, hover_color="#dc2626",
            command=self._refresh_activity,
        ).pack(side="left", padx=16, pady=8)

        # ── Lista de actividad ───────────────────────────────────────────────
        self._activity_list_frame = ctk.CTkScrollableFrame(
            frame, fg_color=COLOR_BG, corner_radius=0,
            scrollbar_button_color="#4a5568",
            scrollbar_button_hover_color=COLOR_ACCENT,
            height=340,
        )
        self._activity_list_frame.grid(row=3, column=0, padx=20, pady=(4, 16), sticky="ew")
        self._activity_list_frame.grid_columnconfigure(0, weight=1)

        self._activity_placeholder = ctk.CTkLabel(
            self._activity_list_frame,
            text="No hay optimizaciones registradas en esta sesión.\n\n"
                 "Aplica optimizaciones con el botón '🚀 Aplicar Todo' para verlas aquí.",
            font=FONT_BODY, text_color=COLOR_MUTED,
            wraplength=500,
        )
        self._activity_placeholder.pack(pady=40)

    def _refresh_activity(self) -> None:
        """Reconstruye la lista de optimizaciones en el panel de actividad."""
        changes = self.tracker.get_session_changes()

        # Filtrar
        cat_filter = self._activity_filter.get() if hasattr(self, "_activity_filter") else "Todas"
        only_errors = self._activity_show_errors.get() if hasattr(self, "_activity_show_errors") else False

        filtered = changes
        if cat_filter != "Todas":
            filtered = [c for c in filtered if c.get("category", "") == cat_filter]
        if only_errors:
            filtered = [c for c in filtered if c.get("status") != "success"]

        # Estadísticas
        total_ok = sum(1 for c in changes if c.get("status") == "success")
        total_err = sum(1 for c in changes if c.get("status") != "success")
        cats = set(c.get("category", "?") for c in changes)
        last_ts = changes[-1]["timestamp"][:16].replace("T", " ") if changes else "—"

        if hasattr(self, "_activity_stat_cards") and len(self._activity_stat_cards) == 4:
            self._activity_stat_cards[0].configure(text=str(total_ok), text_color=COLOR_SUCCESS)
            self._activity_stat_cards[1].configure(text=str(total_err),
                                                    text_color=COLOR_DANGER if total_err else COLOR_MUTED)
            self._activity_stat_cards[2].configure(text=str(len(cats)), text_color=COLOR_ACCENT2)
            self._activity_stat_cards[3].configure(text=last_ts, text_color=COLOR_TEXT)

        # Limpiar lista
        if hasattr(self, "_activity_list_frame"):
            for w in self._activity_list_frame.winfo_children():
                w.destroy()

            if not filtered:
                msg = "No hay registros que coincidan con el filtro." if changes else (
                    "No hay optimizaciones registradas en esta sesión.\n\n"
                    "Aplica optimizaciones con el botón '🚀 Aplicar Todo' para verlas aquí."
                )
                ctk.CTkLabel(
                    self._activity_list_frame, text=msg,
                    font=FONT_BODY, text_color=COLOR_MUTED, wraplength=500,
                ).pack(pady=40)
                return

            CATEGORY_COLORS = {
                "services": COLOR_ACCENT2,
                "registry": COLOR_WARNING,
                "power": "#f97316",
                "cleanup": COLOR_SUCCESS,
                "network": "#a78bfa",
                "visual": "#ec4899",
            }

            for i, change in enumerate(reversed(filtered)):
                status = change.get("status", "success")
                is_ok = status == "success"
                ts = change.get("timestamp", "")[:19].replace("T", " ")
                cat = change.get("category", "?")
                desc = change.get("description", "")
                cat_color = CATEGORY_COLORS.get(cat, COLOR_ACCENT)
                border = COLOR_SUCCESS if is_ok else COLOR_DANGER

                row = ctk.CTkFrame(
                    self._activity_list_frame,
                    fg_color=COLOR_CARD, corner_radius=8,
                    border_width=1, border_color=border,
                )
                row.pack(fill="x", padx=4, pady=3)
                row.grid_columnconfigure(1, weight=1)

                # Icono estado
                icon = "✅" if is_ok else "❌"
                ctk.CTkLabel(
                    row, text=icon, font=("Segoe UI", 16), width=30,
                ).grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=8)

                # Descripción
                ctk.CTkLabel(
                    row, text=desc, font=FONT_BODY, text_color=COLOR_TEXT,
                    anchor="w", wraplength=500,
                ).grid(row=0, column=1, padx=4, pady=(8, 2), sticky="w")

                # Metadatos
                meta_row = ctk.CTkFrame(row, fg_color="transparent")
                meta_row.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")

                ctk.CTkLabel(
                    meta_row, text=f" {cat} ",
                    font=FONT_SMALL, text_color="#000",
                    fg_color=cat_color, corner_radius=4,
                ).pack(side="left", padx=(0, 6))

                ctk.CTkLabel(
                    meta_row, text=ts, font=FONT_SMALL, text_color=COLOR_MUTED,
                ).pack(side="left")

            # Re-enlazar mousewheel para children dinámicos
            if "activity" in self._section_frames:
                self.after(50, lambda: self._bind_mousewheel(self._section_frames["activity"]))

    def _clear_activity(self) -> None:
        """Limpia el historial de la sesión actual."""
        from tkinter import messagebox as _mb
        if not self.tracker.get_session_changes():
            _mb.showinfo("Sin cambios", "No hay cambios en la sesión actual.")
            return
        if _mb.askyesno("Limpiar sesión", "¿Borrar el historial de esta sesión?\n(Los logs en disco se mantienen)"):
            self.tracker.clear_session()
            self._refresh_activity()

    def _add_activity_entry(self, category: str, description: str, status: str = "success") -> None:
        """Registra una optimización en curso para el panel de actividad."""
        self.tracker.record(category, "optimize", description, status=status)
        if self._current_section == "activity":
            self.after(0, self._refresh_activity)

    def _build_log_section(self) -> None:
        frame = self._make_section_frame("log")

        header = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        header.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")

        ctk.CTkLabel(
            header, text="📋 Historial de Cambios",
            font=FONT_HEADING, text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="Registro de todas las optimizaciones aplicadas en esta sesión.",
            font=FONT_BODY, text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # Botón actualizar log
        ctk.CTkButton(
            header, text="🔄 Actualizar",
            font=FONT_BODY, fg_color=COLOR_ACCENT2,
            hover_color="#2563eb", text_color=COLOR_TEXT,
            width=120, height=30,
            command=self._refresh_log,
        ).pack(anchor="e", padx=16, pady=(0, 8))

        # Área de texto del log
        self._log_text = ctk.CTkTextbox(
            frame,
            font=FONT_CODE,
            fg_color="#0d1117",
            text_color=COLOR_TEXT,
            corner_radius=8,
            height=400,
        )
        self._log_text.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Directorio de logs
        log_dir_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=8)
        log_dir_frame.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="ew")

        backup_mgr = BackupManager()
        log_dir = str(backup_mgr.get_backup_dir().parent)
        ctk.CTkLabel(
            log_dir_frame,
            text=f"📁 Directorio de logs: {log_dir}",
            font=FONT_SMALL, text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=8)

    def _refresh_log(self) -> None:
        """Actualiza el área de texto del log con los cambios de la sesión."""
        changes = self.tracker.get_session_changes()
        self._log_text.delete("0.0", "end")

        if not changes:
            self._log_text.insert("0.0", "Sin cambios registrados en esta sesión.\n")
            return

        content = f"=== WinOptimizer Pro - Sesión {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n\n"
        for i, change in enumerate(changes, 1):
            ts = change.get("timestamp", "")[:19].replace("T", " ")
            status = "✅" if change.get("status") == "success" else "❌"
            content += f"{i:02d}. [{ts}] {status} {change.get('description', '')}\n"
            if change.get("revert_command"):
                content += f"     🔄 Revertir: {change['revert_command'][:80]}\n"
            content += "\n"

        self._log_text.insert("0.0", content)

    # ─── NAVEGACIÓN ───────────────────────────────────────────────────────────

    def _show_section(self, section_id: str) -> None:
        """Muestra la sección especificada y oculta las demás."""
        for s_id, frame in self._section_frames.items():
            frame.grid_remove()

        if section_id in self._section_frames:
            self._section_frames[section_id].grid()

        # Actualizar botones de navegación
        for btn_id, btn in self._nav_buttons.items():
            if btn_id == section_id:
                btn.configure(fg_color="#1f2937", text_color=COLOR_ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_MUTED)

        # Actualizar título del header
        titles = {
            "dashboard": "🏠  Dashboard",
            "monitor": "📊  Monitor de Rendimiento",
            "diagnostics": "🔍  Diagnóstico del Sistema",
            "activity": "⚡  Panel de Actividad",
            "services": "⚙️  Servicios",
            "registry": "🔧  Registro de Windows",
            "power": "⚡  Plan de Energía",
            "cleanup": "🧹  Limpieza del Sistema",
            "network": "🌐  Optimización de Red",
            "visual": "👁  Efectos Visuales",
            "log": "📋  Historial de Cambios",
            "ai": "🤖  Asistente IA",
        }
        self._section_title.configure(text=titles.get(section_id, section_id.title()))
        self._current_section = section_id

        # Arrancar monitor si se entra a esa sección, parar si se sale
        if section_id == "monitor":
            if not self._perf_monitor._running:
                self._perf_monitor.start()
        else:
            if section_id != "monitor":
                self._perf_monitor.stop()

        # Si va al log, actualizarlo
        if section_id == "log":
            self._refresh_log()

        # Si va a actividad, refrescar
        if section_id == "activity":
            self._refresh_activity()

    # ─── ACCIONES ─────────────────────────────────────────────────────────────

    def _is_checked(self, key: str) -> bool:
        cb = self._checkboxes.get(key)
        if cb:
            return cb.get() == 1
        return False

    def _update_progress(self, message: str, percentage: int) -> None:
        """Actualiza la barra de progreso y el mensaje de estado (thread-safe)."""
        def _update():
            self._status_var.set(message)
            self._progress_var.set(percentage / 100)
        self.after(0, _update)

    def _set_buttons_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._apply_btn.configure(state=state)

    def _create_backup_thread(self) -> None:
        """Crea un punto de restauración en un hilo separado."""
        if self._optimization_running:
            return
        self._optimization_running = True
        self._set_buttons_state(False)
        threading.Thread(target=self._create_backup_task, daemon=True).start()

    def _create_backup_task(self) -> None:
        self._update_progress("Creando punto de restauración...", 0)
        backup_mgr = BackupManager(progress_callback=self._update_progress)
        ok = backup_mgr.create_restore_point("WinOptimizer - Antes de optimizar")

        # Respaldar claves de registro
        reg_keys = self.reg_opt.get_registry_keys_for_backup()
        self._backup_data = backup_mgr.backup_registry_keys(reg_keys)

        if ok:
            self._backup_created = True
            self.after(0, lambda: messagebox.showinfo(
                "Backup creado",
                "✅ Punto de restauración del sistema creado exitosamente.\n\n"
                "Ya puedes aplicar las optimizaciones de forma segura.",
            ))
        else:
            self.after(0, lambda: messagebox.showwarning(
                "Advertencia",
                "⚠️ No se pudo crear el punto de restauración.\n"
                "Esto puede deberse a que ya existe uno reciente (< 24h).\n\n"
                "Puedes continuar, pero se recomienda proceder con precaución.",
            ))

        self._update_progress("Backup completado.", 100)
        self._optimization_running = False
        self.after(0, lambda: self._set_buttons_state(True))

    def _apply_all_thread(self) -> None:
        """Aplica todas las optimizaciones seleccionadas en un hilo separado."""
        if self._optimization_running:
            return

        # Verificar backup
        if not self._backup_created:
            confirm = messagebox.askyesno(
                "Sin backup",
                "⚠️ No has creado un punto de restauración.\n\n"
                "¿Deseas continuar sin él?\n"
                "(No recomendado - primero haz clic en '🛡 Crear Backup')",
            )
            if not confirm:
                return

        # Confirmar
        confirm = messagebox.askyesno(
            "Confirmar optimización",
            "¿Aplicar todas las optimizaciones seleccionadas?\n\n"
            "• Los cambios en registro requieren reiniciar para tomar efecto completo.\n"
            "• Los servicios se deshabilitarán inmediatamente.\n"
            "• Puedes revertir los cambios desde el botón '↩ Revertir'.",
        )
        if not confirm:
            return

        self._optimization_running = True
        self._set_buttons_state(False)
        threading.Thread(target=self._apply_all_task, daemon=True).start()

    def _apply_all_task(self) -> None:
        """Tarea de aplicación de optimizaciones (ejecuta en hilo separado)."""
        total_ok = 0
        total_fail = 0
        is_win11 = self.system_info.get("is_win11", False)

        try:
            # 1. Servicios
            selected_svcs = [
                key.replace("svc_", "")
                for key, cb in self._checkboxes.items()
                if key.startswith("svc_") and cb.get() == 1
            ]
            if selected_svcs:
                self._update_progress("Optimizando servicios...", 10)
                ok, fail = self.svc_opt.optimize_all(selected_svcs, is_win11)
                total_ok += ok
                total_fail += fail

            # 2. Registro
            selected_regs = [
                key.replace("reg_", "")
                for key, cb in self._checkboxes.items()
                if key.startswith("reg_") and cb.get() == 1
            ]
            if selected_regs:
                self._update_progress("Aplicando tweaks del registro...", 30)
                ok, fail = self.reg_opt.apply_all(selected_regs)
                total_ok += ok
                total_fail += fail

            # 3. Energía
            self._update_progress("Configurando plan de energía...", 45)
            if self._is_checked("pwr_ultimate"):
                ok = self.pwr_opt.enable_ultimate_performance() if not self.is_laptop else \
                     self.pwr_opt.optimize_all(is_laptop=True)[0] > 0
                total_ok += 1 if ok else 0
                total_fail += 0 if ok else 1

            if self._is_checked("pwr_processor") and not self.is_laptop:
                ok = self.pwr_opt.set_processor_state(100, 100)
                total_ok += 1 if ok else 0

            if self._is_checked("pwr_hibernation") and not self.is_laptop:
                ok = self.pwr_opt.disable_hibernation()
                total_ok += 1 if ok else 0

            # 4. Limpieza
            self._update_progress("Limpiando sistema...", 60)
            run_dism = self._is_checked("clean_dism")
            clean_logs = self._is_checked("clean_event_logs")

            if self._is_checked("clean_user_temp"):
                ok, _ = self.clean_opt.clean_user_temp()
                total_ok += 1 if ok else 0

            if self._is_checked("clean_system_temp"):
                ok, _ = self.clean_opt.clean_system_temp()
                total_ok += 1 if ok else 0

            if self._is_checked("clean_recycle_bin"):
                ok, _ = self.clean_opt.clean_recycle_bin()
                total_ok += 1 if ok else 0

            if self._is_checked("clean_wu_cache"):
                ok, _ = self.clean_opt.clean_windows_update_cache()
                total_ok += 1 if ok else 0

            if self._is_checked("clean_trim"):
                ok = self.clean_opt.enable_trim() or self.clean_opt.check_trim_status()
                total_ok += 1 if ok else 0

            if run_dism:
                ok, _ = self.clean_opt.run_dism_cleanup()
                total_ok += 1 if ok else 0

            if clean_logs:
                ok = self.clean_opt.clean_event_logs()
                total_ok += 1 if ok else 0

            # 5. Red
            self._update_progress("Optimizando red...", 78)
            if self._is_checked("net_nagle"):
                ok = self.net_opt.disable_nagle_algorithm()
                total_ok += 1 if ok else 0

            if self._is_checked("net_tcp"):
                ok = self.net_opt.optimize_tcp_settings()
                total_ok += 1 if ok else 0

            if self._is_checked("net_throttling"):
                ok = self.net_opt.disable_network_throttling()
                total_ok += 1 if ok else 0

            if self._is_checked("net_dns"):
                ok = self.net_opt.flush_dns()
                total_ok += 1 if ok else 0

            # 6. Visual
            self._update_progress("Optimizando efectos visuales...", 90)
            if self._is_checked("vis_performance"):
                ok = self.vis_opt.set_performance_mode()
                total_ok += 1 if ok else 0

            if self._is_checked("vis_animations"):
                ok = self.vis_opt.disable_window_animations()
                total_ok += 1 if ok else 0

            if self._is_checked("vis_transparency"):
                ok = self.vis_opt.disable_transparency()
                total_ok += 1 if ok else 0

            if self._is_checked("vis_aero_shake"):
                ok = self.vis_opt.disable_aero_shake()
                total_ok += 1 if ok else 0

            self._update_progress(
                f"✅ Optimización completada: {total_ok} éxitos, {total_fail} fallos.", 100
            )

        except Exception as e:
            logger.error(f"Error crítico durante optimización: {e}", exc_info=True)
            self._update_progress(f"❌ Error: {e}", 0)
            total_fail += 1

        finally:
            self._optimization_running = False
            self.after(0, lambda: self._set_buttons_state(True))
            # Refrescar panel de actividad automáticamente
            self.after(100, self._refresh_activity)

        # Mostrar resultado
        self.after(0, lambda: messagebox.showinfo(
            "Optimización completada",
            f"✅ Optimización finalizada\n\n"
            f"• Exitosas: {total_ok}\n"
            f"• Con errores: {total_fail}\n\n"
            f"🔄 Se recomienda REINICIAR el equipo para que todos los cambios "
            f"tomen efecto completamente.\n\n"
            f"📋 Ve a la sección 'Registro de Cambios' para ver el detalle.",
        ))

    def _revert_changes_thread(self) -> None:
        """Revierte los cambios aplicados."""
        if self._optimization_running:
            return

        revertible = self.tracker.get_revertible_changes()
        if not revertible:
            messagebox.showinfo("Sin cambios", "No hay cambios para revertir en esta sesión.")
            return

        confirm = messagebox.askyesno(
            "Confirmar reversión",
            f"¿Revertir los {len(revertible)} cambios de esta sesión?\n\n"
            "Esto restaurará la configuración anterior.\n"
            "⚠️ Los servicios deshabilitados se volverán a habilitar en modo Manual.",
        )
        if not confirm:
            return

        self._optimization_running = True
        self._set_buttons_state(False)
        threading.Thread(target=self._revert_task, daemon=True).start()

    def _revert_task(self) -> None:
        """Ejecuta la reversión de cambios."""
        self._update_progress("Revirtiendo cambios...", 0)
        ok_count = 0
        fail_count = 0

        changes = self.tracker.get_revertible_changes()
        total = len(changes)

        from optimizer.core import PowerShellRunner
        ps = PowerShellRunner()

        for i, change in enumerate(changes):
            pct = int(((i + 1) / total) * 100)
            self._update_progress(f"Revirtiendo: {change['description'][:50]}...", pct)

            revert_cmd = change.get("revert_command")
            if revert_cmd:
                ok, _, _ = ps.run(revert_cmd)
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1
                    logger.warning(f"Error revirtiendo: {change['description']}")

        # Revertir tweaks del registro usando los datos de respaldo
        if self._backup_data:
            backup_mgr = BackupManager()
            r_ok, r_fail = backup_mgr.restore_registry_from_backup(self._backup_data)
            ok_count += r_ok
            fail_count += r_fail

        self._update_progress(
            f"↩️ Reversión completada: {ok_count} éxitos, {fail_count} fallos.", 100
        )
        self._optimization_running = False
        self.after(0, lambda: self._set_buttons_state(True))

        self.after(0, lambda: messagebox.showinfo(
            "Reversión completada",
            f"↩️ Cambios revertidos\n\n"
            f"• Exitosos: {ok_count}\n"
            f"• Con errores: {fail_count}\n\n"
            "Se recomienda reiniciar el equipo.",
        ))


    # ─── SECCIÓN DIAGNÓSTICO ─────────────────────────────────────────────────

    def _build_diagnostics_section(self) -> None:
        frame = self._make_section_frame("diagnostics")
        frame.grid_columnconfigure(0, weight=1)

        # Header card
        header_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        header_card.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        header_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_card,
            text="🔍 Diagnóstico del Sistema",
            font=FONT_HEADING,
            text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(
            header_card,
            text="Analiza 7 áreas clave de tu PC y genera un reporte completo.",
            font=FONT_BODY,
            text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._diag_run_btn = ctk.CTkButton(
            header_card,
            text="▶  Ejecutar Diagnóstico Completo",
            font=("Segoe UI", 12, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color="#00b894",
            text_color="#000000",
            height=40,
            command=self._run_diagnostics_thread,
        )
        self._diag_run_btn.pack(anchor="w", padx=16, pady=(0, 12))

        # Tarjeta de tareas
        tasks_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        tasks_card.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        tasks_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tasks_card,
            text="Tareas de diagnóstico",
            font=FONT_HEADING,
            text_color=COLOR_TEXT,
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self._diag_tasks = [
            ("cmd1", "CMD 1: Diagnóstico de servicios críticos de Windows"),
            ("cmd2", "CMD 2: Uso de recursos actuales (CPU, RAM, Disco)"),
            ("cmd3", "CMD 3: Top procesos por CPU y RAM"),
            ("cmd4", "CMD 4: Programas en inicio automático"),
            ("cmd5", "CMD 5: Errores críticos en Event Viewer (últimas 24 h)"),
            ("cmd6", "CMD 6: Estado del disco (SMART y sistema de archivos)"),
            ("cmd7", "CMD 7: Drivers problemáticos y actualizaciones"),
        ]

        self._diag_status_labels: dict[str, ctk.CTkLabel] = {}
        self._diag_row_frames: dict[str, ctk.CTkFrame] = {}

        for task_id, task_name in self._diag_tasks:
            row = ctk.CTkFrame(tasks_card, fg_color="#1e2a3a", corner_radius=6)
            row.pack(fill="x", padx=12, pady=3)
            row.grid_columnconfigure(1, weight=1)

            status_lbl = ctk.CTkLabel(
                row,
                text="◻",
                font=("Segoe UI", 14),
                text_color=COLOR_MUTED,
                width=30,
            )
            status_lbl.grid(row=0, column=0, padx=(12, 4), pady=8)

            ctk.CTkLabel(
                row,
                text=task_name,
                font=FONT_BODY,
                text_color=COLOR_TEXT,
                anchor="w",
            ).grid(row=0, column=1, padx=4, pady=8, sticky="ew")

            self._diag_status_labels[task_id] = status_lbl
            self._diag_row_frames[task_id] = row

        ctk.CTkFrame(tasks_card, height=1, fg_color="transparent").pack(pady=4)

        # Tarjeta de resultados
        results_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        results_card.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="ew")
        results_card.grid_columnconfigure(0, weight=1)

        res_header = ctk.CTkFrame(results_card, fg_color="transparent")
        res_header.pack(fill="x", padx=16, pady=(12, 4))
        res_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            res_header,
            text="📋 Resultados en tiempo real",
            font=FONT_HEADING,
            text_color=COLOR_TEXT,
        ).grid(row=0, column=0, sticky="w")

        self._diag_report_btn = ctk.CTkButton(
            res_header,
            text="📄 Ver Reporte Completo",
            font=FONT_SMALL,
            fg_color=COLOR_ACCENT2,
            hover_color="#2563eb",
            text_color=COLOR_TEXT,
            height=30,
            width=190,
            state="disabled",
            command=self._show_diag_report_window,
        )
        self._diag_report_btn.grid(row=0, column=1, sticky="e")

        self._diag_result_text = ctk.CTkTextbox(
            results_card,
            font=FONT_CODE,
            fg_color="#0d1117",
            text_color=COLOR_TEXT,
            height=300,
            wrap="none",
        )
        self._diag_result_text.pack(fill="x", padx=16, pady=(4, 16))
        self._diag_result_text.configure(state="disabled")

        self._diag_running = False
        self._diag_results_data: dict[str, str] = {}

    def _run_diagnostics_thread(self) -> None:
        if self._diag_running:
            return
        threading.Thread(target=self._run_diagnostics_task, daemon=True).start()

    def _run_diagnostics_task(self) -> None:
        from optimizer.core import PowerShellRunner
        self._diag_running = True
        self._diag_results_data = {}

        self.after(0, lambda: self._diag_run_btn.configure(
            state="disabled", text="⏳  Ejecutando diagnóstico..."
        ))
        self.after(0, lambda: self._diag_report_btn.configure(state="disabled"))
        self.after(0, self._diag_clear_results)

        for task_id, _ in self._diag_tasks:
            self.after(0, lambda t=task_id: self._diag_set_status(t, "pending"))

        ps = PowerShellRunner()

        DIAG_COMMANDS: list[tuple[str, str, str]] = [
            (
                "cmd1",
                "Servicios críticos de Windows detenidos",
                r"Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -ne 'Running'} | Select-Object Name, DisplayName, Status | Format-Table -AutoSize | Out-String -Width 120",
            ),
            (
                "cmd2",
                "Uso de recursos actuales (CPU, RAM, Disco)",
                r"""$cpu = [math]::Round((Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average, 1); $os = Get-WmiObject Win32_OperatingSystem; $ramUsed = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 2); $ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2); $ramPct = [math]::Round($ramUsed / $ramTotal * 100, 1); Write-Host "--- CPU ---"; Write-Host "Uso actual: $cpu %"; Write-Host ""; Write-Host "--- RAM ---"; Write-Host "En uso: $ramUsed GB / $ramTotal GB  ($ramPct %)"; Write-Host ""; Write-Host "--- DISCOS ---"; Get-WmiObject Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, @{N='Total(GB)';E={[math]::Round($_.Size/1GB,1)}}, @{N='Libre(GB)';E={[math]::Round($_.FreeSpace/1GB,1)}}, @{N='Usado%';E={[math]::Round((($_.Size-$_.FreeSpace)/$_.Size)*100,1)}} | Format-Table -AutoSize | Out-String -Width 120""",
            ),
            (
                "cmd3",
                "Top procesos por CPU y RAM",
                r"Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Name, @{N='CPU(s)';E={[math]::Round($_.CPU,1)}}, @{N='RAM(MB)';E={[math]::Round($_.WorkingSet/1MB,1)}} | Format-Table -AutoSize | Out-String -Width 120",
            ),
            (
                "cmd4",
                "Programas en inicio automático",
                r"Get-CimInstance Win32_StartupCommand | Select-Object Name, Location, User | Format-Table -AutoSize -Wrap | Out-String -Width 120",
            ),
            (
                "cmd5",
                "Errores críticos en Event Viewer (últimas 24 h)",
                r"try { $s = (Get-Date).AddHours(-24); Get-EventLog -LogName System -EntryType Error -After $s -Newest 20 -ErrorAction Stop | Select-Object TimeGenerated, Source, @{N='Mensaje';E={$_.Message.Substring(0,[Math]::Min(80,$_.Message.Length))}} | Format-Table -AutoSize -Wrap | Out-String -Width 120 } catch { Write-Host 'Sin errores criticos en las ultimas 24 horas (o acceso denegado).' }",
            ),
            (
                "cmd6",
                "Estado del disco (SMART y sistema de archivos)",
                r"Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus, @{N='Tamanio(GB)';E={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize | Out-String -Width 120",
            ),
            (
                "cmd7",
                "Drivers no firmados / problemáticos",
                r"$drivers = Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceName -ne $null -and $_.IsSigned -ne $true }; if ($drivers) { $drivers | Select-Object DeviceName, DriverVersion, IsSigned | Select-Object -First 20 | Format-Table -AutoSize | Out-String -Width 120 } else { Write-Host 'Todos los drivers instalados estan firmados correctamente.' }",
            ),
        ]

        for task_id, label, cmd in DIAG_COMMANDS:
            self.after(0, lambda t=task_id: self._diag_set_status(t, "running"))
            sep = "=" * 60
            self.after(0, lambda l=label, s=sep: self._diag_append_result(
                f"\n{s}\n  {l}\n{s}\n"
            ))

            ok, out, err = ps.run(cmd, timeout=60)
            result = out if out.strip() else (err.strip() if err.strip() else "(sin resultados)")
            self._diag_results_data[task_id] = result

            self.after(0, lambda r=result: self._diag_append_result(r + "\n"))
            self.after(0, lambda t=task_id, s=ok: self._diag_set_status(t, "done" if s else "error"))

        self._diag_running = False
        self.after(0, lambda: self._diag_run_btn.configure(
            state="normal", text="▶  Ejecutar Diagnóstico Completo"
        ))
        self.after(0, lambda: self._diag_report_btn.configure(state="normal"))

    def _diag_set_status(self, task_id: str, status: str) -> None:
        lbl = self._diag_status_labels.get(task_id)
        row = self._diag_row_frames.get(task_id)
        if not lbl:
            return
        if status == "pending":
            lbl.configure(text="◻", text_color=COLOR_MUTED)
            if row:
                row.configure(fg_color="#1e2a3a")
        elif status == "running":
            lbl.configure(text="◼", text_color=COLOR_WARNING)
            if row:
                row.configure(fg_color="#2d2a1a")
        elif status == "done":
            lbl.configure(text="✔", text_color=COLOR_SUCCESS)
            if row:
                row.configure(fg_color="#1a2d1a")
        elif status == "error":
            lbl.configure(text="✗", text_color=COLOR_DANGER)
            if row:
                row.configure(fg_color="#2d1a1a")

    def _diag_clear_results(self) -> None:
        self._diag_result_text.configure(state="normal")
        self._diag_result_text.delete("1.0", "end")
        self._diag_result_text.configure(state="disabled")

    def _diag_append_result(self, text: str) -> None:
        self._diag_result_text.configure(state="normal")
        self._diag_result_text.insert("end", text)
        self._diag_result_text.see("end")
        self._diag_result_text.configure(state="disabled")

    def _show_diag_report_window(self) -> None:
        """Abre ventana de reporte completo en el escritorio."""
        win = ctk.CTkToplevel(self)
        win.title("📋 Reporte de Diagnóstico — WinOptimizer Pro")
        win.geometry("960x720")
        win.configure(fg_color=COLOR_BG)
        win.grab_set()

        win.update_idletasks()
        x = (win.winfo_screenwidth() - 960) // 2
        y = (win.winfo_screenheight() - 720) // 2
        win.geometry(f"+{x}+{y}")

        # Header
        header = ctk.CTkFrame(win, fg_color="#111827", height=64, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🔍 Reporte de Diagnóstico del Sistema",
            font=FONT_HEADING,
            text_color=COLOR_ACCENT,
        ).pack(side="left", padx=24, pady=16)

        ctk.CTkLabel(
            header,
            text=datetime.now().strftime("Generado: %d/%m/%Y  %H:%M"),
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
        ).pack(side="right", padx=24)

        # Resumen de tareas (indicadores)
        summary_frame = ctk.CTkFrame(win, fg_color=COLOR_CARD, corner_radius=0)
        summary_frame.pack(fill="x", padx=0, pady=0)

        inner = ctk.CTkFrame(summary_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        for task_id, task_name in self._diag_tasks:
            lbl = self._diag_status_labels.get(task_id)
            icon = lbl.cget("text") if lbl else "◻"
            color = lbl.cget("text_color") if lbl else COLOR_MUTED
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=icon, font=("Segoe UI", 11), text_color=color, width=22).pack(side="left")
            ctk.CTkLabel(row, text=task_name, font=FONT_SMALL, text_color=COLOR_TEXT).pack(side="left", padx=4)

        # Contenido del reporte
        self._diag_result_text.configure(state="normal")
        content = self._diag_result_text.get("1.0", "end")
        self._diag_result_text.configure(state="disabled")

        full_text = (
            f"REPORTE DE DIAGNÓSTICO — WinOptimizer Pro\n"
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"{'=' * 80}\n\n" + content
        )

        text_box = ctk.CTkTextbox(
            win,
            font=FONT_CODE,
            fg_color="#0d1117",
            text_color=COLOR_TEXT,
            wrap="none",
        )
        text_box.pack(fill="both", expand=True, padx=16, pady=8)
        text_box.insert("1.0", full_text)
        text_box.configure(state="disabled")

        # Botones
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            btn_frame,
            text="💾 Guardar como .txt en Escritorio",
            font=FONT_BODY,
            fg_color=COLOR_ACCENT2,
            hover_color="#2563eb",
            text_color=COLOR_TEXT,
            height=36,
            command=lambda: self._save_diag_report(full_text),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="✕ Cerrar",
            font=FONT_BODY,
            fg_color="#374151",
            hover_color="#4b5563",
            text_color=COLOR_TEXT,
            height=36,
            command=win.destroy,
        ).pack(side="right", padx=4)

    def _save_diag_report(self, content: str) -> None:
        """Guarda el reporte de diagnóstico como archivo .txt."""
        import tkinter.filedialog as fd
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"WinOptimizer_Diagnostico_{timestamp}.txt"
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filepath = fd.asksaveasfilename(
            initialdir=desktop,
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
            title="Guardar reporte de diagnóstico",
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo(
                "Reporte guardado",
                f"✅ Reporte guardado correctamente en:\n{filepath}",
            )

    # ─── SECCIÓN ASISTENTE IA ────────────────────────────────────────────────

    def _build_ai_section(self) -> None:
        frame = self._make_section_frame("ai")
        frame.grid_columnconfigure(0, weight=1)

        # Card de configuración API
        api_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        api_card.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        api_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            api_card, text="🤖 Asistente IA — Powered by OpenRouter",
            font=FONT_HEADING, text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(
            api_card,
            text="Analiza tu sistema, recomienda optimizaciones y responde preguntas técnicas.",
            font=FONT_BODY, text_color=COLOR_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        key_row = ctk.CTkFrame(api_card, fg_color="transparent")
        key_row.pack(fill="x", padx=16, pady=(0, 12))
        key_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            key_row, text="API Key:", font=FONT_BODY, text_color=COLOR_TEXT, width=70,
        ).grid(row=0, column=0, padx=(0, 8))

        self._api_key_var = ctk.StringVar(value=self.ai_assistant._api_key)
        ctk.CTkEntry(
            key_row, textvariable=self._api_key_var, show="*",
            font=FONT_BODY, fg_color="#0d1117", text_color=COLOR_TEXT,
            border_color=COLOR_BORDER, placeholder_text="sk-or-v1-...",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            key_row, text="Guardar", font=FONT_SMALL,
            fg_color=COLOR_ACCENT2, hover_color="#2563eb", text_color=COLOR_TEXT,
            width=80, height=32, command=self._save_ai_key,
        ).grid(row=0, column=2)

        # Botones de acceso rápido
        presets_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        presets_card.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        presets_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            presets_card, text="Preguntas rápidas:", font=FONT_SMALL, text_color=COLOR_MUTED,
        ).grid(row=0, column=0, columnspan=2, padx=16, pady=(10, 6), sticky="w")

        presets = [
            ("🔍 Analizar mi sistema",
             "Analiza mi sistema y dime cuáles son las optimizaciones más importantes para mi configuración. Dame un plan de acción priorizado de mayor a menor impacto."),
            ("⚡ ¿Qué optimizar primero?",
             "¿Cuáles son las 3 optimizaciones más impactantes que debo aplicar primero en este sistema? Explica el beneficio concreto de cada una."),
            ("🎮 Optimizar para gaming",
             "¿Cómo optimizo este sistema específicamente para gaming? ¿Qué tweaks tienen mayor impacto en FPS y latencia con mi hardware?"),
            ("🛡 ¿Es seguro aplicar todo?",
             "¿Es seguro aplicar todas las optimizaciones disponibles en mi sistema? ¿Hay alguna que deba evitar con mi configuración?"),
        ]

        for i, (label, prompt) in enumerate(presets):
            ctk.CTkButton(
                presets_card, text=label, font=FONT_SMALL,
                fg_color="#1f2937", hover_color="#374151",
                text_color=COLOR_TEXT, border_width=1, border_color=COLOR_BORDER,
                height=34, corner_radius=6,
                command=lambda p=prompt: self._send_ai_message(p),
            ).grid(row=1 + i // 2, column=i % 2, padx=8, pady=4, sticky="ew")

        ctk.CTkLabel(presets_card, text="").grid(row=3, padx=0, pady=2)

        # Área de chat
        self._ai_chat = ctk.CTkTextbox(
            frame, font=("Consolas", 10),
            fg_color="#0d1117", text_color=COLOR_TEXT,
            corner_radius=8, state="disabled",
            height=360,
        )
        self._ai_chat.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="ew")

        self._ai_chat.configure(state="normal")
        self._ai_chat.insert("0.0", "Bienvenido al Asistente IA de WinOptimizer Pro.\n"
                             "Usa los botones rapidos o escribe tu pregunta abajo.\n"
                             + "─" * 60 + "\n")
        self._ai_chat.configure(state="disabled")

        # Fila de input
        input_card = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=8)
        input_card.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="ew")
        input_card.grid_columnconfigure(0, weight=1)

        self._ai_input = ctk.CTkEntry(
            input_card, font=FONT_BODY,
            fg_color="#0d1117", text_color=COLOR_TEXT,
            border_color=COLOR_BORDER, placeholder_text="Escribe tu pregunta aqui...",
            height=40,
        )
        self._ai_input.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="ew")
        self._ai_input.bind("<Return>", lambda e: self._send_ai_message())

        self._ai_send_btn = ctk.CTkButton(
            input_card, text="Enviar",
            font=("Segoe UI", 11, "bold"),
            fg_color=COLOR_ACCENT, hover_color="#00b894",
            text_color="#000000", width=100, height=40,
            command=self._send_ai_message,
        )
        self._ai_send_btn.grid(row=0, column=1, padx=(0, 8), pady=10)

        ctk.CTkButton(
            input_card, text="Limpiar", font=FONT_SMALL,
            fg_color="transparent", hover_color="#1f2937",
            text_color=COLOR_MUTED, width=72, height=40,
            command=self._clear_ai_chat,
        ).grid(row=0, column=2, padx=(0, 12), pady=10)

    def _save_ai_key(self) -> None:
        key = self._api_key_var.get().strip()
        if key:
            self.ai_assistant.save_api_key(key)
            messagebox.showinfo("Guardado", "API key de OpenRouter guardada correctamente.")
        else:
            messagebox.showwarning("Sin clave", "Ingresa una API key valida.")

    def _build_ai_context(self) -> str:
        info = self.system_info
        selected = [k for k, cb in self._checkboxes.items() if cb.get() == 1]
        return (
            f"SO: {info.get('product_name', 'Windows')} (Build {info.get('build', '?')})\n"
            f"RAM: {info.get('ram_gb', '?')} GB | "
            f"SSD: {'Si' if info.get('has_ssd') else 'No (HDD)'} | "
            f"NVMe: {'Si' if info.get('has_nvme') else 'No'} | "
            f"Laptop: {'Si' if self.is_laptop else 'No (Desktop)'} | "
            f"Windows 11: {'Si' if info.get('is_win11') else 'No'}\n"
            f"Optimizaciones seleccionadas: {len(selected)} de {len(self._checkboxes)}\n"
            f"IDs seleccionados: {', '.join(selected[:20]) if selected else 'ninguno'}"
        )

    def _append_ai_chat(self, role: str, text: str) -> None:
        self._ai_chat.configure(state="normal")
        if role == "user":
            self._ai_chat.insert("end", f"\nTu: {text}\n")
        else:
            self._ai_chat.insert("end", f"\nAsistente IA:\n{text}\n{'─' * 60}\n")
        self._ai_chat.see("end")
        self._ai_chat.configure(state="disabled")

    def _send_ai_message(self, preset_text: str = "") -> None:
        msg = preset_text or (self._ai_input.get().strip() if hasattr(self, "_ai_input") else "")
        if not msg:
            return
        if not preset_text and hasattr(self, "_ai_input"):
            self._ai_input.delete(0, "end")

        self._append_ai_chat("user", msg)
        self._ai_send_btn.configure(state="disabled", text="Pensando...")
        context = self._build_ai_context()

        def _task():
            ok, response = self.ai_assistant.ask(msg, context)
            self.after(0, lambda: self._append_ai_chat("assistant", response))
            self.after(0, lambda: self._ai_send_btn.configure(state="normal", text="Enviar"))

        threading.Thread(target=_task, daemon=True).start()

    def _clear_ai_chat(self) -> None:
        self.ai_assistant.clear_conversation()
        self._ai_chat.configure(state="normal")
        self._ai_chat.delete("0.0", "end")
        self._ai_chat.insert("0.0", "Chat limpiado. Inicia una nueva conversacion.\n" + "─" * 60 + "\n")
        self._ai_chat.configure(state="disabled")

    # ─── SaaS Integration ────────────────────────────────────────────────────

    def _saas_login(self) -> None:
        """Autentica con el SaaS y obtiene el token JWT."""
        import requests as _req
        email = self._saas_email_var.get().strip()
        password = self._saas_pass_var.get().strip()
        if not email or not password:
            messagebox.showwarning("Faltan datos", "Ingresa tu email y contraseña.")
            return

        self._saas_connect_btn.configure(state="disabled", text="Conectando...")
        self._saas_status_lbl.configure(text="Conectando...", text_color=COLOR_MUTED)

        def _task():
            try:
                resp = _req.post(
                    "https://win-optimizer-saas.vercel.app/api/auth/login",
                    json={"email": email, "password": password},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._saas_token = data["access_token"]
                    self._saas_email = data["user"]["email"]
                    self._saas_agent = SupabaseAgent(
                        user_token=self._saas_token,
                        device_name=self.system_info.get("product_name", "PC"),
                    )
                    self.after(0, lambda: self._saas_status_lbl.configure(
                        text=f"Conectado como: {self._saas_email}", text_color=COLOR_SUCCESS))
                    self.after(0, lambda: self._saas_diag_btn.configure(state="normal"))
                    self.after(0, lambda: self._saas_connect_btn.configure(
                        state="normal", text="Reconectar"))
                else:
                    msg = resp.json().get("error", "Error desconocido")
                    self.after(0, lambda: self._saas_status_lbl.configure(
                        text=f"Error: {msg}", text_color=COLOR_DANGER))
                    self.after(0, lambda: self._saas_connect_btn.configure(
                        state="normal", text="Conectar"))
            except Exception as e:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text=f"Sin conexión: {e}", text_color=COLOR_DANGER))
                self.after(0, lambda: self._saas_connect_btn.configure(
                    state="normal", text="Conectar"))

        threading.Thread(target=_task, daemon=True).start()

    def _saas_diagnose(self) -> None:
        """Envía métricas al SaaS y muestra el plan de diagnóstico IA."""
        if not self._saas_agent:
            return

        self._saas_diag_btn.configure(state="disabled", text="Analizando...")
        self._saas_status_lbl.configure(
            text="Recolectando métricas y enviando diagnóstico...", text_color=COLOR_MUTED)

        def _task():
            try:
                result = self._saas_agent.run_diagnostic()
            except SessionExpiredError:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text="Sesión expirada — vuelve a conectarte.", text_color=COLOR_DANGER))
                self.after(0, lambda: self._saas_diag_btn.configure(
                    state="disabled", text="Enviar Diagnóstico IA"))
                self.after(0, lambda: self._saas_connect_btn.configure(
                    state="normal", text="Reconectar"))
                return
            except InsufficientCreditsError:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text="Sin créditos. Recarga en win-optimizer-saas.vercel.app", text_color=COLOR_DANGER))
                self.after(0, lambda: self._saas_diag_btn.configure(
                    state="normal", text="Enviar Diagnóstico IA"))
                return
            if not result:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text="Error de conexión. Verifica tu internet.", text_color=COLOR_DANGER))
                self.after(0, lambda: self._saas_diag_btn.configure(
                    state="normal", text="Enviar Diagnóstico IA"))
                return

            plan = result["plan"]
            log_id = result["log_id"]
            summary = plan.get("summary", "")
            score = plan.get("score", "?")
            steps = plan.get("steps", [])

            # Guardar log_id para sincronización posterior
            self._saas_last_log_id = log_id

            lines = [
                f"DIAGNÓSTICO IA — Score: {score}/100",
                f"Resumen: {summary}",
                "─" * 50,
            ]
            for i, step in enumerate(steps, 1):
                lines.append(
                    f"Paso {i}: {step.get('action', '')} "
                    f"[Riesgo: {step.get('risk_level', '?').upper()}]"
                )
                lines.append(f"  {step.get('justification', '')}")
                if step.get("command"):
                    lines.append(f"  CMD: {step['command']}")
            lines.append("─" * 50)
            lines.append("Aplica las optimizaciones y luego usa 'Sincronizar Trabajos'.")
            msg = "\n".join(lines)

            self.after(0, lambda: self._saas_status_lbl.configure(
                text=f"Diagnóstico completado — Score: {score}/100", text_color=COLOR_SUCCESS))
            self.after(0, lambda: self._saas_diag_btn.configure(
                state="normal", text="Enviar Diagnóstico IA"))
            self.after(0, lambda: self._saas_sync_btn.configure(state="normal"))
            self.after(0, lambda: messagebox.showinfo("Diagnóstico IA", msg))

        threading.Thread(target=_task, daemon=True).start()

    def _saas_sync_jobs(self) -> None:
        """Sincroniza los trabajos realizados en la sesión con el dashboard SaaS."""
        if not self._saas_agent:
            messagebox.showwarning("Sin conexión", "Conéctate al dashboard primero.")
            return

        if not self._saas_last_log_id:
            messagebox.showwarning(
                "Sin diagnóstico",
                "Ejecuta un Diagnóstico IA primero para asociar los trabajos a un log.",
            )
            return

        session_changes = self.tracker.get_session_changes()
        if not session_changes:
            messagebox.showinfo(
                "Sin trabajos",
                "No hay trabajos registrados en esta sesión.\n"
                "Aplica alguna optimización primero.",
            )
            return

        self._saas_sync_btn.configure(state="disabled", text="Sincronizando...")
        self._saas_status_lbl.configure(
            text=f"Sincronizando {len(session_changes)} trabajos...", text_color=COLOR_MUTED)

        log_id_snapshot = self._saas_last_log_id

        def _task():
            # Recolectar métricas actuales (después de optimizar)
            metrics_after = None
            try:
                metrics_after = self._saas_agent.collect_metrics()
            except Exception:
                pass  # métricas after son opcionales

            ok = self._saas_agent.send_jobs(
                log_id=log_id_snapshot,
                applied_jobs=session_changes,
                metrics_after=metrics_after,
            )

            if ok:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text=f"✓ {len(session_changes)} trabajos sincronizados con el dashboard.",
                    text_color=COLOR_SUCCESS))
                self.after(0, lambda: messagebox.showinfo(
                    "Sincronización exitosa",
                    f"{len(session_changes)} trabajos enviados al dashboard.\n"
                    "Ya puedes verlos en win-optimizer-saas.vercel.app",
                ))
            else:
                self.after(0, lambda: self._saas_status_lbl.configure(
                    text="Error al sincronizar trabajos.", text_color=COLOR_DANGER))
                self.after(0, lambda: messagebox.showerror(
                    "Error de sincronización",
                    "No se pudieron enviar los trabajos al dashboard.\n"
                    "Verifica tu conexión a internet.",
                ))

            self.after(0, lambda: self._saas_sync_btn.configure(
                state="normal", text="Sincronizar Trabajos"))

        threading.Thread(target=_task, daemon=True).start()


def main() -> None:
    """Punto de entrada principal."""
    # Verificar y solicitar permisos de administrador
    if not is_admin():
        logger.warning("No se tienen permisos de administrador. Solicitando elevación...")
        request_admin()
        return

    logger.info(f"Iniciando {APP_NAME} v{APP_VERSION}")
    app = WinOptimizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
