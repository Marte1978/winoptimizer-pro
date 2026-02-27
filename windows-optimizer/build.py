"""
Script de compilación para WinOptimizer Pro.
Genera un ejecutable .exe único con PyInstaller.

Uso:
    python build.py
    python build.py --onefile        # Ejecutable único (más portátil)
    python build.py --onedir         # Carpeta con dependencias (más rápido al arrancar)
    python build.py --debug          # Con consola visible para depuración

Requisitos:
    pip install pyinstaller pillow
"""
import subprocess
import sys
import os
import shutil
import argparse
from pathlib import Path

APP_NAME = "WinOptimizerPro"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "main.py"
ICON_PATH = "assets/icon.ico"
DIST_DIR = "dist"
BUILD_DIR = "build"


def clean_previous_build() -> None:
    """Elimina artefactos de compilaciones anteriores."""
    for dir_name in [DIST_DIR, BUILD_DIR]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"[limpieza] Eliminado: {dir_name}/")

    spec_file = f"{APP_NAME}.spec"
    if Path(spec_file).exists():
        os.remove(spec_file)
        print(f"[limpieza] Eliminado: {spec_file}")


def create_default_icon() -> None:
    """Crea un icono por defecto si no existe."""
    icon_path = Path(ICON_PATH)
    if icon_path.exists():
        return

    icon_path.parent.mkdir(exist_ok=True)

    try:
        from PIL import Image, ImageDraw
        # Crear icono simple de 256x256
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Fondo oscuro redondeado
        draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill="#0f0f0f")
        # Acento verde
        draw.rounded_rectangle([20, 20, 236, 236], radius=35, outline="#00d4aa", width=4)
        # Símbolo de rayo ⚡
        draw.polygon([(128, 40), (80, 130), (118, 130), (96, 216), (176, 110), (136, 110)],
                     fill="#00d4aa")

        img.save(str(icon_path), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print(f"[icono] Icono generado: {icon_path}")
    except ImportError:
        print("[advertencia] Pillow no instalado. Se usará icono por defecto de Python.")
    except Exception as e:
        print(f"[advertencia] No se pudo crear icono: {e}")


def build(one_file: bool = True, debug: bool = False) -> None:
    """Ejecuta PyInstaller para compilar el ejecutable."""
    create_default_icon()

    # Detectar rutas de TCL/TK — buscar en múltiples ubicaciones posibles
    import sysconfig, glob as _glob

    def _find_python_home() -> Path:
        """Busca el directorio real de Python (no el lanzador py.exe)."""
        candidates = [
            Path(sys.executable).parent,
            Path(sysconfig.get_path("stdlib")).parent.parent,
        ]
        # También buscar por tkinter.__file__
        try:
            import tkinter as _tk
            candidates.append(Path(_tk.__file__).parent.parent.parent)
        except Exception:
            pass
        for c in candidates:
            if (c / "DLLs").exists() and (c / "tcl").exists():
                return c
        return Path(sys.executable).parent

    python_dir = _find_python_home()
    tcl_dir = python_dir / "tcl"
    dlls_dir = python_dir / "DLLs"
    print(f"[build] Python home detectado: {python_dir}")
    print(f"[build] TCL dir: {tcl_dir} (existe: {tcl_dir.exists()})")
    print(f"[build] DLLs dir: {dlls_dir} (existe: {dlls_dir.exists()})")

    # Argumentos base de PyInstaller
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        MAIN_SCRIPT,
        "--name", APP_NAME,
        "--clean",
        "--noconfirm",
        "--collect-all", "customtkinter",
        "--collect-all", "tkinter",
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.messagebox",
        "--hidden-import", "_tkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "winreg",
        "--add-data", "optimizer;optimizer",
        "--add-data", "utils;utils",
    ]

    # Incluir DLLs de TCL/TK explícitamente
    for dll_name in ["tcl86t.dll", "tk86t.dll", "_tkinter.pyd"]:
        dll_path = dlls_dir / dll_name
        if dll_path.exists():
            pyinstaller_args += ["--add-binary", f"{dll_path};."]

    # Incluir carpetas TCL/TK con los nombres exactos que PyInstaller espera:
    # pyi_rth__tkinter.py busca "_tcl_data" y "_tk_data" en el directorio temporal
    if tcl_dir.exists():
        tcl86 = tcl_dir / "tcl8.6"
        tk86  = tcl_dir / "tk8.6"
        if tcl86.exists():
            pyinstaller_args += ["--add-data", f"{tcl86};_tcl_data"]
        if tk86.exists():
            pyinstaller_args += ["--add-data", f"{tk86};_tk_data"]

    # Icono (si existe)
    if Path(ICON_PATH).exists():
        pyinstaller_args += ["--icon", ICON_PATH]

    # Modo de empaquetado
    if one_file:
        pyinstaller_args.append("--onefile")
        print("[build] Modo: ejecutable único (.exe)")
    else:
        pyinstaller_args.append("--onedir")
        print("[build] Modo: directorio (arranque más rápido)")

    # Modo ventana vs consola
    if debug:
        pyinstaller_args.append("--console")
        print("[build] Modo: consola (debug)")
    else:
        pyinstaller_args.append("--windowed")
        print("[build] Modo: ventana (sin consola)")

    # Metadata de versión (solo Windows)
    version_file = _create_version_file()
    if version_file and Path(version_file).exists():
        pyinstaller_args += ["--version-file", version_file]

    print(f"\n[build] Compilando {APP_NAME} v{APP_VERSION}...")
    print(f"[build] Comando: {' '.join(pyinstaller_args[2:])}\n")

    result = subprocess.run(pyinstaller_args)

    if result.returncode == 0:
        exe_path = _find_output_exe(one_file)
        print(f"\n{'='*60}")
        print(f"[OK] Compilacion exitosa!")
        print(f"   Ejecutable: {exe_path}")
        print(f"   Tamano: {_file_size_mb(exe_path):.1f} MB")
        print(f"{'='*60}")
        _show_run_instructions(exe_path)
    else:
        print(f"\n[ERROR] Error en la compilacion (codigo {result.returncode})")
        sys.exit(1)

    # Limpiar archivo de versión temporal
    if version_file and Path(version_file).exists():
        os.remove(version_file)


