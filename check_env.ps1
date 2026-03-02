Write-Host "=== Variables de entorno Python ==="
Write-Host "PYTHONHOME: $env:PYTHONHOME"
Write-Host "PYTHONPATH: $env:PYTHONPATH"

Write-Host ""
Write-Host "=== PATH entries con Python ==="
$env:PATH -split ';' | Where-Object { $_ -match 'ython|ython' } | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== python.exe en Python314 AppData ==="
$p = "C:\Users\willy\AppData\Local\Programs\Python\Python314"
Get-ChildItem -Path $p -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object FullName

Write-Host ""
Write-Host "=== Versiones disponibles (py --list) ==="
& py --list 2>&1
