# Re-aplicar configuracion - Asistente de voz local
# REEMPLAZA toda la configuracion de Handy (microfono, atajos, prompts...) por la del repo
# y descarga el modelo de dictado si falta.
# Si ya tienes Handy configurado en este PC, es preferible scripts\patch-config.ps1
# (solo cambia modelo de dictado, diccionario y buffer; conserva el resto).
# Requiere Handy CERRADO (bandeja del sistema -> Salir).

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Aplicando configuracion del asistente de voz local..." -ForegroundColor Cyan
Write-Host "OJO: este script REEMPLAZA toda la configuracion de Handy (microfono, atajos, prompts...)." -ForegroundColor Yellow
Write-Host "Si ya tienes Handy configurado en este PC, usa mejor scripts\patch-config.ps1." -ForegroundColor Yellow

# Modelo de dictado (Whisper Turbo) en la carpeta de modelos que lee Handy
$modelosDir = Join-Path $env:APPDATA "com.pais.handy\models"
New-Item -ItemType Directory -Force -Path $modelosDir | Out-Null
$modeloFile = Join-Path $modelosDir "ggml-large-v3-turbo.bin"
$modeloUrl = "https://blob.handy.computer/ggml-large-v3-turbo.bin"
$modeloSha = "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"
$modeloBytes = 1624555275
$modeloOk = $false

if (Test-Path $modeloFile) {
    $hashOk = (Get-FileHash $modeloFile -Algorithm SHA256).Hash.ToLower() -eq $modeloSha
    $sizeOk = (Get-Item $modeloFile).Length -eq $modeloBytes
    if ($hashOk -and $sizeOk) {
        Write-Host "Modelo de dictado ya presente y verificado."
        $modeloOk = $true
    } else {
        Write-Warning "El modelo presente no coincide (sha256 o tamano). Se descarga de nuevo."
        Remove-Item $modeloFile -Force
    }
}

if (-not $modeloOk) {
    Write-Host "Descargando modelo de dictado (Whisper Turbo, ~1,5 GB)..."
    Write-Host "Descargando desde blob.handy.computer..."
    curl.exe -L --fail --retry 3 -o $modeloFile $modeloUrl
    if ($LASTEXITCODE -eq 0 -and (Test-Path $modeloFile)) {
        $hash = (Get-FileHash $modeloFile -Algorithm SHA256).Hash.ToLower()
        $bytes = (Get-Item $modeloFile).Length
        if ($hash -eq $modeloSha -and $bytes -eq $modeloBytes) {
            Write-Host "Modelo de dictado descargado y verificado."
            $modeloOk = $true
        } else {
            Write-Warning "El archivo descargado no coincide (sha256 o tamano). Se borra."
            Remove-Item $modeloFile -Force
        }
    } else {
        if (Test-Path $modeloFile) { Remove-Item $modeloFile -Force }
        Write-Warning "Fallo la descarga desde el origen."
    }
    if (-not $modeloOk) {
        Write-Warning "No se pudo descargar el modelo de dictado. Revisa tu conexion y repite."
    }
}

# Configuracion de Handy
# Handy debe estar cerrado: si esta abierto, al salir reescribe el fichero y perderia el cambio
$proc = Get-Process handy -ErrorAction SilentlyContinue
if ($proc) {
    $pids = ($proc | ForEach-Object { $_.Id }) -join ", "
    Write-Warning "Handy esta en ejecucion (pid $pids). No se ha copiado la configuracion."
    Write-Host "Cierra Handy (icono de bandeja -> Salir) y vuelve a ejecutar este script." -ForegroundColor Yellow
    exit 1
}

$cfgDir = Join-Path $env:APPDATA "com.pais.handy"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$cfg = Join-Path $cfgDir "settings_store.json"
if (Test-Path $cfg) {
    Copy-Item $cfg "$cfg.bak" -Force
    Write-Host "Copia de seguridad de la configuracion anterior: settings_store.json.bak"
}
Copy-Item (Join-Path $repoRoot "config\handy-settings.json") $cfg -Force
Write-Host "Configuracion copiada del repo (reemplaza la anterior)." -ForegroundColor Green

Write-Host "Listo. Reinicia Handy (bandeja del sistema -> salir) y vuelve a abrirlo." -ForegroundColor Green
