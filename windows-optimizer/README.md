# ⚡ WinOptimizer Pro v1.0.0

> Optimizador de rendimiento para Windows 10 y Windows 11.
> Desarrollado con SaaS Factory V3 methodology.

```
┌─────────────────────────────────────────────────┐
│   ⚡ WinOptimizer Pro v1.0.0                     │
│   Optimiza tu PC con Windows en un solo clic    │
└─────────────────────────────────────────────────┘
```

## Características

- ✅ **18+ servicios** innecesarios identificados y desactivables
- ✅ **12 tweaks del registro** de rendimiento y gaming
- ✅ **Plan Ultimate Performance** (oculto por defecto en Windows)
- ✅ **Limpieza profunda** del sistema (temp, WU cache, WinSxS)
- ✅ **Optimización de red** (Nagle, TCP, DNS)
- ✅ **Efectos visuales** configurables
- ✅ **Punto de restauración** automático antes de cambios
- ✅ **Reversión completa** de todos los cambios
- ✅ **Log detallado** de cada operación
- ✅ Detecta **laptops** automáticamente (ajusta recomendaciones)
- ✅ Compatible con **Windows 10 y Windows 11**

## Capturas de pantalla (diseño)

```
┌──────────────┬─────────────────────────────────────────┐
│ ⚡WinOptimiz │  🏠 Dashboard                            │
│              │  ────────────────────────────────────   │
│ 🏠 Dashboard │  🖥 Windows 11    💾 16 GB   💿 SSD     │
│ ⚙️ Servicios │                                          │
│ 🔧 Registro  │  ⚠️ Recomendaciones:                    │
│ ⚡ Energía   │  1. Crear backup primero                │
│ 🧹 Limpieza  │  2. Cerrar aplicaciones                 │
│ 🌐 Red       │  3. Revisar cada sección                │
│ 👁 Visual    │  4. Reiniciar al finalizar              │
│ 📋 Log       │                                          │
│              │  📊 Optimizaciones disponibles:         │
│ [🛡 Backup]  │  ⚙️ Servicios  18 servicios             │
│ [🚀 Aplicar] │  🔧 Registro   12 tweaks                │
│ [↩ Revertir] │  ⚡ Energía    Ultimate Performance     │
└──────────────┴─────────────────────────────────────────┘
```

## Instalación rápida

### Opción A: Ejecutable compilado (recomendado)
```cmd
# 1. Instalar Python 3.10+ (con "Add to PATH" marcado)
# 2. Doble clic en install.bat
# 3. Clic derecho en dist\WinOptimizerPro.exe → "Ejecutar como administrador"
```

### Opción B: Modo desarrollo
```bash
pip install -r requirements.txt
python main.py
```

## Estructura del proyecto

```
windows-optimizer/
├── main.py                   # GUI + Controller principal
├── requirements.txt          # Dependencias Python
├── build.py                  # Script de compilación PyInstaller
├── install.bat               # Instalador automático
├── run_dev.bat               # Ejecutar en modo desarrollo
│
├── optimizer/
│   ├── core.py               # Motor base (PowerShell + Registry)
│   ├── backup.py             # Restore points + backup registro
│   ├── services.py           # Gestión de servicios
│   ├── registry.py           # Tweaks del registro
│   ├── power.py              # Plan de energía
│   ├── cleanup.py            # Limpieza del disco
│   ├── network.py            # Optimización de red
│   └── visual.py             # Efectos visuales
│
├── utils/
│   ├── admin.py              # Verificación de privilegios
│   ├── logger.py             # Sistema de logging
│   └── compatibility.py     # Compatibilidad del sistema
│
├── assets/
│   └── icon.ico              # Icono de la aplicación
│
├── RESEARCH_REPORT.md        # Parte 1: Investigación técnica
├── TECHNICAL_DOCS.md         # Parte 3: Documentación técnica
└── README.md                 # Este archivo
```

## Uso

1. **Crear backup** → Clic en `🛡 Crear Backup` (siempre primero)
2. **Revisar secciones** → Desmarcar lo que no quieras
3. **Aplicar** → Clic en `🚀 Aplicar Todo`
4. **Reiniciar** → El equipo para aplicar todos los cambios
5. **Revertir** → Si algo falla: `↩ Revertir Cambios`

## Requisitos

| Componente | Mínimo |
|------------|--------|
| SO | Windows 10 (1809+) / Windows 11 |
| Privilegios | Administrador (requerido) |
| Python | 3.10+ (solo modo dev) |
| RAM | 512 MB disponibles |

## Tecnologías

| Componente | Tecnología |
|------------|-----------|
| GUI | CustomTkinter 5.2+ |
| Optimizaciones | PowerShell 5.1 + winreg |
| Compilación | PyInstaller 6.0+ |
| Logging | Python logging module |
| Backup | WMI + JSON |

## Seguridad

- 🛡 Crea punto de restauración del sistema automáticamente
- 🔄 Respaldo del registro en JSON antes de modificar
- ↩ Reversión completa disponible
- 📋 Log detallado de cada operación
- ✅ Solo modifica lo que el usuario selecciona explícitamente
- ❌ No se conecta a Internet
- ❌ No modifica servicios críticos del sistema

## Licencia

MIT License - Uso libre con atribución.

---

Desarrollado con ❤️ usando **SaaS Factory V3 Methodology**
