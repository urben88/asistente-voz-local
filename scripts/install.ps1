# Instalador - Asistente de voz local (Handy + Ollama)
# Uso: clic derecho sobre este archivo -> "Ejecutar con PowerShell"
#   o:  powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Asistente de voz local - Instalador Windows  " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# --- 1) Handy (dictado por voz) ---
Write-Host "[1/5] Instalando Handy (dictado)..." -ForegroundColor Yellow
winget install --id cjpais.Handy -e --accept-package-agreements --accept-source-agreements

# --- 2) Ollama (IA local) ---
Write-Host "[2/5] Comprobando Ollama (IA local)..." -ForegroundColor Yellow
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    Start-Sleep -Seconds 10
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Warning "No se encontro ollama en el PATH. Cierra esta ventana, abre una nueva y vuelve a ejecutar el instalador."
        exit 1
    }
} else {
    Write-Host "Ollama ya esta instalado."
}

# --- 3) Modelos de IA ---
Write-Host "[3/5] Descargando modelos de IA (varios GB, puede tardar)..." -ForegroundColor Yellow
ollama pull "hf.co/jc-builds/Qwen3.5-9B-Q4_K_M-GGUF:Q4_K_M"
Write-Host "Descargando alternativa rapida (opcional)..."
ollama pull "qwen3:4b-instruct"

# --- 4) Modelo de dictado en vivo (Nemotron para Handy) ---
Write-Host "[4/5] Descargando modelo de dictado (Nemotron Streaming, ~716 MB)..." -ForegroundColor Yellow
$modelsDir = Join-Path $env:APPDATA "com.pais.handy\models"
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
$gguf = Join-Path $modelsDir "nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf"
if (Test-Path $gguf) {
    Write-Host "El modelo de dictado ya esta presente."
} else {
    $url = "https://huggingface.co/handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf/resolve/6d44e540bc31b0de1dbe174a3cea87f53a7f22fb/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf"
    curl.exe -L --fail -o $gguf $url
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Fallo la descarga del modelo de dictado. Vuelve a ejecutar el instalador."
    } else {
        $hash = (Get-FileHash $gguf -Algorithm SHA256).Hash.ToLower()
        if ($hash -ne "b94545b313b3223fda7b2857a52681da813935c2127643d1e9ff0c23d988089c") {
            Write-Warning "El hash del modelo de dictado no coincide. Borra el archivo y repite."
        } else {
            Write-Host "Modelo de dictado descargado y verificado."
        }
    }
}

# --- 5) Configuracion de Handy ---
Write-Host "[5/5] Aplicando configuracion de Handy..." -ForegroundColor Yellow
$cfgDir = Join-Path $env:APPDATA "com.pais.handy"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
$cfg = Join-Path $cfgDir "settings_store.json"
if (Test-Path $cfg) {
    Copy-Item $cfg "$cfg.bak" -Force
    Write-Host "Copia de seguridad del ajuste anterior: settings_store.json.bak"
}
Copy-Item (Join-Path $repoRoot "config\handy-settings.json") $cfg -Force

Write-Host ""
Write-Host "============================ LISTO ============================" -ForegroundColor Green
Write-Host " 1. Abre Handy (menu Inicio) y elige tu microfono en Ajustes."
Write-Host " 2. Ctrl+Alt+Espacio  = dictado normal (texto en vivo)"
Write-Host " 3. Ctrl+Shift+Espacio = asistente IA local (resumen / peticiones)"
Write-Host " La primera respuesta de la IA tarda mas (carga el modelo en GPU)."
Write-Host "===============================================================" -ForegroundColor Green
