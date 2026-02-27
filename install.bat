@echo off
:: ================================================================
::  WinOptimizer Pro - Instalador de dependencias y compilador
::  Ejecutar como Administrador
:: ================================================================
title WinOptimizer Pro - Instalacion

echo.
echo  ===================================================
echo   WinOptimizer Pro v1.0.0 - Instalacion
echo  ===================================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo        Descarga Python 3.10+ desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Verificando Python...
python --version
echo.

:: Actualizar pip
echo [2/4] Actualizando pip...
python -m pip install --upgrade pip --quiet
echo.

:: Instalar dependencias
echo [3/4] Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)
echo.

:: Compilar ejecutable
echo [4/4] Compilando WinOptimizerPro.exe...
python build.py
if errorlevel 1 (
    echo [ERROR] La compilacion fallo. Revisa el output anterior.
    pause
    exit /b 1
)

echo.
echo  ===================================================
echo   COMPILACION EXITOSA
echo  ===================================================
echo.
echo  El ejecutable se encuentra en:
echo    dist\WinOptimizerPro.exe
echo.
echo  Para ejecutar:
echo    Clic derecho -> "Ejecutar como administrador"
echo.
pause
