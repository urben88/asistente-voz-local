# Instalador - Asistente de voz local (Handy + Ollama)
# Uso recomendado: doble clic en Instalar.cmd (raiz del repo): se auto-eleva con UAC.
#   o:  powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
#
# Opciones:
#   -Simular                   solo comprueba la maquina y explica lo que haria
#                              (no instala, no descarga, no copia y no toca la configuracion)
#   -AsistenteModelo <modelo>  fuerza el modelo de texto del asistente (p. ej. qwen3:4b-instruct)
#   -NoAbrir                   no ofrece abrir Handy al terminar
#   -SinLector                 no instala el lector de voz (fase 6, Kokoro)
#
# Requiere Handy CERRADO (bandeja del sistema -> Salir).

param(
    [switch]$Simular,
    [string]$AsistenteModelo = "",
    [switch]$NoAbrir,
    [switch]$SinLector
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$repoConfig = Join-Path $repoRoot "config\handy-settings.json"
$modeloEstandar = "gemma4:e4b"
$modeloLigero = "qwen3:4b-instruct"
$vramMinima = 8000
$fallos = @()
$avisos = 0

# Logica de merge compartida con patch-config.ps1 (UTF-8 sin BOM, -Depth 20, backup y verificacion)
. (Join-Path $PSScriptRoot "settings-merge.ps1")

# --- Utilidades de salida (estilo del repo: espanol sin tildes, Write-Host con color) ---

function Mostrar-Paso {
    param([string]$Texto)
    Write-Host ""
    Write-Host $Texto -ForegroundColor Yellow
}

function Mostrar-Ok {
    param([string]$Texto)
    Write-Host ("  OK     " + $Texto) -ForegroundColor Green
}

function Mostrar-Aviso {
    param([string]$Texto)
    Write-Host ("  AVISO  " + $Texto) -ForegroundColor Yellow
    $script:avisos++
}

function Mostrar-Fallo {
    param([string]$Texto)
    Write-Host ("  FALLO  " + $Texto) -ForegroundColor Red
    $script:fallos += $Texto
}

function Mostrar-Simulacion {
    param([string]$Texto)
    if ($Simular) { Write-Host ("  SIMULA " + $Texto) -ForegroundColor Cyan }
}

function Mostrar-Dato {
    param([string]$Etiqueta, [string]$Valor, [string]$Color = "Gray")
    Write-Host ("  " + $Etiqueta.PadRight(18) + ": " + $Valor) -ForegroundColor $Color
}

# --- Utilidades de comprobacion ---

function Probar-Puerto {
    param([string]$HostName, [int]$Puerto = 443, [int]$TimeoutMs = 5000)
    $cliente = $null
    try {
        $cliente = New-Object System.Net.Sockets.TcpClient
        $tarea = $cliente.ConnectAsync($HostName, $Puerto)
        return [bool]$tarea.Wait($TimeoutMs)
    } catch {
        return $false
    } finally {
        if ($cliente) { $cliente.Close() }
    }
}

function Probar-Ollama {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Obtener-ModelosOllama {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 5
        return @(($r.Content | ConvertFrom-Json).models | ForEach-Object { $_.name })
    } catch {
        return @()
    }
}

function Tiene-Modelo {
    param([string[]]$Lista, [string]$Modelo)
    foreach ($m in @($Lista)) {
        if ($m -eq $Modelo -or $m -eq ($Modelo + ":latest")) { return $true }
    }
    return $false
}

function Obtener-VramNVidia {
    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { return $null }
    try {
        $salida = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $salida) { return $null }
        $valores = @($salida | ForEach-Object { [int]($_ -replace "[^0-9]", "") } | Where-Object { $_ -gt 0 })
        if ($valores.Count -eq 0) { return $null }
        return [int]($valores | Measure-Object -Maximum).Maximum
    } catch {
        return $null
    }
}

# =====================================================================
#  Cabecera
# =====================================================================

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Asistente de voz local - Instalador Windows  " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
if ($Simular) {
    Write-Host "  MODO SIMULACION: no se instala, no se descarga y no se toca nada" -ForegroundColor Cyan
} else {
    Write-Host "  Instalacion real en este PC" -ForegroundColor Cyan
}

if (-not (Test-Path $repoConfig)) {
    Write-Host ""
    Write-Host "No se encuentra config\handy-settings.json." -ForegroundColor Red
    Write-Host "Ejecuta el instalador desde la carpeta completa del repositorio." -ForegroundColor Yellow
    exit 1
}

# =====================================================================
#  Preflight (nada se instala hasta terminar estas comprobaciones)
# =====================================================================

