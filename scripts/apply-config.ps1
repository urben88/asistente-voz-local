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

# Modelo de dictado (Cohere Transcribe 2B) en el cache de Hugging Face que lee Handy
$hfRev = "dfa4adebb64f3076b7b6b90b721275cc069cb421"
$hfBase = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--handy-computer--cohere-transcribe-03-2026-gguf"
$hfSnapshots = Join-Path $hfBase "snapshots\$hfRev"
$hfRefs = Join-Path $hfBase "refs"
New-Item -ItemType Directory -Force -Path $hfSnapshots | Out-Null
New-Item -ItemType Directory -Force -Path $hfRefs | Out-Null
$gguf = Join-Path $hfSnapshots "cohere-transcribe-03-2026-Q5_K_M.gguf"
$ggufSha = "14d02f1ad6dd77b3a60f82639879012c3adb4fe25c50a5a47a2c4c661daf1558"
$ggufBytes = 1770270208

if (Test-Path $gguf) {
    $hashOk = (Get-FileHash $gguf -Algorithm SHA256).Hash.ToLower() -eq $ggufSha
    $sizeOk = (Get-Item $gguf).Length -eq $ggufBytes
    if ($hashOk -and $sizeOk) {
        Write-Host "Modelo de dictado ya presente y verificado."
    } else {
        Write-Warning "El modelo presente no coincide (sha256 o tamano). Se descarga de nuevo."
        Remove-Item $gguf -Force
    }
}

if (-not ((Test-Path $gguf) -and ((Get-FileHash $gguf -Algorithm SHA256).Hash.ToLower() -eq $ggufSha))) {
    Write-Host "Descargando modelo de dictado (Cohere Transcribe 2B, ~1,7 GB)..."
    $urls = @(
        "https://huggingface.co/handy-computer/cohere-transcribe-03-2026-gguf/resolve/$hfRev/cohere-transcribe-03-2026-Q5_K_M.gguf",
        "https://blob.handy.computer/handy-computer/cohere-transcribe-03-2026-gguf/$hfRev/cohere-transcribe-03-2026-Q5_K_M.gguf"
    )
    $modeloOk = $false
    for ($i = 0; $i -lt $urls.Count; $i++) {
        $origen = if ($i -eq 0) { "Hugging Face" } else { "mirror (blob.handy.computer)" }
        Write-Host "Descargando desde $origen..."
        curl.exe -L --fail --retry 3 -o $gguf $urls[$i]
        if ($LASTEXITCODE -eq 0 -and (Test-Path $gguf)) {
            $hash = (Get-FileHash $gguf -Algorithm SHA256).Hash.ToLower()
            $bytes = (Get-Item $gguf).Length
            if ($hash -eq $ggufSha -and $bytes -eq $ggufBytes) {
                Write-Host "Modelo de dictado descargado y verificado."
                $modeloOk = $true
                break
            }
            Write-Warning "El archivo descargado no coincide (sha256 o tamano). Se borra y se prueba otro origen."
            Remove-Item $gguf -Force
        } else {
            if (Test-Path $gguf) { Remove-Item $gguf -Force }
            Write-Warning "Fallo la descarga desde este origen."
        }
        if ($i -lt ($urls.Count - 1)) {
            Write-Host "Probando el siguiente origen..."
        }
    }
    if (-not $modeloOk) {
        Write-Warning "No se pudo descargar el modelo de dictado. Revisa tu conexion y repite."
    }
}

if ((Test-Path $gguf) -and ((Get-FileHash $gguf -Algorithm SHA256).Hash.ToLower() -eq $ggufSha)) {
    Set-Content -Path (Join-Path $hfRefs "main") -Value $hfRev -NoNewline -Encoding ascii
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
