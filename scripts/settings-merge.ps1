# Merge de configuracion de Handy - Asistente de voz local
# Se carga con dot-source desde install.ps1 y patch-config.ps1 (funcion compartida).
#
# Merge-HandySettings copia SOLO selected_model, custom_words, word_correction_threshold y extra_recording_buffer_ms
# de config\handy-settings.json al settings real de Handy, conservando el resto de claves
# (microfono, atajos, prompts...). Con -EsCopiaCompleta escribe el fichero entero del repo
# (PC nuevo, sin configuracion previa).
#
# Cuidados obligatorios (lo lee Rust/serde_json):
#   - UTF-8 SIN BOM, con File.ReadAllText/WriteAllText (Get-Content -Raw en PowerShell 5.1
#     leeria el fichero como ANSI y corromperia los acentos del microfono y de los prompts).
#   - ConvertTo-Json -Depth 20 (con el -Depth por defecto se trunca el anidamiento).
#   - Copia previa settings_store.json.bak.
#   - Verificacion posterior: mismo microfono, mismos prompts y mismo numero de claves.
#
# El llamador debe comprobar ANTES que Handy esta cerrado (si no, lo reescribe al salir).

function Merge-HandySettings {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepoConfigPath,
        [Parameter(Mandatory = $true)][string]$LiveConfigPath,
        [string]$AsistenteModelo = "",
        [switch]$EsCopiaCompleta
    )

    $utf8 = [System.Text.UTF8Encoding]::new($false)

    $res = [pscustomobject]@{
        Ok              = $false
        CopiaCompleta   = [bool]$EsCopiaCompleta
        Backup          = ""
        ModeloDictado   = ""
        Palabras        = 0
        Buffer          = 0
        UmbralCorrector = 0.0
        MicrofonoAntes  = ""
        MicrofonoFinal  = ""
        PromptsAntes    = 0
        PromptsFinal    = 0
        ClavesAntes     = 0
        ClavesFinal     = 0
        AsistenteModelo = ""
        Error           = ""
    }

    # --- Leer origen y destino ---
    try {
        $srcFull = [System.IO.File]::ReadAllText($RepoConfigPath, $utf8) | ConvertFrom-Json
        if ($EsCopiaCompleta) {
            $dest = $srcFull
        } else {
            if (-not (Test-Path $LiveConfigPath)) {
                $res.Error = "No existe la configuracion de Handy: $LiveConfigPath"
                return $res
            }
            $dest = [System.IO.File]::ReadAllText($LiveConfigPath, $utf8) | ConvertFrom-Json
        }
    } catch {
        $res.Error = "No se pudo leer el JSON: " + $_.Exception.Message
        return $res
    }

    # Valores esperados (los del repo) capturados antes de tocar nada
    $esperadoModelo = $srcFull.settings.selected_model
    $esperadoPalabras = @($srcFull.settings.custom_words).Count
    $esperadoBuffer = $srcFull.settings.extra_recording_buffer_ms
    $esperadoUmbral = $srcFull.settings.word_correction_threshold

    # --- Estado previo + copia de seguridad ---
    $res.MicrofonoAntes = $dest.settings.selected_microphone
    $res.PromptsAntes = @($dest.settings.post_process_prompts).Count
    $res.ClavesAntes = $dest.settings.PSObject.Properties.Name.Count
    $teniaUmbral = $dest.settings.PSObject.Properties.Name -contains "word_correction_threshold"

    if (Test-Path $LiveConfigPath) {
        Copy-Item $LiveConfigPath "$LiveConfigPath.bak" -Force
        $res.Backup = "$LiveConfigPath.bak"
        Write-Host "Copia de seguridad: settings_store.json.bak" -ForegroundColor Green
    }

    # --- Parchear SOLO las claves del repo (y el modelo del asistente si es un PC ligero) ---
    $dest.settings.selected_model = $esperadoModelo
    $dest.settings.custom_words = @($srcFull.settings.custom_words)
    $dest.settings.extra_recording_buffer_ms = $esperadoBuffer
    $dest.settings | Add-Member -NotePropertyName word_correction_threshold -NotePropertyValue $esperadoUmbral -Force
    if ($AsistenteModelo -ne "" -and $AsistenteModelo -ne "gemma4:e4b") {
        $dest.settings.post_process_models.custom = $AsistenteModelo
    }

    $json = $dest | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($LiveConfigPath, $json, $utf8)

    # --- Re-parsear y comprobar ---
    $final = ([System.IO.File]::ReadAllText($LiveConfigPath, $utf8) | ConvertFrom-Json).settings
    $res.ModeloDictado = $final.selected_model
    $res.Palabras = @($final.custom_words).Count
    $res.Buffer = $final.extra_recording_buffer_ms
    $res.UmbralCorrector = $final.word_correction_threshold
    $res.MicrofonoFinal = $final.selected_microphone
    $res.PromptsFinal = @($final.post_process_prompts).Count
    $res.ClavesFinal = $final.PSObject.Properties.Name.Count
    $res.AsistenteModelo = $final.post_process_models.custom

    Write-Host ""
    Write-Host "Aplicado:" -ForegroundColor Green
    Write-Host ("  selected_model            : " + $final.selected_model)
    Write-Host ("  extra_recording_buffer_ms : " + $final.extra_recording_buffer_ms)
    Write-Host ("  word_correction_threshold : " + $final.word_correction_threshold)
    Write-Host ("  custom_words (" + $res.Palabras + "): " + ($final.custom_words -join ", "))
    if ($AsistenteModelo -ne "") {
        Write-Host ("  post_process_models.custom: " + $final.post_process_models.custom)
    }
    if (-not $EsCopiaCompleta) {
        Write-Host "Conservado:" -ForegroundColor Green
        Write-Host ("  selected_microphone       : " + $final.selected_microphone)
        Write-Host ("  post_process_prompts      : " + $res.PromptsFinal + " (antes " + $res.PromptsAntes + ")")
        Write-Host ("  claves de settings        : " + $res.ClavesFinal + " (antes " + $res.ClavesAntes + ")")
    }

    $ok = ($res.ModeloDictado -eq $esperadoModelo) -and
          ($res.Palabras -eq $esperadoPalabras) -and
          ($res.Buffer -eq $esperadoBuffer) -and
          ($res.UmbralCorrector -eq $esperadoUmbral)
    if (-not $EsCopiaCompleta) {
        $ok = $ok -and
              ($res.MicrofonoFinal -eq $res.MicrofonoAntes) -and
              ($res.PromptsFinal -eq $res.PromptsAntes) -and
              ($res.ClavesFinal -eq ($res.ClavesAntes + $(if ($teniaUmbral) { 0 } else { 1 })))
    }
    if ($AsistenteModelo -ne "") {
        $ok = $ok -and ($res.AsistenteModelo -eq $AsistenteModelo)
    }

    if (-not $ok) {
        $res.Error = "El resultado no coincide con lo esperado."
        Write-Warning "Algo mas cambio y no deberia. Restaura settings_store.json.bak si falta algun ajuste."
    }
    $res.Ok = $ok
    return $res
}
