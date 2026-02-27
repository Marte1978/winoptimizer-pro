# 📊 Parte 1: Investigación — Optimización de Windows 10/11

> Documento de investigación técnica exhaustiva.
> Fuentes: Microsoft Docs, TenForums, ElevenForum, XDA, HowToGeek, GitHub.

---

## Resumen Ejecutivo

La optimización de Windows puede dividirse en 6 áreas de impacto:

| Área | Impacto en rendimiento | Riesgo típico |
|------|----------------------|---------------|
| Servicios innecesarios | 1-5% CPU/RAM libre | Bajo |
| Tweaks de registro | 2-10% FPS / respuesta | Bajo |
| Plan de energía | 5-15% en cargas CPU | Bajo (desktops) |
| Limpieza del disco | 2-20 GB liberados | Muy bajo |
| Red/TCP | -10-200ms latencia | Bajo |
| Efectos visuales | 1-3% CPU | Muy bajo |

---

## 1. Servicios de Windows Desactivables Seguros

### Metodología de desactivación
```powershell
Stop-Service -Force -Name "NombreServicio"
Set-Service -Name "NombreServicio" -StartupType Disabled
```

### Lista curada (18 servicios seguros)

| Servicio | Nombre | Beneficio | Riesgo |
|----------|--------|-----------|--------|
| SysMain (Superfetch) | SysMain | Reduce uso de disco en SSD | Bajo |
| Delivery Optimization | DoSvc | Libera ancho de banda | Bajo |
| Print Spooler | Spooler | Seguridad + rendimiento | Bajo* |
| Mobile Hotspot | icssvc | RAM libre | Bajo |
| Phone Service | PhoneSvc | Procesos reducidos | Bajo |
| Smart Card | SCardSvr | Sin uso en PC personal | Bajo |
| Sensor Service | SensrSvc | Innecesario en desktop | Bajo |
| Geolocation | lfsvc | Privacidad + CPU | Bajo |
| Bluetooth | bthserv | Si no se usa BT | Bajo |
| Fax | Fax | Obsoleto | Bajo |
| Telemetría | DiagTrack | Privacidad + red | Bajo |
| Xbox Game Save | XblGameSave | Sin Xbox Game Pass | Bajo |
| Xbox Auth | XblAuthManager | Sin Xbox Game Pass | Bajo |
| Xbox Networking | XboxNetApiSvc | Sin Xbox Game Pass | Bajo |
| Retail Demo | RetailDemo | Bloatware | Bajo |
| WMP Network | WMPNetworkSvc | Obsoleto (Win10) | Bajo |
| Remote Desktop | TermService | Si no se usa RDP | Medio |
| Diagnostic Execution | diagsvc | No requerido | Bajo |

> *Print Spooler: deshabilitar solo si no hay impresora conectada.

