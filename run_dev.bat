@echo off
:: ================================================================
::  WinOptimizer Pro - Ejecutar en modo desarrollo
::  Requiere Python 3.10+ y dependencias instaladas
:: ================================================================
title WinOptimizer Pro - Dev Mode

echo Iniciando WinOptimizer Pro en modo desarrollo...
echo (Requiere privilegios de administrador)
echo.

:: Verificar si se esta ejecutando como administrador
net session >nul 2>&1
if errorlevel 1 (
    echo [ELEVANDO] Solicitando privilegios de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Ejecutar el programa
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] El programa termino con errores.
    pause
)
