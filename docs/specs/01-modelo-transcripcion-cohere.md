# Spec 01 — Cambiar el modelo de dictado a Cohere Transcribe 2B (y mejoras de precisión)

Estado: implementada (revisión independiente: apto). Pendiente: aplicar el settings live en la
máquina (requiere Handy cerrado) y probar con dictado real.
Fecha: 2026-10-14

## Objetivo

El dictado actual falla palabras ("no pilla bien las palabras"). La causa principal es el modelo:
ahora está seleccionado **Nemotron Streaming 3.5 0.6B** (modelo *streaming* pequeño, 82/100 de
precisión según el catálogo interno de Handy — el más flojo de la lista). Se sustituye por
**Cohere Transcribe 2B Q5_K_M** (92/100, acelerado por GPU, español soportado, PC con RTX 3070)
y se añaden dos mejoras de precisión: **diccionario de términos técnicos** y **buffer de audio
extra** para no cortar la última palabra.

El cambio debe quedar en el repo (instalación reproducible en PC nuevo con los scripts) **y**
aplicado a la máquina actual.

## Contexto verificado (Handy 0.9.8)

- Catálogo interno de Handy (embebido): Cohere Transcribe = 2.0B, precisión 92/100, velocidad 63/100,
  14 idiomas (incluye `es`), **GPU por Vulkan** en Windows. **No detecta idioma automáticamente**:
  exige tener el idioma fijado → ya está `selected_language: "es"`.
- Id exacto del modelo en settings (formato `<repo_id>/<archivo>` del quant por defecto):
  `handy-computer/cohere-transcribe-03-2026-gguf/cohere-transcribe-03-2026-Q5_K_M.gguf`
- Revisión del catálogo: `dfa4adebb64f3076b7b6b90b721275cc069cb421`
- Archivo: `cohere-transcribe-03-2026-Q5_K_M.gguf`
  - bytes: 1770270208 (~1688 MiB)
  - sha256: `14d02f1ad6dd77b3a60f82639879012c3adb4fe25c50a5a47a2c4c661daf1558`
  - URLs (ambas verificadas HTTP 200):
    - HF: `https://huggingface.co/handy-computer/cohere-transcribe-03-2026-gguf/resolve/dfa4adebb64f3076b7b6b90b721275cc069cb421/cohere-transcribe-03-2026-Q5_K_M.gguf`
    - Mirror: `https://blob.handy.computer/handy-computer/cohere-transcribe-03-2026-gguf/dfa4adebb64f3076b7b6b90b721275cc069cb421/cohere-transcribe-03-2026-Q5_K_M.gguf`