Mostrar-Paso "[0/6] Comprobaciones previas"

# --- Sistema operativo ---
$verSo = [Environment]::OSVersion.Version
$nombreSo = "Windows (build " + $verSo.Build + ")"
if ($verSo.Build -ge 22000) {
    $nombreSo = "Windows 11 (build " + $verSo.Build + ")"
} elseif ($verSo.Build -ge 10240) {
    $nombreSo = "Windows 10 (build " + $verSo.Build + ")"
}
if ([Environment]::Is64BitOperatingSystem) {
    Mostrar-Ok ("Sistema: " + $nombreSo + ", 64 bits")
} else {
    Mostrar-Aviso ("Sistema: " + $nombreSo + " de 32 bits; se necesita Windows 10/11 de 64 bits")
}

# --- winget ---
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Mostrar-Ok "winget disponible"
} else {
    Write-Host ""
    Write-Host "No se encuentra winget (Administrador de paquetes de Windows)." -ForegroundColor Red
    Write-Host "Instala 'Instalador de aplicaciones' (App Installer) desde Microsoft Store:" -ForegroundColor Yellow
    Write-Host "  https://apps.microsoft.com/detail/9nblggh4nns1" -ForegroundColor Yellow
    Write-Host "Despues, vuelve a ejecutar el instalador." -ForegroundColor Yellow
    exit 1
}

