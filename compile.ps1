Set-Location "C:\Users\willy\optimizador windows 2"

# Configurar entorno Python correctamente
$env:PYTHONHOME = "C:\Users\willy\AppData\Local\Programs\Python\Python314"
$env:PYTHONPATH = "C:\Users\willy\AppData\Local\Programs\Python\Python314\Lib;C:\Users\willy\AppData\Local\Programs\Python\Python314\Lib\site-packages"
$python = "C:\Python314\python.exe"

Write-Host "[build] Python: $python"
Write-Host "[build] PYTHONHOME: $env:PYTHONHOME"
Write-Host "[build] Iniciando compilacion..."

& $python build.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Build exitoso"
} else {
    Write-Host "[ERROR] Build fallo con codigo $LASTEXITCODE"
    exit 1
}
