# Re-aplicar configuracion - Asistente de voz local
# Descarga el modelo de dictado (si falta) y copia la configuracion de Handy.

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Aplicando configuracion del asistente de voz local..." -ForegroundColor Cyan

# Modelo de dictado
$modelsDir = Join-Path $env:APPDATA "com.pais.handy\models"
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
$gguf = Join-Path $modelsDir "nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf"
if (-not (Test-Path $gguf)) {
    Write-Host "Descargando modelo de dictado (Nemotron Streaming)..."
    $url = "https://huggingface.co/handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf/resolve/6d44e540bc31b0de1dbe174a3cea87f53a7f22fb/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf"
    curl.exe -L --fail -o $gguf $url
}

# Configuracion de Handy
$cfgDir = Join-Path $env:APPDATA "com.pais.handy"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$cfg = Join-Path $cfgDir "settings_store.json"
if (Test-Path $cfg) {
    Copy-Item $cfg "$cfg.bak" -Force
}
Copy-Item (Join-Path $repoRoot "config\handy-settings.json") $cfg -Force

Write-Host "Listo. Reinicia Handy (bandeja del sistema -> salir) y vuelve a abrirlo." -ForegroundColor Green