# --- Espacio libre en la unidad del sistema ---
$letraSistema = $env:SystemDrive
$libreGB = $null
try {
    $disco = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$letraSistema'" -ErrorAction Stop
    if ($disco) { $libreGB = [math]::Round($disco.FreeSpace / 1GB, 1) }
} catch {
    $unidad = Get-PSDrive -Name $letraSistema.TrimEnd(":") -ErrorAction SilentlyContinue
    if ($unidad) { $libreGB = [math]::Round($unidad.Free / 1GB, 1) }
}
if ($null -eq $libreGB) {
    Mostrar-Aviso ("No se ha podido comprobar el espacio libre en " + $letraSistema.TrimEnd(":"))
} elseif ($libreGB -lt 20) {
    Mostrar-Aviso ("Quedan solo " + $libreGB + " GB libres en " + $letraSistema.TrimEnd(":") + " (se recomiendan 20 GB)")
    if ($Simular) {
        Mostrar-Simulacion "preguntaria: Continuar de todas formas? (s/n)"
    } else {
        $respuesta = Read-Host "Continuar de todas formas? (s/n)"
        if ($respuesta -notmatch "^(s|si)$") {
            Write-Host "Instalacion cancelada por falta de espacio." -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Mostrar-Ok ("Espacio libre en " + $letraSistema.TrimEnd(":") + ": " + $libreGB + " GB")
}

# --- Conectividad basica (avisa, no bloquea) ---
$netModelo = Probar-Puerto -HostName "blob.handy.computer"
$netOllama = Probar-Puerto -HostName "ollama.com"
if ($netModelo) { Mostrar-Ok "Conectividad: blob.handy.computer accesible" }
else { Mostrar-Aviso "No se puede acceder a blob.handy.computer (no se podra descargar el modelo de dictado)" }
if ($netOllama) { Mostrar-Ok "Conectividad: ollama.com accesible" }
else { Mostrar-Aviso "No se puede acceder a ollama.com (no se podran descargar los modelos del asistente)" }

if (-not $SinLector) {
    $netGithub = Probar-Puerto -HostName "github.com"
    if ($netGithub) { Mostrar-Ok "Conectividad: github.com accesible" }
    else { Mostrar-Aviso "No se puede acceder a github.com (no se podra descargar el modelo del lector de voz)" }
} else {
    $netGithub = $false
}

# --- Handy NO en ejecucion ---
$procHandy = Get-Process handy -ErrorAction SilentlyContinue
if ($procHandy) {
    $pidsHandy = ($procHandy | ForEach-Object { $_.Id }) -join ", "
    Write-Host ""
    Write-Host ("Handy esta ABIERTO (pid " + $pidsHandy + ").") -ForegroundColor Red
    Write-Host "Hay que cerrarlo antes de instalar, porque Handy reescribe su configuracion al salir:" -ForegroundColor Yellow
    Write-Host "  icono de Handy en la bandeja del sistema (junto al reloj) -> clic derecho -> Salir" -ForegroundColor Yellow
    Write-Host "Despues, vuelve a ejecutar el instalador." -ForegroundColor Yellow
    if ($Simular) {
        Mostrar-Simulacion "se detendria aqui (codigo 1) porque Handy esta abierto"
    } else {
        exit 1
    }
} else {
    Mostrar-Ok "Handy no esta en ejecucion"
}

# =====================================================================
#  Eleccion del modelo del asistente
# =====================================================================

Mostrar-Paso "Modelo del asistente (IA de texto)"
$motivoModelo = ""
if ($AsistenteModelo -ne "") {
    $motivoModelo = "forzado con -AsistenteModelo"
} else {
    $vram = Obtener-VramNVidia
    if ($null -eq $vram) {
        $AsistenteModelo = $modeloLigero
        $motivoModelo = "no se detecta GPU NVIDIA (nvidia-smi)"
    } elseif ($vram -lt $vramMinima) {
        $AsistenteModelo = $modeloLigero
        $motivoModelo = "GPU NVIDIA con " + $vram + " MiB de VRAM (menos de " + $vramMinima + " MiB)"
    } else {
        $AsistenteModelo = $modeloEstandar
        $motivoModelo = "GPU NVIDIA con " + $vram + " MiB de VRAM (" + $vramMinima + " MiB o mas)"
    }
}
Write-Host ("  Modelo elegido: " + $AsistenteModelo + " (" + $motivoModelo + ")") -ForegroundColor Cyan
$modelosAsistente = @($AsistenteModelo)
if ($AsistenteModelo -ne $modeloLigero) { $modelosAsistente += $modeloLigero }

# =====================================================================
#  Fase 1: Handy
# =====================================================================

Mostrar-Paso "[1/6] Handy (dictado por voz)"
$handyExe = ""
foreach ($candidato in @((Join-Path $env:LOCALAPPDATA "Handy\handy.exe"), (Join-Path $env:ProgramFiles "Handy\handy.exe"))) {
    if (Test-Path $candidato) { $handyExe = $candidato; break }
}
if ($handyExe -eq "") {
    $cmdHandy = Get-Command handy -ErrorAction SilentlyContinue
    if ($cmdHandy) { $handyExe = $cmdHandy.Source }
}
$handyVer = ""
if ($handyExe -ne "") { $handyVer = (Get-Item $handyExe).VersionInfo.ProductVersion }

if ($handyExe -ne "") {
    Mostrar-Ok ("Handy ya instalado: " + $handyVer + "  (" + $handyExe + ")")
    $version = $null
    if ($handyVer) {
        try { $version = [version]($handyVer.Split(" ")[0]) } catch { $version = $null }
    }
    if ($version -and $version -lt [version]"0.9.8") {
        Mostrar-Aviso ("Version antigua (" + $handyVer + "). Actualiza con: winget upgrade cjpais.Handy")
    }
} else {
    Mostrar-Aviso "Handy no esta instalado"
    if ($Simular) {
        Mostrar-Simulacion "instalaria Handy: winget install --id cjpais.Handy -e --accept-package-agreements --accept-source-agreements"
    } else {
        Write-Host "  Instalando Handy con winget..."
        winget install --id cjpais.Handy -e --accept-package-agreements --accept-source-agreements
        Start-Sleep -Seconds 5
        if (Test-Path (Join-Path $env:LOCALAPPDATA "Handy\handy.exe")) {
            $handyExe = Join-Path $env:LOCALAPPDATA "Handy\handy.exe"
            $handyVer = (Get-Item $handyExe).VersionInfo.ProductVersion
            Mostrar-Ok ("Handy instalado: " + $handyVer)
        } else {
            Mostrar-Fallo "Handy no se ha instalado correctamente (revisa el aviso de winget)"
        }
    }
}

# =====================================================================
#  Fase 2: Ollama (instalacion + servidor en marcha)
# =====================================================================

Mostrar-Paso "[2/6] Ollama (IA local)"
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaApp = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe"

if ($ollamaCmd) {
    Mostrar-Ok ("Ollama ya instalado (" + $ollamaCmd.Source + ")")
} else {
    Mostrar-Aviso "Ollama no esta instalado"
    if ($Simular) {
        Mostrar-Simulacion "instalaria Ollama: winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements"
    } else {
        Write-Host "  Instalando Ollama con winget..."
        winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
        Start-Sleep -Seconds 10
        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollamaCmd) {
            Mostrar-Ok ("Ollama instalado (" + $ollamaCmd.Source + ")")
        } else {
            Mostrar-Fallo "Ollama no se ha instalado (si acabas de instalarlo, abre una ventana nueva y repite)"
        }
    }
}

# Servidor de Ollama escuchando en 127.0.0.1:11434
$servidorOllama = Probar-Ollama
if ($servidorOllama) {
    Mostrar-Ok "Servidor de Ollama respondiendo en http://127.0.0.1:11434"
} else {
    Mostrar-Aviso "El servidor de Ollama no responde"
    if ($Simular) {
        Mostrar-Simulacion ("arrancaria el servidor: " + $ollamaApp + " y esperaria hasta 60 s")
    } else {
        if (Test-Path $ollamaApp) {
            Start-Process $ollamaApp
        } elseif ($ollamaCmd) {
            Start-Process $ollamaCmd.Source -ArgumentList "serve" -WindowStyle Hidden
        }
        Write-Host "  Esperando a que arranque el servidor (hasta 60 s)..."
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 2
            if (Probar-Ollama) { $servidorOllama = $true; break }
        }
        if ($servidorOllama) {
            Mostrar-Ok "Servidor de Ollama en marcha"
        } else {
            Mostrar-Aviso "El servidor de Ollama no arranca: abre Ollama (menu Inicio) y repite el instalador"
        }
    }
}