- **Cómo descubre Handy los modelos descargados** (código fuente verificado): escanea el cache
  Hugging Face en `%USERPROFILE%\.cache\huggingface\hub\models--<org>--<repo>\`:
  - `refs\main` → fichero de texto con la revisión (el sha de 40 chars)
  - `snapshots\<revisión>\<archivo>.gguf` → el fichero real (sin symlinks; así lo creó Handy para
    Nemotron en esta máquina)
  Con eso lo marca como "descargado" y el id del catálogo queda disponible.
- **Importante**: si `selected_model` apunta a un modelo ausente en disco, Handy limpia la selección
  y auto-selecciona otro modelo al arrancar. Por tanto el modelo debe estar descargado ANTES de
  arrancar Handy con la nueva config.
- `custom_words` en modelos **no-Whisper** (Cohere incluido) aplica solo corrección difusa
  (Levenshtein + Soundex, `word_correction_threshold = 0.18`). **Riesgo**: palabras de la lista que
  coincidan con palabras normales del español (p. ej. `MES` ≈ "mes", `RAM` ≈ "rama", `REST` ≈
  "resto") corromperían texto normal. La lista de abajo evita esas colisiones.
- `extra_recording_buffer_ms`: ms extra de grabación tras soltar el atajo (evita cortar la última
  palabra; el VAD descarta el silencio añadido).
- Con un modelo no-streaming se pierde la vista previa palabra a palabra (el overlay muestra la
  píldora hasta terminar). El texto aparece al acabar la grabación (rápido en GPU). Documentarlo.

## Requisitos

R1. `config/handy-settings.json` (JSON válido, resto de claves intactas):
   - `selected_model` = `handy-computer/cohere-transcribe-03-2026-gguf/cohere-transcribe-03-2026-Q5_K_M.gguf`
   - `extra_recording_buffer_ms` = `250`
   - `custom_words` = lista de exactamente estos términos:
     `["PLC","HMI","SCADA","Modbus","OPC","PROFIBUS","PROFINET","EtherCAT","MQTT","RabbitMQ","Ollama","Docker","Kubernetes","Git","GitHub","GitLab","SQL","PostgreSQL","MySQL","JSON","CSV","PDF","VPN","SSD","USB","GPU","CPU","KPI","API","IoT","RFID","Ethernet","PowerShell","Linux","Ubuntu","Windows","NVIDIA","InfluxDB","Grafana","OpenCode","Handy","Claude"]`
     (NO añadir "MES" ni otras que colisionen con palabras normales en español.)
   - `selected_language` sigue `"es"`; no tocar nada más.

R2. `scripts/install.ps1`: sustituir el paso "[4/5] modelo de dictado (Nemotron)" por la descarga
   del modelo de Cohere con:
   - destino: `%USERPROFILE%\.cache\huggingface\hub\models--handy-computer--cohere-transcribe-03-2026-gguf\snapshots\dfa4adebb64f3076b7b6b90b721275cc069cb421\cohere-transcribe-03-2026-Q5_K_M.gguf`
   - `refs\main` (mismo repo) con el texto `dfa4adebb64f3076b7b6b90b721275cc069cb421`
   - descarga con `curl.exe -L --fail`, primero HF y si falla el mirror; verificación de **sha256 y
     tamaño**; si no coincide: borrar el fichero y avisar (no dejarlo a medias).
   - si ya existe y su sha256 coincide: no re-descargar.
   - mantener el estilo del script (mensajes en español sin tildes, `Write-Host` con colores,
     `$ErrorActionPreference = "Continue"`), y actualizar el texto del paso (numeración "[4/5]",
     GB estimados, ~1,7 GB).
R3. `scripts/apply-config.ps1`: mismo cambio (descarga/verificación del modelo de Cohere si falta,
   con el layout del cache HF) + copia de config como ya hace.
R4. `README.md`:
   - Tabla "Componentes": fila de Handy → modelo `Cohere Transcribe 2B (Q5_K_M, GPU vía Vulkan)`.
   - Sección "Configuración" (o nueva "Modelo de dictado"): cómo cambiar de modelo
     (Handy → Ajustes → Modelos), qué alternativas hay ya disponibles y para qué:
     - `Cohere Transcribe` → máxima precisión (por defecto).
     - `Nemotron Streaming 3.5` → única con **vista previa en vivo** mientras hablas; baja precisión.
     - `Whisper Turbo` → ya está el archivo en el PC (`ggml-large-v3-turbo.bin`), alternativa probada.
     - `Whisper Large v3` (~1 GB) → un poco más preciso que Turbo, más lento.
   - Explicar el **diccionario** (`custom_words`): qué es, cómo añadir/quitar términos
     (Handy → Ajustes → Advanced → Custom Words, o editando `config/handy-settings.json` +
     `apply-config.ps1`), y la advertencia de no meter palabras que choquen con español normal
     (MES, RAM, REST…). Mencionar también `extra_recording_buffer_ms = 250`.
   - Nota sobre la vista previa en vivo (se pierde con modelos no-streaming).
   - Requisitos/instalación: actualizar "~12 GB de disco (modelos incluidos)" si aplica y la
     mención del modelo en el paso 4 del instalador.
   - Troubleshooting: añadir entrada "las palabras raras siguen saliendo mal → añade la palabra al
     diccionario" y "quiero la vista previa en vivo → cambia a Nemotron Streaming en Ajustes".
R5. Aplicar a la máquina actual:
   - Comprobar que Handy NO está en ejecución (`Get-Process handy`). Si estuviera abierto: NO tocar
     el settings live y reportarlo (lo cierra el usuario y se reintenta).
   - Descargar el modelo a la ruta del cache HF de R2 (+ `refs\main`), con verificación sha256/tamaño.
   - Copia previa `settings_store.json` → `settings_store.json.bak` y parchear SOLO
     `selected_model`, `custom_words` y `extra_recording_buffer_ms` del
     `%APPDATA%\com.pais.handy\settings_store.json` **preservando el resto de claves** (edición con
     `ConvertFrom-Json`/`ConvertTo-Json`, no copia del fichero del repo, para no pisar ajustes
     locales del usuario como el micrófono).
     Cuidados obligatorios al reescribir el JSON (lo lee Rust/serde_json):
     - `ConvertTo-Json -Depth 20` (el JSON tiene objetos y arrays anidados; con el `-Depth` por
       defecto se trunca y Handy perdería ajustes).
     - Escribir **UTF-8 sin BOM**: `[System.IO.File]::WriteAllText($cfg, $json, [System.Text.UTF8Encoding]::new($false))`.
       (Un BOM rompe el parseo de serde_json.)
     - Tras escribir, re-parsear el fichero y comprobar que los 3 campos quedan y que, p. ej.,
       `selected_microphone`, `bindings` y `post_process_prompts` siguen presentes (mismo número
       de prompts que antes).
R6. No tocar `prompts/`, `config/` más allá de R1, ni la config del firewall/atajos.

## Criterios de aceptación

- [ ] `config/handy-settings.json` parsea como JSON y contiene los 3 valores de R1.
- [ ] El `.gguf` está en el cache HF (ruta exacta de R2), tamaño 1770270208 bytes y sha256 correcto.
- [ ] `refs\main` contiene la revisión.
- [ ] `%APPDATA%\com.pais.handy\settings_store.json` parcheado (3 campos) + `.bak` creado; parsea
      como JSON y el resto de claves intactas (micrófono, atajos, prompts).
- [ ] `install.ps1` y `apply-config.ps1` pasan el parser de PowerShell sin errores
      (`[System.Management.Automation.Language.Parser]::ParseFile`).
- [ ] README actualizado según R4.
- [ ] Informe final: rutas, comandos usados, hashes verificados y dudas.

## Fuera de alcance

- Cambiar de aplicación (seguimos con Handy).
- Modelos alternativos que no estén ya en el disco o en el catálogo (p. ej. Voxtral, Granite).
- Tocar los prompts de post-proceso o el asistente de Ollama.
- Instalar el modelo en otro PC (lo cubren los scripts).

## Dudas abiertas

- Si al probar Cohere en su voz la precisión no convence, el plan B es `Whisper Turbo` (ya en disco)
  y después `Whisper Large v3`. No requiere cambios de repo.
