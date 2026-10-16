# Parche selectivo de la configuracion - Asistente de voz local
# Copia SOLO el modelo de dictado, el diccionario (custom_words), el umbral del corrector (word_correction_threshold) y el buffer
# de config\handy-settings.json al Handy de ESTE PC.
# Todo lo demas (microfono, atajos, prompts...) se conserva tal cual.
# Requiere Handy CERRADO (bandeja del sistema -> Salir).
#
# Uso: clic derecho sobre este archivo -> "Ejecutar con PowerShell"
#   o:  powershell -ExecutionPolicy Bypass -File .\scripts\patch-config.ps1
# Para un PC nuevo (instalar todo desde cero) usa scripts\install.ps1.

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "==== Parche selectivo de la configuracion de Handy ====" -ForegroundColor Cyan
Write-Host " Solo se cambian: modelo de dictado, diccionario, umbral del corrector y buffer." -ForegroundColor Cyan
Write-Host " El resto de tu configuracion (microfono, atajos, prompts) se conserva." -ForegroundColor Cyan
Write-Host ""

# --- 1) Handy debe estar cerrado: si no, no se toca nada ---
$proc = Get-Process handy -ErrorAction SilentlyContinue
if ($proc) {
    $pids = ($proc | ForEach-Object { $_.Id }) -join ", "
    Write-Warning "Handy esta en ejecucion (pid $pids). NO se ha tocado la configuracion."
    Write-Host " Cierra Handy (icono de bandeja -> Salir) y vuelve a ejecutar este script." -ForegroundColor Yellow
    exit 1
}

# --- 2) Ficheros de origen y destino ---
$srcCfg = Join-Path $repoRoot "config\handy-settings.json"
$cfgDir = Join-Path $env:APPDATA "com.pais.handy"
$cfg = Join-Path $cfgDir "settings_store.json"

# Logica de merge compartida con install.ps1 (UTF-8 sin BOM, -Depth 20, backup y verificacion)
. (Join-Path $PSScriptRoot "settings-merge.ps1")

if (-not (Test-Path $srcCfg)) {
    Write-Warning "No se encuentra la configuracion del repo: $srcCfg"
    exit 1
}
if (-not (Test-Path $cfg)) {
    Write-Warning "No se encuentra la configuracion de Handy: $cfg"
    Write-Host " Este script es para un PC ya configurado. En un PC nuevo usa scripts\install.ps1." -ForegroundColor Yellow
    exit 1
}

# --- 3) Merge selectivo (logica compartida en scripts\settings-merge.ps1) ---
$res = Merge-HandySettings -RepoConfigPath $srcCfg -LiveConfigPath $cfg

if (-not $res.Ok) {
    Write-Warning "No se pudo aplicar el parche: $($res.Error)"
    exit 1
}

Write-Host ""
Write-Host "Listo. Abre Handy y comprueba en Ajustes que el modelo de dictado es el esperado." -ForegroundColor Green