def _create_version_file() -> str:
    """Crea un archivo de versión para el ejecutable de Windows."""
    ver_parts = APP_VERSION.split(".")
    while len(ver_parts) < 4:
        ver_parts.append("0")
    ver_tuple = ", ".join(ver_parts)

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({ver_tuple}),
    prodvers=({ver_tuple}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'WinOptimizer Pro'),
         StringStruct(u'FileDescription', u'WinOptimizer Pro - Optimizador de Windows'),
         StringStruct(u'FileVersion', u'{APP_VERSION}'),
         StringStruct(u'InternalName', u'{APP_NAME}'),
         StringStruct(u'OriginalFilename', u'{APP_NAME}.exe'),
         StringStruct(u'ProductName', u'WinOptimizer Pro'),
         StringStruct(u'ProductVersion', u'{APP_VERSION}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
"""
    ver_file = "version_info.txt"
    with open(ver_file, "w", encoding="utf-8") as f:
        f.write(content)
    return ver_file


def _find_output_exe(one_file: bool) -> str:
    if one_file:
        candidates = list(Path(DIST_DIR).glob(f"{APP_NAME}*.exe"))
        if candidates:
            return str(candidates[0])
        return f"{DIST_DIR}/{APP_NAME}.exe"
    else:
        return f"{DIST_DIR}/{APP_NAME}/{APP_NAME}.exe"


def _file_size_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0


def _show_run_instructions(exe_path: str) -> None:
    print(f"""
[!] Instrucciones de ejecucion:

   1. Clic derecho en {Path(exe_path).name}
   2. Seleccionar "Ejecutar como administrador"
   3. Aceptar el aviso de UAC

   IMPORTANTE: El programa REQUIERE privilegios de administrador
      para modificar servicios y el registro de Windows.
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Compilador de {APP_NAME} v{APP_VERSION}"
    )
    parser.add_argument(
        "--onefile", action="store_true", default=True,
        help="Generar ejecutable único (default)"
    )
    parser.add_argument(
        "--onedir", action="store_true",
        help="Generar en directorio (arranque más rápido)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Incluir consola de depuración"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Solo limpiar artefactos anteriores"
    )
    args = parser.parse_args()

    if args.clean:
        clean_previous_build()
        sys.exit(0)

    clean_previous_build()

    one_file_mode = not args.onedir
    build(one_file=one_file_mode, debug=args.debug)
