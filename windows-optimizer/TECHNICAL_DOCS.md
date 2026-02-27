# 📖 Parte 3: Documentación Técnica — WinOptimizer Pro v1.0.0

---

## Índice

1. [Arquitectura del Programa](#arquitectura)
2. [Requisitos del Sistema](#requisitos)
3. [Dependencias y Permisos](#dependencias)
4. [Guía de Ejecución Paso a Paso](#ejecucion)
5. [Descripción de Módulos](#modulos)
6. [Pruebas de Funcionalidad](#pruebas)
7. [Seguridad](#seguridad)
8. [Solución de Problemas](#troubleshooting)

---

## 1. Arquitectura del Programa {#arquitectura}

### Diagrama de arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     WinOptimizer Pro                         │
├──────────────────────────────────────────────────────────────┤
│  CAPA PRESENTACIÓN (main.py)                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │ Sidebar Nav  │  │ Main Content│  │   Status Bar      │  │
│  │ + Botones    │  │ (Secciones) │  │   Progress Bar    │  │
│  └──────────────┘  └─────────────┘  └───────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  CAPA LÓGICA (optimizer/)                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ services │ │ registry │ │  power   │ │   cleanup    │  │
│  │ .py      │ │ .py      │ │  .py     │ │   .py        │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │ network  │ │ visual   │ │  backup  │                   │
│  │ .py      │ │ .py      │ │  .py     │                   │
│  └──────────┘ └──────────┘ └──────────┘                   │
├──────────────────────────────────────────────────────────────┤
│  CAPA BASE (optimizer/core.py + utils/)                      │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │ PowerShellRun  │ │ RegistryEdit │ │ ServiceManager   │  │
│  └────────────────┘ └──────────────┘ └──────────────────┘  │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  admin.py      │ │  logger.py   │ │ compatibility.py │  │
│  └────────────────┘ └──────────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  CAPA SISTEMA OPERATIVO                                      │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │  PowerShell    │ │   winreg     │ │  Windows APIs    │  │
│  │  (subprocess)  │ │  (stdlib)    │ │  (subprocess)    │  │
│  └────────────────┘ └──────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de ejecución

```
1. Inicio → Verificar privilegios Admin (UAC)
2. Cargar info del sistema (versión Windows, RAM, SSD)
3. Renderizar GUI con CustomTkinter
4. Usuario → [Crear Backup] → Punto de restauración + backup registro
5. Usuario → Seleccionar optimizaciones → [Aplicar Todo]
6. Para cada categoría seleccionada:
   a. Ejecutar en hilo separado (no bloquear UI)
   b. Llamar módulo correspondiente
   c. Módulo ejecuta cambio (PowerShell / winreg)
   d. Registrar en ChangeTracker
   e. Actualizar progress bar
7. Al finalizar: mostrar resumen + recomendación de reinicio
8. Opcionalmente: [Revertir] → Ejecutar comandos de reversión
```

### Patrón de diseño

- **Feature-First**: Cada área de optimización es un módulo independiente
- **Strategy Pattern**: Cada optimizador implementa la misma interfaz (`optimize_all()`)
- **Observer Pattern**: `ChangeTracker` registra todos los cambios
- **Command Pattern**: Cada cambio incluye su comando de reversión
- **Thread Worker**: Las operaciones largas se ejecutan en hilos separados

---

## 2. Requisitos del Sistema {#requisitos}

### Mínimos

| Componente | Requisito |
|------------|-----------|
| **SO** | Windows 10 (Build 17763 / 1809) o superior |
| **Arquitectura** | x64 (64-bit) |
| **RAM** | 512 MB disponibles |
| **Disco** | 50 MB para el ejecutable |
| **Privilegios** | Administrador (requerido) |
| **Python** | 3.10+ (solo en modo desarrollo) |

### Recomendados

| Componente | Recomendado |
|------------|-------------|
| **SO** | Windows 10 22H2 / Windows 11 23H2 |
| **RAM** | 1 GB disponibles |
| **PowerShell** | 5.1+ (incluido en Windows 10/11) |

### Verificación de compatibilidad (automática al iniciar)

```python
# El programa verifica automáticamente:
- Versión de Windows (Build number)
- Disponibilidad de PowerShell
- Presencia de SSD o HDD
- RAM total instalada
- Si es laptop o desktop (detecta batería)
```

---

## 3. Dependencias y Permisos {#dependencias}

### Dependencias Python (requirements.txt)

```
customtkinter>=5.2.2    # GUI moderna (dark mode)
pyinstaller>=6.0.0      # Compilar a .exe
pillow>=10.0.0          # Procesar imágenes/iconos
```

### Módulos estándar utilizados (sin instalación)

```
winreg          # Acceso al registro de Windows
subprocess      # Ejecutar PowerShell y comandos del sistema
threading       # Operaciones no bloqueantes
logging         # Sistema de logs
json            # Persistencia de datos
pathlib         # Manejo de rutas
ctypes          # Verificación de privilegios Admin
platform        # Información del sistema
os, shutil      # Operaciones de archivos
```

### Permisos requeridos

| Permiso | Por qué se necesita |
|---------|---------------------|
| **Administrador** | Modificar servicios, registro HKLM, planes de energía |
| **Escritura en HKLM** | Tweaks de rendimiento del sistema |
| **Escritura en HKCU** | Tweaks del usuario (efectos visuales, etc.) |
| **Acceso a servicios** | Detener/configurar servicios de Windows |
| **PowerShell Bypass** | Ejecutar scripts de optimización |
| **Escritura en %APPDATA%** | Guardar logs y backups del registro |

---

## 4. Guía de Ejecución Paso a Paso {#ejecucion}

### Modo Desarrollo (código fuente)

#### Paso 1: Instalar Python 3.10+
```
https://www.python.org/downloads/
⚠️ Marcar "Add Python to PATH" durante la instalación
```

#### Paso 2: Instalar dependencias
```bash
cd "C:\Users\willy\optimizacion windows\windows-optimizer"
pip install -r requirements.txt
```

#### Paso 3: Ejecutar
```bash
# Doble clic en run_dev.bat (se eleva automáticamente)
# O manualmente:
python main.py
```

### Modo Compilado (ejecutable .exe)

#### Paso 1: Compilar
```bash
# Doble clic en install.bat (o ejecutar como admin):
python build.py

# O con opciones específicas:
python build.py --onefile       # Un solo .exe (más portátil)
python build.py --onedir        # Carpeta (arranque más rápido)
python build.py --debug         # Con consola para debug
```

#### Paso 2: Ejecutar el .exe
```
1. Navegar a: dist\WinOptimizerPro.exe
2. Clic derecho → "Ejecutar como administrador"
3. Aceptar el aviso de Control de Cuentas de Usuario (UAC)
```

### Flujo recomendado de uso

```
1. [Verificar] Información del sistema en el Dashboard
2. [Backup]    Clic en "🛡 Crear Backup" → Esperar confirmación
3. [Revisar]   Recorrer cada sección y desmarcar lo que NO quieras
4. [Aplicar]   Clic en "🚀 Aplicar Todo" → Confirmar el diálogo
5. [Esperar]   Barra de progreso (puede tardar 2-10 min con DISM)
6. [Reiniciar] Windows para aplicar todos los cambios
7. [Verificar] Comprobar que todo funciona correctamente
8. [Revertir]  Si algo falla → Clic en "↩ Revertir Cambios"
```

---

## 5. Descripción de Módulos {#modulos}

### `main.py` — GUI y Controller
- **Framework:** CustomTkinter (tema oscuro)
- **Patrón:** MVC (Controller + View combinados)
- **Responsabilidad:** Renderizar UI, gestionar eventos, coordinar módulos
- **Threading:** Todas las operaciones pesadas en `threading.Thread(daemon=True)`
- **Tamaño:** ~500 líneas

### `optimizer/core.py` — Motor base
- `PowerShellRunner.run()`: Ejecuta comandos PowerShell con timeout y manejo de errores
- `RegistryEditor`: CRUD completo sobre el registro de Windows usando `winreg`
- `ServiceManager`: Control de servicios vía PowerShell

### `optimizer/backup.py` — Sistema de seguridad
- `create_restore_point()`: Crea checkpoint del sistema vía `Checkpoint-Computer`
- `backup_registry_keys()`: Lee y serializa valores del registro a JSON
- `restore_registry_from_backup()`: Revierte valores del registro desde JSON
- **Almacenamiento:** `%APPDATA%\WinOptimizer\backups\`

### `optimizer/services.py` — Servicios
- Lista curada de 18 servicios seguros de deshabilitar
- Detecta si el servicio existe antes de actuar
- Registra el estado original para reversión

### `optimizer/registry.py` — Registro
- 12 tweaks probados y documentados
- Categorías: rendimiento, gaming, red, visual, startup
- Cada tweak incluye: hive, path, name, value, revert_value, risk level

### `optimizer/power.py` — Energía
- Habilita el plan Ultimate Performance oculto
- Configura estados del procesador al 100%
- Detecta laptops y aplica plan adecuado
- Deshabilita hibernación (libera espacio = tamaño RAM)

### `optimizer/cleanup.py` — Limpieza
- Limpia TEMP usuario, TEMP sistema, Papelera, caché WU
- Verifica y habilita TRIM para SSDs
- DISM cleanup opcional (lento pero efectivo)

### `optimizer/network.py` — Red
- Deshabilita algoritmo de Nagle por adaptador de red activo
- Optimiza parámetros TCP con `netsh`
- Deshabilita Network Throttling en el perfil multimedia

### `optimizer/visual.py` — Visual
- Configura VisualFXSetting = 2 (máximo rendimiento)
- Deshabilita animaciones de ventanas
- Deshabilita efectos de transparencia (opcional)
- Deshabilita Aero Shake

### `utils/admin.py` — Privilegios
- Detecta si el proceso tiene privilegios de administrador
- Relanza el proceso con elevación UAC automáticamente

### `utils/logger.py` — Logging
- Logs a archivo con timestamp en `%APPDATA%\WinOptimizer\logs\`
- `ChangeTracker`: registra cambios en JSON con comandos de reversión

### `utils/compatibility.py` — Compatibilidad
- Detecta versión de Windows (build number, Win10 vs Win11)
- Detecta RAM, SSD, NVMe
- Calcula pagefile recomendado

---

## 6. Pruebas de Funcionalidad {#pruebas}

### Casos de prueba manuales

#### Test 1: Verificación de privilegios
```
1. Ejecutar sin privilegios de administrador
ESPERADO: Solicita elevación UAC automáticamente
```

#### Test 2: Detección del sistema
```
1. Abrir Dashboard
ESPERADO: Muestra versión correcta de Windows, RAM, tipo de disco
```

#### Test 3: Crear punto de restauración
```
1. Clic en "🛡 Crear Backup"
ESPERADO: Muestra progreso, confirma éxito
VERIFICAR: Panel de control → Restaurar sistema → Puntos de restauración
```

#### Test 4: Servicios — deshabilitar y verificar
```
1. Sección Servicios → Seleccionar solo "SysMain"
2. Clic en "🚀 Aplicar Todo"
VERIFICAR: services.msc → SysMain → Tipo de inicio = Deshabilitado
```

#### Test 5: Registry tweak
```
1. Sección Registro → Seleccionar solo "Reducir delay del menú contextual"
2. Clic en "🚀 Aplicar Todo"
VERIFICAR: regedit → HKCU\Control Panel\Desktop → MenuShowDelay = 200
```

#### Test 6: Reversión
```
1. Aplicar algunas optimizaciones
2. Clic en "↩ Revertir Cambios"
VERIFICAR: Valores regresan al estado original
```

#### Test 7: Limpieza
```
1. Sección Limpieza → Habilitar todas las opciones básicas
2. Clic en "🚀 Aplicar Todo"
VERIFICAR: Carpetas TEMP vacías, espacio en disco aumentado
```

#### Test 8: Plan de energía
```
1. Sección Energía → Habilitar Ultimate Performance
2. Aplicar
VERIFICAR: powercfg /getactivescheme → muestra Ultimate Performance
```

### Comandos de verificación post-optimización

```powershell
# Verificar servicios deshabilitados
Get-Service SysMain, DoSvc, Spooler | Select-Object Name, StartType

# Verificar plan de energía activo
powercfg /getactivescheme

# Verificar TRIM habilitado
fsutil behavior query disabledeletenotify

# Verificar tweaks del registro
Get-ItemProperty "HKCU:\Control Panel\Desktop" -Name MenuShowDelay
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile" -Name SystemResponsiveness

# Ver logs del optimizador
Get-ChildItem "$env:APPDATA\WinOptimizer\logs\"
```

---

## 7. Seguridad {#seguridad}

### Medidas de seguridad implementadas

| Medida | Implementación |
|--------|---------------|
| **Backup obligatorio** | Punto de restauración antes de cambios |
| **Backup del registro** | JSON serializado en APPDATA |
| **Sin hardcode de secrets** | Sin credenciales en código |
| **Timeouts en comandos** | Máx. 120s por comando PS (600s DISM) |
| **Error handling** | try/except en cada operación crítica |
| **No modificar servicios críticos** | Lista negra implícita (solo lista blanca) |
| **Verificación de existencia** | Cada servicio/clave se verifica antes de modificar |
| **Logs completos** | Toda operación queda registrada |
| **Reversión completa** | Cada cambio incluye su comando de reversión |

### Lo que el programa NO hace

- ❌ No descarga ni ejecuta código externo
- ❌ No se conecta a Internet
- ❌ No modifica BIOS/UEFI
- ❌ No elimina archivos del sistema
- ❌ No modifica servicios críticos (Windows Defender, Firewall, WMI)
- ❌ No requiere claves de producto ni activación

### Análisis de riesgos

```
RIESGO BAJO: 90% de las optimizaciones
- Tweaks del registro con valores conocidos y documentados
- Servicios opcionales con amplia documentación pública
- Efectos visuales y preferencias del usuario

RIESGO MEDIO: 5%
- DISM /StartComponentCleanup (no reversible con /ResetBase)
  → Mitigado: el /ResetBase NO se usa; solo /StartComponentCleanup

RIESGO BAJO-MEDIO: 5%
- Plan Ultimate Performance en laptops → Mitigado: detecta laptop automáticamente
- Deshabilitar Print Spooler con impresora conectada → Advertencia en UI
```

---

## 8. Solución de Problemas {#troubleshooting}

### Problema: "No se puede ejecutar - necesita administrador"
**Solución:** Clic derecho → "Ejecutar como administrador"

### Problema: El punto de restauración falla
**Causa:** Límite de 1 punto por 24 horas en Windows 10/11
**Solución:** Normal si ya hay uno reciente. Continúa sin él o espera 24h.

### Problema: Servicio no se deshabilita
**Causa:** El servicio puede tener dependencias protegidas
**Solución:** Revisar en `services.msc`, algunos servicios rechazan desactivación por grupos protegidos

### Problema: DISM tarda demasiado
**Causa:** Normal - puede tardar 5-15 minutos
**Solución:** Esperar. No cerrar la aplicación. La opción DISM está desactivada por defecto.

### Problema: La GUI no se ve correctamente
**Causa:** Escala de pantalla > 100% puede afectar DPI
**Solución:** El programa usa CustomTkinter que maneja DPI automáticamente.

### Problema: Python no encontrado al compilar
**Solución:**
```cmd
# Verificar instalación
python --version
# Si no está en PATH, agregar manualmente o reinstalar con "Add to PATH" marcado
```

### Problema: CustomTkinter no instala
**Solución:**
```bash
pip install --upgrade pip
pip install customtkinter --user
```

---

## Directorio de Logs y Backups

```
%APPDATA%\WinOptimizer\
├── logs\
│   ├── optimizer_20260226_143000.log   # Log completo con timestamp
│   └── ...
├── backups\
│   ├── registry_backup_20260226_143000.json   # Backup del registro
│   └── ...
└── changes_history.json               # Historial completo de cambios
```

---

## Información del Build

| Campo | Valor |
|-------|-------|
| Versión | 1.0.0 |
| Fecha | 2026-02-26 |
| Python mínimo | 3.10 |
| Tamaño estimado .exe | 25-40 MB (onefile con CustomTkinter) |
| Compatibilidad | Windows 10 Build 17763+ / Windows 11 |
| Arquitectura | x64 |