### Advertencia de interdependencias
> Nunca deshabilitar: Windows Update, Windows Defender Firewall,
> DCOM Server Process Launcher, Windows Management Instrumentation.
> Fuente: [TenForums](https://www.tenforums.com/performance-maintenance/60418-windows-services-can-you-safely-disable.html)

---

## 2. Tweaks del Registro — Técnicas Probadas

### 2.1 Power Throttling (Rendimiento CPU)
```
HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling
PowerThrottlingOff = 1 (DWORD)
```
**Beneficio:** 5-10% en cargas CPU intensivas.
**Riesgo:** Bajo. Mayor consumo en laptops.
**Fuente:** [SpyBoy Blog 2025](https://spyboy.blog/2025/01/13/boost-windows-11-performance-with-registry-hacks/)

### 2.2 WaitToKillServiceTimeout
```
HKLM\SYSTEM\CurrentControlSet\Control
WaitToKillServiceTimeout = "2000" (String, default: 5000)
```
**Beneficio:** Apagado 3 segundos más rápido.
**Riesgo:** Muy bajo.

### 2.3 Eliminar Startup Delay
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize
StartupDelayInMSec = 0 (DWORD)
```
**Beneficio:** Elimina delay artificial de 10s en arranque.
**Riesgo:** Muy bajo.

### 2.4 MMCSS — Prioridad Gaming
```
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile
SystemResponsiveness = 10 (DWORD, default: 20)

...\Tasks\Games
GPU Priority = 8
Priority = 6
```
**Beneficio:** +2-8% FPS, mejor respuesta en juegos.
**Riesgo:** Bajo.
**Fuente:** [Geekflare](https://geekflare.com/gaming/windows-registry-hacks-to-improve-gaming/)

### 2.5 GameDVR / Xbox Game Bar
```
HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR
AppCaptureEnabled = 0

HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR
AllowGameDVR = 0
```
**Beneficio:** +2-5% FPS en juegos.
**Riesgo:** Muy bajo. Pierde grabación con Win+G.

### 2.6 HAGS (Hardware-Accelerated GPU Scheduling)
```
HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers
HwSchMode = 2 (DWORD)
```
**Beneficio:** Mejora frametime consistency, reduce 1% lows.
**Requisito:** GPU GTX 1000+ / RX 5000+ + driver reciente.
**Fuente:** [HowToGeek](https://www.howtogeek.com/756935/how-to-enable-hardware-accelerated-gpu-scheduling-in-windows-11/)

### 2.7 Nagle Algorithm
```
HKLM\SYSTEM\...\Tcpip\Parameters\Interfaces\{GUID}
TcpAckFrequency = 1
TcpNoDelay = 1
```
**Beneficio:** -10-200ms latencia en gaming online.
**Riesgo:** Bajo. Más tráfico de red.

---

## 3. Plan de Energía — Ultimate Performance

### Habilitar plan oculto
```powershell
powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
```
**Beneficio:** Elimina micro-latencias del CPU. Ideal para desktops.
**Riesgo:** Mayor consumo de energía. NO recomendado en laptops.
**Fuente:** [Ghacks](https://www.ghacks.net/2024/12/04/how-to-enable-the-ultimate-performance-plan-in-windows-11/)

### Configurar procesador al 100%
```
Panel de Control → Opciones de energía → Configuración avanzada
Procesador mínimo: 100%
Procesador máximo: 100%
```

### Comparativa de planes

| Plan | CPU Throttling | Latencia | Consumo |
|------|---------------|----------|---------|
| Equilibrado | Sí (50-100%) | Variable | Normal |
| Alto rendimiento | Parcial | Baja | Alto |
| Ultimate Performance | No (100%) | Mínima | Muy alto |

---

## 4. Gestión de Memoria Virtual

### Configuración óptima por RAM instalada

| RAM | Pagefile Inicial | Pagefile Máximo |
|-----|-----------------|-----------------|
| 8 GB | 8.192 MB | 16.384 MB |
| 16 GB | 16.384 MB | 32.768 MB |
| 32 GB | 24.576 MB | 48.000 MB |

**Reglas clave:**
- Usar tamaño **fijo** (inicial = máximo) en SSD para evitar fragmentación
- **Nunca deshabilitar** completamente aunque tengas 32+ GB RAM
- En SSD NVMe: dejar en automático suele ser óptimo
- Fuente: [WindowsCentral](https://www.windowscentral.com/software-apps/windows-11/how-to-manage-virtual-memory-on-windows-11)

---

## 5. Optimización de SSD

### TRIM — Verificar y habilitar
```cmd
fsutil behavior query disabledeletenotify
:: DisableDeleteNotify = 0 → TRIM HABILITADO ✅
:: DisableDeleteNotify = 1 → TRIM DESHABILITADO ❌

fsutil behavior set disabledeletenotify 0
```
**Fuente:** [TechTimes 2024](https://www.techtimes.com/articles/304713/20240516/ssd-trim-command-enable-disable-windows-11.htm)

### Prácticas para SSD
- **NO desfragmentar** (Windows lo hace automáticamente con TRIM)
- Deshabilitar indexación del contenido del drive SSD
- Mantener 15-20% de espacio libre para wear leveling
- Actualizar firmware del fabricante (Samsung Magician, WD Dashboard)

---

## 6. Limpieza del Sistema

### Jerarquía de limpieza (de menor a mayor riesgo)

1. **Archivos TEMP del usuario** (`%TEMP%`) — Sin riesgo
2. **Windows\\Temp** — Sin riesgo
3. **Papelera de reciclaje** — Sin riesgo
4. **Caché Windows Update** — Bajo riesgo (se re-descarga si es necesario)
5. **WinSxS con DISM** — Bajo riesgo, no reversible con `/ResetBase`
6. **Prefetch** — No recomendado en SSD (Windows lo gestiona)

### DISM para WinSxS
```cmd
Dism.exe /Online /Cleanup-Image /AnalyzeComponentStore
Dism.exe /Online /Cleanup-Image /StartComponentCleanup
```
**Beneficio:** 2-15 GB liberados
**Fuente:** [Microsoft Docs](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/clean-up-the-winsxs-folder?view=windows-11)

---

## 7. Herramientas de Terceros Recomendadas

### Gratuitas y confiables

| Herramienta | Función | Riesgo | URL |
|-------------|---------|--------|-----|
| **ChrisTitus WinUtil** | Debloat + tweaks | Medio | github.com/ChrisTitusTech/winutil |
| **Autoruns** (Microsoft) | Gestión arranque | Muy bajo | learn.microsoft.com/sysinternals |
| **Winaero Tweaker** | GUI tweaks | Bajo | winaero.com/winaero-tweaker |
| **BleachBit** | Limpieza | Bajo | bleachbit.org |
| **Process Lasso** | Prioridad procesos | Bajo | bitsum.com |
| **TCP Optimizer** | Red TCP/IP | Bajo | speedguide.net |

### De pago (Premium)
| Herramienta | Función | Precio aprox. |
|-------------|---------|---------------|
| **NVCleanstall** | Driver NVIDIA limpio | Gratis (donación) |
| **Process Lasso Pro** | Optimización avanzada | ~$35 |

---

## 8. Seguridad y Rendimiento — Equilibrio

### Impacto del antivirus en rendimiento

| Solución | Impacto en disco | Impacto en CPU | Recomendación |
|----------|-----------------|----------------|---------------|
| Windows Defender | 2-5% | 1-3% | ✅ Suficiente para uso general |
| Malwarebytes (escáner) | Bajo (escaneo manual) | Bajo | ✅ Complemento gratuito |
| Norton/McAfee | 8-15% | 5-10% | ⚠️ Exceso para mayoría |
| Kaspersky/ESET | 4-7% | 3-5% | Decisión personal |

### Recomendaciones seguras
- Usar **Windows Defender** como solución principal
- Excluir carpetas de proyectos/desarrollo del escáner en tiempo real
- No deshabilitar Windows Firewall
- Mantener SmartScreen activado

---

## 9. Actualizaciones y Drivers

### Estrategia de actualización
- **Windows Update:** Activar, pero con opción "Notificarme para reiniciar"
- **Drivers GPU:** Actualizar manual desde sitio del fabricante (NVIDIA/AMD/Intel)
  - NVIDIA: [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx)
  - AMD: [amd.com/support](https://www.amd.com/en/support)
- **NVCleanstall** para NVIDIA: instala solo los componentes necesarios del driver
- **Delivery Optimization:** Desactivar para no compartir ancho de banda

---

## 10. Optimización de Navegadores

### Google Chrome

```
# Hardware Acceleration
chrome://settings/ → Sistema → Usar aceleración por hardware → ON

# Flags de rendimiento
chrome://flags/#enable-gpu-rasterization → Enabled
chrome://flags/#parallel-downloading → Enabled
chrome://flags/#memory-saver-mode → Enabled (duerme tabs inactivas)
```

### Mozilla Firefox

```javascript
// about:config
gfx.webrender.all = true              // GPU rendering
browser.cache.memory.capacity = 204800 // 200 MB cache
layers.acceleration.force-enabled = true
```

### Microsoft Edge

```
edge://settings/system
- Sleeping Tabs: ON (ahorra RAM)
- Hardware Acceleration: ON
- Efficiency Mode: Equilibrado
```

---

## Comparativa Global — Antes vs Después

| Métrica | Antes | Después (tipico) | Mejora |
|---------|-------|-----------------|--------|
| Tiempo de inicio | 30-60s | 15-30s | ~40% |
| RAM en reposo (16GB) | 3-4 GB | 2-3 GB | ~25% |
| FPS en juegos (CPU-bound) | Base | +5-15% | Variable |
| Latencia online (ms) | 20-50 ms | 10-30 ms | -30% |
| Espacio liberado | - | 3-20 GB | Significativo |
| Tiempo de apagado | 10-15s | 5-8s | ~40% |

---

## Fuentes y Referencias

1. [TenForums - Services Safe to Disable](https://www.tenforums.com/performance-maintenance/60418-windows-services-can-you-safely-disable.html)
2. [ElevenForum - Services to Disable Win11](https://www.elevenforum.com/t/services-to-disable-in-windows-11.3055/)
3. [SpyBoy - Registry Hacks 2025](https://spyboy.blog/2025/01/13/boost-windows-11-performance-with-registry-hacks/)
4. [Geekflare - Windows Registry Gaming](https://geekflare.com/gaming/windows-registry-hacks-to-improve-gaming/)
5. [HowToGeek - HAGS](https://www.howtogeek.com/756935/how-to-enable-hardware-accelerated-gpu-scheduling-in-windows-11/)
6. [Ghacks - Ultimate Performance Plan](https://www.ghacks.net/2024/12/04/how-to-enable-the-ultimate-performance-plan-in-windows-11/)
7. [Microsoft - WinSxS DISM](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/clean-up-the-winsxs-folder?view=windows-11)
8. [WindowsCentral - Virtual Memory](https://www.windowscentral.com/software-apps/windows-11/how-to-manage-virtual-memory-on-windows-11)
9. [XDA - Windows Gaming 2026](https://www.xda-developers.com/im-stuck-with-windows-for-gaming-in-2026-but-heres-how-im-optimizing-it/)
10. [GitHub - ChrisTitusTech/winutil](https://github.com/ChrisTitusTech/winutil)
11. [Mozilla Support - Firefox Performance](https://support.mozilla.org/en-US/kb/performance-settings)
12. [Microsoft Sysinternals - Autoruns](https://learn.microsoft.com/en-us/sysinternals/downloads/autoruns)
13. [TechTimes - SSD TRIM Win11](https://www.techtimes.com/articles/304713/20240516/ssd-trim-command-enable-disable-windows-11.htm)
14. [Auslogics - SSD Optimization](https://www.auslogics.com/en/articles/ssd-optimization-on-windows/)
15. [WindowsForum - Gaming Tuning 2026](https://windowsforum.com/threads/windows-11-gaming-tuning-guide-2026-safe-consistent-performance.401517/)