# =====================================================================
#  Fase 3: Modelos del asistente
# =====================================================================

Mostrar-Paso "[3/6] Modelos del asistente (Ollama)"
$modelosPresentes = Obtener-ModelosOllama

foreach ($modelo in $modelosAsistente) {
    if (Tiene-Modelo -Lista $modelosPresentes -Modelo $modelo) {
        Mostrar-Ok ("Modelo presente: " + $modelo)
    } else {
        Mostrar-Aviso ("Modelo ausente: " + $modelo)
        if ($Simular) {
            Mostrar-Simulacion ("descargaria el modelo: ollama pull " + $modelo)
        } else {
            Write-Host ("  Descargando " + $modelo + " (varios GB, puede tardar)...")
            ollama pull $modelo
            if ($LASTEXITCODE -ne 0) {
                Mostrar-Fallo ("No se ha podido descargar " + $modelo)
            } else {
                Mostrar-Ok ("Modelo descargado: " + $modelo)
            }
        }
    }
}

# =====================================================================
#  Fase 4: Modelo de dictado (Whisper Turbo)
# =====================================================================

Mostrar-Paso "[4/6] Modelo de dictado (Whisper Turbo, ~1,5 GB)"
# Handy guarda los modelos de dictado en %APPDATA%\com.pais.handy\models\
$modelosDir = Join-Path $env:APPDATA "com.pais.handy\models"
$modeloFile = Join-Path $modelosDir "ggml-large-v3-turbo.bin"
$modeloUrl = "https://blob.handy.computer/ggml-large-v3-turbo.bin"
$modeloSha = "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"
$modeloBytes = 1624555275
$modeloOk = $false

if (Test-Path $modeloFile) {
    $hashOk = (Get-FileHash $modeloFile -Algorithm SHA256).Hash.ToLower() -eq $modeloSha
    $sizeOk = (Get-Item $modeloFile).Length -eq $modeloBytes
    if ($hashOk -and $sizeOk) {
        Mostrar-Ok "El modelo de dictado ya esta presente y verificado (sha256 y tamano)"
        $modeloOk = $true
    } else {
        Mostrar-Aviso "El modelo presente no coincide (sha256 o tamano)"
        if ($Simular) {
            Mostrar-Simulacion "borraria el archivo y lo descargaria de nuevo"
        } else {
            Remove-Item $modeloFile -Force
        }
    }
} else {
    Mostrar-Aviso "El modelo de dictado todavia no esta descargado"
}

if (-not $modeloOk) {
    if ($Simular) {
        Mostrar-Simulacion "descargaria el .bin (~1,5 GB) de blob.handy.computer; verifica sha256 y tamano"
    } else {
        New-Item -ItemType Directory -Force -Path $modelosDir | Out-Null
        Write-Host "Descargando desde $modeloUrl"
        curl.exe -L --fail --retry 3 -o $modeloFile $modeloUrl
        if ($LASTEXITCODE -eq 0 -and (Test-Path $modeloFile)) {
            $hash = (Get-FileHash $modeloFile -Algorithm SHA256).Hash.ToLower()
            $bytes = (Get-Item $modeloFile).Length
            if ($hash -eq $modeloSha -and $bytes -eq $modeloBytes) {
                Write-Host "Modelo de dictado descargado y verificado."
                $modeloOk = $true
            } else {
                Write-Warning "Descarga incompleta o corrupta. Se borra el archivo."
                Remove-Item $modeloFile -Force
            }
        } else {
            if (Test-Path $modeloFile) { Remove-Item $modeloFile -Force }
            Write-Warning "Fallo la descarga."
        }
        if (-not $modeloOk) {
            Write-Host ""
            Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
            Write-Host " AVISO: NO se ha podido descargar el modelo de dictado." -ForegroundColor Red
            Write-Host " Sin el, Handy arrancara con OTRO modelo seleccionado y el dictado" -ForegroundColor Red
            Write-Host " no tendra la precision esperada. Vuelve a ejecutar el instalador" -ForegroundColor Red
            Write-Host " cuando tengas conexion (esta tarea se puede repetir sin problema)." -ForegroundColor Red
            Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
            Write-Host ""
            Mostrar-Fallo "Modelo de dictado no descargado"
        }
    }
}

