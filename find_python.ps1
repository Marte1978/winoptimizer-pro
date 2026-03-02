Write-Host "=== Contenido de Python314 ==="
Get-ChildItem "C:\Users\willy\AppData\Local\Programs\Python\Python314" | Select-Object Name, Length

Write-Host ""
Write-Host "=== python.exe en Roaming ==="
$roaming = "C:\Users\willy\AppData\Roaming"
Get-ChildItem -Path $roaming -Filter "python.exe" -Recurse -Depth 4 -ErrorAction SilentlyContinue | Select-Object FullName

Write-Host ""
Write-Host "=== PyInstaller shebang / python ref ==="
$pi = "C:\Users\willy\AppData\Local\Programs\Python\Python314\Scripts\pyinstaller.exe"
if (Test-Path $pi) {
    $bytes = [System.IO.File]::ReadAllBytes($pi)
    $text = [System.Text.Encoding]::ASCII.GetString($bytes[0..512])
    $text | Select-String "python" | Select-Object -First 5
}
