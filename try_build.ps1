Set-Location "C:\Users\willy\optimizador windows 2"

# Intentar con el python del Windows Apps (Microsoft Store)
$pythonWinApps = "C:\Users\willy\AppData\Local\Microsoft\WindowsApps\python.exe"

Write-Host "=== Test con WindowsApps python ==="
& $pythonWinApps -c "import sys; print(sys.version); import PyInstaller; print('PyInstaller:', PyInstaller.__version__)" 2>&1

Write-Host ""
Write-Host "=== Test con Python314 + PYTHONHOME ==="
$env:PYTHONHOME = "C:\Users\willy\AppData\Local\Programs\Python\Python314"
$env:PYTHONPATH = "C:\Users\willy\AppData\Local\Programs\Python\Python314\Lib;C:\Users\willy\AppData\Local\Programs\Python\Python314\Lib\site-packages"
& "C:\Python314\python.exe" -c "import sys; print(sys.version); import PyInstaller; print('PyInstaller:', PyInstaller.__version__)" 2>&1