# =====================================================================
#  Fase 5: Configuracion de Handy
# =====================================================================

Mostrar-Paso "[5/6] Configuracion de Handy"

# Handy debe estar cerrado: si esta abierto, al salir reescribe el fichero y perderia el cambio
$procHandy = Get-Process handy -ErrorAction SilentlyContinue
if ($procHandy) {
    $pidsHandy = ($procHandy | ForEach-Object { $_.Id }) -join ", "
    Write-Host ("  Handy esta en ejecucion (pid " + $pidsHandy + ").") -ForegroundColor Red
    Write-Host "  Cierra Handy (icono de bandeja -> Salir) y vuelve a ejecutar el instalador." -ForegroundColor Yellow
    if ($Simular) {
        Mostrar-Simulacion "no se tocaria la configuracion (se detendria con codigo 1)"
    } else {
        exit 1
    }
}

$cfgDir = Join-Path $env:APPDATA "com.pais.handy"
$cfg = Join-Path $cfgDir "settings_store.json"
$hayConfig = Test-Path $cfg
if ($hayConfig) {
    Write-Host "  Camino: MERGE de 4 campos (habia configuracion previa: se conserva tu microfono, atajos y prompts)" -ForegroundColor Cyan
} else {
    Write-Host "  Camino: COPIA completa de config\handy-settings.json (no habia configuracion previa)" -ForegroundColor Cyan
}
if ($AsistenteModelo -ne $modeloEstandar) {
    Write-Host ("  PC ligero: se ajustara post_process_models.custom a " + $AsistenteModelo) -ForegroundColor Cyan
}

$resMerge = $null
if ($Simular) {
    if ($hayConfig) {
        Mostrar-Simulacion ("hararia copia de settings_store.json a settings_store.json.bak y mergearia selected_model, custom_words, word_correction_threshold y extra_recording_buffer_ms")
    } else {
        Mostrar-Simulacion ("crearia " + $cfg + " copiando config\handy-settings.json")
    }
    if ($AsistenteModelo -ne $modeloEstandar) {
        Mostrar-Simulacion ("ajustaria post_process_models.custom a " + $AsistenteModelo)
    }
} else {
    New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
    if ($hayConfig) {
        $resMerge = Merge-HandySettings -RepoConfigPath $repoConfig -LiveConfigPath $cfg -AsistenteModelo $AsistenteModelo
    } else {
        $resMerge = Merge-HandySettings -RepoConfigPath $repoConfig -LiveConfigPath $cfg -AsistenteModelo $AsistenteModelo -EsCopiaCompleta
    }
    if ($resMerge.Ok) {
        Mostrar-Ok "Configuracion aplicada en $cfg"
    } else {
        Mostrar-Fallo ("No se ha podido aplicar la configuracion de Handy: " + $resMerge.Error)
    }
}

# =====================================================================
#  Fase 6: Lector de voz (Kokoro)
# =====================================================================

Mostrar-Paso "[6/6] Lector de voz (Kokoro, ~0,7 GB entre modelo y entorno Python)"

$lectorDir = Join-Path $env:LOCALAPPDATA "asistente-voz-local\lector"
$lectorModeloDir = Join-Path $lectorDir "modelo"
$lectorVenv = Join-Path $lectorDir ".venv"
$lectorPy = Join-Path $lectorVenv "Scripts\python.exe"
$lectorPyw = Join-Path $lectorVenv "Scripts\pythonw.exe"
$lectorLnk = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\Lector de voz.lnk"
$lectorRepo = Join-Path $repoRoot "lector"
$lectorUrlBase = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
$lectorArchivos = @(
    @{ Nombre = "kokoro-v1.0.fp16.onnx"; Bytes = 163527961; Sha = "f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96" },
    @{ Nombre = "voices-v1.0.bin"; Bytes = 28214398; Sha = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d" }
)
$lectorModeloOk = $false
$lectorAuto = $false
$lectorVenvOk = $false

function Verificar-ArchivoLector {
    param([string]$Ruta, [long]$Bytes, [string]$Sha)
    if (-not (Test-Path $Ruta)) { return $false }
    if ((Get-Item $Ruta).Length -ne $Bytes) { return $false }
    return ((Get-FileHash $Ruta -Algorithm SHA256).Hash.ToLower() -eq $Sha)
}

function Buscar-Uv {
    $c = Get-Command uv -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($ruta in @((Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\uv.exe"), (Join-Path $env:USERPROFILE ".local\bin\uv.exe"))) {
        if (Test-Path $ruta) { return $ruta }
    }
    return ""
}

function Buscar-ProcesosLector {
    return @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains("lector.py") -and
        $_.CommandLine.IndexOf($lectorDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    })
}

if ($SinLector) {
    Mostrar-Ok "Omitido: -SinLector (no se instala el lector de voz)"
} elseif ($Simular) {
    Mostrar-Simulacion ("pararia el lector si esta en marcha y copiaria lector\*.py y requirements.txt a " + $lectorDir)
    Mostrar-Simulacion ("copiaria config\lector.json solo si no existe ya en " + $lectorDir)
    $uvSim = Buscar-Uv
    if ($uvSim -eq "") { Mostrar-Simulacion "instalaria uv: winget install --id astral-sh.uv -e --accept-package-agreements --accept-source-agreements" }
    else { Mostrar-Ok ("uv disponible (" + $uvSim + ")") }
    if (Test-Path $lectorPy) { Mostrar-Ok "Entorno Python 3.12 ya creado" }
    else { Mostrar-Simulacion ("crearia el entorno: uv venv -p 3.12 " + $lectorVenv) }
    Mostrar-Simulacion "instalaria las dependencias: uv pip install -p <python del entorno> -r requirements.txt"
    foreach ($a in $lectorArchivos) {
        $destino = Join-Path $lectorModeloDir $a.Nombre
        if (Verificar-ArchivoLector -Ruta $destino -Bytes $a.Bytes -Sha $a.Sha) {
            Mostrar-Ok ($a.Nombre + " ya presente y verificado (sha256 y tamano)")
        } else {
            Mostrar-Simulacion ("descargaria " + $a.Nombre + " (" + $a.Bytes + " bytes) de github.com; verifica sha256 y tamano")
        }
    }
    Mostrar-Simulacion ("crearia el autoarranque: " + $lectorLnk)
    Mostrar-Simulacion "arrancaria el lector (sin privilegios de administrador) a traves del acceso directo"
} else {
    # 2. Parar el lector si esta en marcha
    $parados = Buscar-ProcesosLector
    foreach ($p in $parados) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    if ($parados.Count -gt 0) { Mostrar-Ok "Lector en marcha parado (se reiniciara al terminar)" }

    # 3. Copiar archivos (la config solo si no existe: se conservan los cambios del usuario)
    try {
        New-Item -ItemType Directory -Force -Path $lectorModeloDir | Out-Null
        $archivosLector = @(Get-ChildItem -Path $lectorRepo -Filter "*.py" -File | ForEach-Object { $_.Name }) + @("requirements.txt")
        foreach ($f in $archivosLector) {
            Copy-Item (Join-Path $lectorRepo $f) (Join-Path $lectorDir $f) -Force -ErrorAction Stop
        }
        $cfgLectorDestino = Join-Path $lectorDir "lector.json"
        if (-not (Test-Path $cfgLectorDestino)) {
            Copy-Item (Join-Path $repoRoot "config\lector.json") $cfgLectorDestino -ErrorAction Stop
            Mostrar-Ok "Config del lector creada (lector.json)"
        } else {
            Mostrar-Ok "Config del lector conservada (ya existia lector.json)"
        }
        Mostrar-Ok ("Archivos del lector copiados a " + $lectorDir)
    } catch {
        Mostrar-Fallo ("No se han podido copiar los archivos del lector: " + $_.Exception.Message)
    }

    # 4. uv + entorno Python 3.12 (kokoro-onnx exige Python < 3.14)
    $uv = Buscar-Uv
    if ($uv -eq "") {
        Write-Host "  Instalando uv con winget..."
        winget install --id astral-sh.uv -e --accept-package-agreements --accept-source-agreements
        $uv = Buscar-Uv
    }
    if ($uv -eq "") {
        Mostrar-Fallo "No se encuentra uv (instalalo con: winget install astral-sh.uv) y repite el instalador"
    } else {
        Mostrar-Ok ("uv disponible (" + $uv + ")")
        if (-not (Test-Path $lectorPy)) {
            Write-Host "  Creando el entorno Python 3.12 (puede descargar Python)..."
            & $uv venv -p 3.12 $lectorVenv
        }
        if (Test-Path $lectorPy) {
            Write-Host "  Instalando dependencias del lector..."
            & $uv pip install -p $lectorPy -r (Join-Path $lectorDir "requirements.txt")
            if ($LASTEXITCODE -eq 0) {
                Mostrar-Ok "Entorno Python del lector listo"
                $lectorVenvOk = $true
            } else {
                Mostrar-Fallo "No se han podido instalar las dependencias del lector"
            }
        } else {
            Mostrar-Fallo "No se ha podido crear el entorno Python 3.12 del lector"
        }
    }

    # 5. Modelo (2 archivos) con sha256 y tamano
    $lectorModeloOk = $true
    foreach ($a in $lectorArchivos) {
        $destino = Join-Path $lectorModeloDir $a.Nombre
        if (Verificar-ArchivoLector -Ruta $destino -Bytes $a.Bytes -Sha $a.Sha) {
            Mostrar-Ok ($a.Nombre + " ya presente y verificado (sha256 y tamano)")
            continue
        }
        if (Test-Path $destino) {
            Mostrar-Aviso ($a.Nombre + " no coincide (sha256 o tamano): se descarga de nuevo")
            Remove-Item $destino -Force
        }
        Write-Host ("  Descargando " + $a.Nombre + "...")
        curl.exe -L --fail --retry 3 -o $destino ($lectorUrlBase + $a.Nombre)
        if ($LASTEXITCODE -eq 0 -and (Verificar-ArchivoLector -Ruta $destino -Bytes $a.Bytes -Sha $a.Sha)) {
            Mostrar-Ok ($a.Nombre + " descargado y verificado")
        } else {
            if (Test-Path $destino) { Remove-Item $destino -Force }
            Mostrar-Fallo ("No se ha podido descargar " + $a.Nombre + " (repite el instalador con conexion)")
            $lectorModeloOk = $false
        }
    }

    # 6. Autoarranque (acceso directo en la carpeta Inicio)
    if ($lectorVenvOk) {
        try {
            $sh = New-Object -ComObject WScript.Shell
            $lnk = $sh.CreateShortcut($lectorLnk)
            $lnk.TargetPath = $lectorPyw
            $lnk.Arguments = '"' + (Join-Path $lectorDir "lector.py") + '"'
            $lnk.WorkingDirectory = $lectorDir
            $lnk.Description = "Lector de voz local (Kokoro)"
            $lnk.Save()
            $lectorAuto = $true
            Mostrar-Ok "Autoarranque creado (carpeta Inicio de Windows)"
        } catch {
            Mostrar-Fallo ("No se ha podido crear el autoarranque del lector: " + $_.Exception.Message)
        }
    }

    # 7. Arrancarlo a traves de Explorer: asi corre SIN privilegios de administrador
    if ($lectorAuto -and $lectorModeloOk) {
        Start-Process explorer.exe -ArgumentList ('"' + $lectorLnk + '"')
        Start-Sleep -Seconds 8
        if ((Buscar-ProcesosLector).Count -gt 0) {
            Mostrar-Ok "Lector en marcha (atajo Ctrl+Alt+R)"
        } else {
            Mostrar-Aviso ("El lector no parece estar en marcha: mira " + (Join-Path $lectorDir "lector.log"))
        }
    }
}

# =====================================================================
#  Verificacion y resumen final
# =====================================================================

Write-Host ""
Write-Host "========================= RESUMEN =========================" -ForegroundColor Cyan
if ($Simular) {
    Write-Host " (simulacion: este es el estado actual y lo que haria)" -ForegroundColor Cyan
}

# Handy
if ($handyExe -ne "") {
    Mostrar-Dato "Handy" ($handyVer + "  (" + $handyExe + ")") "Green"
} else {
    Mostrar-Dato "Handy" "no instalado" "Red"
}

# Modelo de dictado
if (Test-Path $modeloFile) {
    $hashFin = (Get-FileHash $modeloFile -Algorithm SHA256).Hash.ToLower()
    $bytesFin = (Get-Item $modeloFile).Length
    if ($hashFin -eq $modeloSha -and $bytesFin -eq $modeloBytes) {
        Mostrar-Dato "Modelo de dictado" ("Whisper Turbo presente (" + $bytesFin + " bytes, sha256 correcto)") "Green"
    } else {
        Mostrar-Dato "Modelo de dictado" ("presente pero NO coincide (" + $bytesFin + " bytes, sha256 " + $hashFin + ")") "Red"
    }
} else {
    Mostrar-Dato "Modelo de dictado" "no descargado" "Red"
}

# Ollama
if (Probar-Ollama) {
    Mostrar-Dato "Ollama" "servidor en marcha (http://127.0.0.1:11434)" "Green"
    $modelosFin = Obtener-ModelosOllama
    foreach ($modelo in $modelosAsistente) {
        if (Tiene-Modelo -Lista $modelosFin -Modelo $modelo) {
            Mostrar-Dato ("Modelo " + $modelo) "presente" "Green"
        } else {
            Mostrar-Dato ("Modelo " + $modelo) "AUSENTE" "Red"
        }
    }
} else {
    Mostrar-Dato "Ollama" "instalado pero el servidor no responde" "Yellow"
}

# Lector de voz
if ($SinLector) {
    Mostrar-Dato "Lector de voz" "omitido (-SinLector)"
} else {
    $okModeloLector = $true
    foreach ($a in $lectorArchivos) {
        if (-not (Verificar-ArchivoLector -Ruta (Join-Path $lectorModeloDir $a.Nombre) -Bytes $a.Bytes -Sha $a.Sha)) { $okModeloLector = $false }
    }
    $okAutoLector = Test-Path $lectorLnk
    $colorLector = "Yellow"
    if ($okModeloLector -and $okAutoLector) { $colorLector = "Green" }
    Mostrar-Dato "Lector de voz" ("modelo verificado: " + $(if ($okModeloLector) { "si" } else { "no" }) + " | autoarranque: " + $(if ($okAutoLector) { "si" } else { "no" })) $colorLector
}

# Conexion
Mostrar-Dato "Conexion" ("blob.handy.computer " + $(if ($netModelo) { "OK" } else { "sin respuesta" }) + " | ollama.com " + $(if ($netOllama) { "OK" } else { "sin respuesta" }))

# Configuracion
if ($Simular) {
    if ($hayConfig) {
        Mostrar-Dato "Settings" ("sin tocar (merge de 4 campos en " + $cfg + ")")
    } else {
        Mostrar-Dato "Settings" ("sin tocar (copia completa a " + $cfg + ")")
    }
} elseif ($resMerge -and $resMerge.Ok) {
    Mostrar-Dato "Settings" ("aplicado en " + $cfg) "Green"
    if ($resMerge.CopiaCompleta) {
        Mostrar-Dato "Camino" "copia completa (PC nuevo)"
    } else {
        Mostrar-Dato "Camino" ("merge de 4 campos; microfono conservado: " + $resMerge.MicrofonoFinal)
    }
    Mostrar-Dato "Copia previa" $resMerge.Backup
} else {
    Mostrar-Dato "Settings" "NO aplicado" "Red"
}

# Fallos y avisos
if ($fallos.Count -eq 0) {
    Mostrar-Dato "Fallos" "ninguno" "Green"
} else {
    Mostrar-Dato "Fallos" ($fallos -join " | ") "Red"
}
Mostrar-Dato "Avisos" ([string]$avisos)

Write-Host ""
Write-Host "Siguientes pasos:" -ForegroundColor Cyan
Write-Host " 1. Abre Handy (menu Inicio) y elige tu microfono en Ajustes."
Write-Host " 2. Prueba los tres atajos: Ctrl+Alt+Espacio (dictado), Ctrl+Shift+Espacio (asistente) y Ctrl+Alt+R (lee el portapapeles en voz alta)."
Write-Host " 3. Para cambiar de modelo de dictado: Handy -> Ajustes -> Modelos."
Write-Host " 4. El resto (modelo del asistente, prompts, diccionario): seccion Configuracion del README."

# Abrir Handy al terminar (salvo -Simular o -NoAbrir)
if (-not $Simular -and -not $NoAbrir) {
    Write-Host ""
    Write-Host "Pulsa INTRO para abrir Handy ahora (o Ctrl+C para terminar)." -ForegroundColor Green
    Read-Host | Out-Null
    if (Test-Path $handyExe) {
        Start-Process $handyExe
    } else {
        Write-Host "No se ha encontrado handy.exe para abrirlo." -ForegroundColor Yellow
    }
}

Write-Host ""
if ($fallos.Count -gt 0) {
    Write-Host ("Terminado con " + $fallos.Count + " fallo(s). Revisa los mensajes de arriba.") -ForegroundColor Red
    exit 1
}
if ($Simular) {
    Write-Host "Simulacion terminada. No se ha modificado nada." -ForegroundColor Cyan
} else {
    Write-Host "Instalacion terminada." -ForegroundColor Green
}
exit 0
