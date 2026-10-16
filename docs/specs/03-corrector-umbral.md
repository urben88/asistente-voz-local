# Spec 03 — Corrector difuso: umbral estricto (fin de las sustituciones inventadas)

Estado: implementada y aplicada al PC; verificación funcional OK (121 s: 103 → 274 palabras).
Validación: testeador (parseo + JSON + sandbox del merge + aplicación real).
Fecha: 2026-10-16

## Objetivo

Eliminar las sustituciones inventadas del dictado ("dice Docker", "llama"→Ollama, "sucede"→SCADA…).
Causa: el corrector difuso de Handy sustituye palabras normales del español por términos de
`custom_words`. Se mantiene la lista de 42 términos y el modelo Cohere 2B (decisión del usuario);
solo se endurece el umbral `word_correction_threshold`: **0.18 → 0.05**.

## Contexto verificado (código fuente, 2026-10-16)

- `apply_custom_words` (`Handy src-tauri/src/audio_toolkit/text.rs`): por cada palabra/n-grama busca
  el mejor término con Levenshtein normalizado + boost fonético (Soundex inglés ×0.3) y sustituye si
  el score < umbral. Con 0.18 acepta coincidencias fonéticas de hasta ~0.6 de distancia.
- Cohere **no** soporta vocabulario nativo (transcribe.cpp `src/arch/cohere/capabilities.cpp`: solo
  cancelación), así que la lista solo actúa por esta corrección difusa. `supports_vocabulary=false`
  → `apply_custom_words` siempre activo.
- Evidencia real en el PC del usuario (`%APPDATA%\com.pais.handy\history.db`):
  "Es Docker, veo que va muy lento la conexión" ← el usuario dijo "Es decir, veo que…"
  ("decir" → "Docker": Levenshtein 3/6 = 0.5, ×0.3 Soundex = **0.15 < 0.18**).
- Simulación del algoritmo contra las 50.000 palabras más frecuentes del español (hermitdave/FrequencyWords):
  - umbral 0.18 → **209 sustituciones posibles** (decir→Docker, llama→Ollama, sucede→SCADA, copa→CPU,
    probable→PROFIBUS, eterna→Ethernet, profundo→PROFINET, envidia→NVIDIA, influencia→InfluxDB…).
  - umbral 0.05 → **6** (solo: sacada→SCADA*, decker→Docker, usb→USB, linux→Linux, windows→Windows,
    claude→Claude; los 5 últimos son correcciones de mayúsculas deseadas y "decker" no es español).
- `0.18` es el valor por defecto de Handy (`settings.rs: default_word_correction_threshold`), no un
  valor elegido por nosotros.
- `scripts/settings-merge.ps1` (merge compartido por install/patch) hoy fusiona SOLO
  `selected_model`, `custom_words` y `extra_recording_buffer_ms`: hay que añadir el umbral para que
  llegue al PC real.

## Requisitos (ediciones exactas)

R1. `config/handy-settings.json`: cambiar
  `"word_correction_threshold": 0.18` → `"word_correction_threshold": 0.05`.
  No tocar nada más (custom_words sigue con 42 términos).

R2. `scripts/settings-merge.ps1`:
  a. Comentario de cabecera (línea ~4): "copia SOLO selected_model, custom_words y extra_recording_buffer_ms"
     → "copia SOLO selected_model, custom_words, word_correction_threshold y extra_recording_buffer_ms".
  b. Objeto `$res`: añadir campo `UmbralCorrector = 0.0` (tras `Buffer = 0`).
  c. Tras `$esperadoBuffer = $srcFull.settings.extra_recording_buffer_ms`:
     añadir `$esperadoUmbral = $srcFull.settings.word_correction_threshold`.
  d. Tras `$dest.settings.extra_recording_buffer_ms = $esperadoBuffer`:
     añadir `$dest.settings | Add-Member -NotePropertyName word_correction_threshold -NotePropertyValue $esperadoUmbral -Force`
     (no una asignación directa: en PowerShell 5.1 un `PSCustomObject` de `ConvertFrom-Json` no admite
     propiedades nuevas por asignación; `Add-Member -Force` funciona con la clave presente y ausente).
  e. Tras `$res.Buffer = $final.extra_recording_buffer_ms`:
     añadir `$res.UmbralCorrector = $final.word_correction_threshold`.
  f. Salida (Write-Host "Aplicado:"): tras la línea de `extra_recording_buffer_ms`, añadir
     `Write-Host ("  word_correction_threshold : " + $final.word_correction_threshold)`.
  g. Verificación `$ok`: añadir `($res.UmbralCorrector -eq $esperadoUmbral)` al primer grupo (junto a
     ModeloDictado/Palabras/Buffer).
  h. En el bloque "Estado previo" (junto a `$res.ClavesAntes`), añadir
     `$teniaUmbral = $dest.settings.PSObject.Properties.Name -contains "word_correction_threshold"`.
     Y en la guarda del recuento de claves, sustituir `($res.ClavesFinal -eq $res.ClavesAntes)` por
     `($res.ClavesFinal -eq ($res.ClavesAntes + $(if ($teniaUmbral) { 0 } else { 1 })))` (si faltaba la
     clave, añadirla suma exactamente 1; cualquier otra desviación sigue detectándose).
  Nota: con R2.d + R2.h, si la config live no tuviera la clave (Handy antiguo), se añade con 0.05 y la
  verificación pasa igualmente (probado en sandbox).

R3. `scripts/patch-config.ps1` (solo textos):
  a. Cabecera: "Copia SOLO el modelo de dictado, el diccionario (custom_words) y el buffer de
     config\handy-settings.json al Handy de ESTE PC." → "Copia SOLO el modelo de dictado, el diccionario
     (custom_words), el umbral del corrector (word_correction_threshold) y el buffer de
     config\handy-settings.json al Handy de ESTE PC."
  b. "Solo se cambian: modelo de dictado, diccionario y buffer." → "Solo se cambian: modelo de dictado,
     diccionario, umbral del corrector y buffer."

R4. `scripts/install.ps1`: (a) en la simulación del merge (línea ~500), "mergearia selected_model,
  custom_words y extra_recording_buffer_ms" → "mergearia selected_model, custom_words,
  word_correction_threshold y extra_recording_buffer_ms"; y (b) alinear "merge de 3 campos" → "merge de
  4 campos" en las tres menciones restantes (cabecera del camino ~489, resumen de `-Simular` ~577 y
  resumen real ~586). No tocar nada más.

R5. `README.md`:
  a. Tabla del instalador (fila 5): "**merge de 3 campos** (modelo de dictado, diccionario y buffer)"
     → "**merge de 4 campos** (modelo de dictado, diccionario, umbral del corrector y buffer)".
  b. Sección "Opciones avanzadas" (línea ~53): "solo cambia modelo de dictado, diccionario y buffer,
     conservando el resto" → "solo cambia modelo de dictado, diccionario, umbral del corrector y buffer,
     conservando el resto".
  c. Sección "### Diccionario de términos (`custom_words`)" (líneas ~107-113): sustituir por:
     ```
     ### Diccionario de términos (`custom_words`) y corrector difuso

     Lista de términos y su forma exacta (`PLC`, `Modbus`, `SCADA`, `PostgreSQL`, `PowerShell`…)
     definida en `custom_words` dentro de `config/handy-settings.json`.

     Cómo se aplica depende del modelo de dictado:
     - **Modelos con vocabulario nativo** (p. ej. Whisper): la lista se envía al modelo como pista del
       decodificador.
     - **Cohere Transcribe (el actual) no admite la lista**: solo actúa el **corrector difuso** de Handy
       sobre el texto ya transcrito (similitud de edición + fonética). Con el umbral por defecto de Handy
       (`word_correction_threshold = 0.18`) esa corrección resulta *demasiado agresiva en español*:
       sustituye palabras normales por términos del diccionario (p. ej. «decir» → «Docker» o
       «copa» → «CPU»). Por eso aquí queda fijado en **`0.05`**, que solo corrige mayúsculas y erratas
       de una letra (`usb` → `USB`).

     - **Añadir o quitar términos**: Handy → Ajustes → **Advanced → Custom Words**, o editando
       `custom_words` en `config/handy-settings.json` y ejecutando `scripts\patch-config.ps1` (con Handy
       cerrado).
     - **Aviso**: evita términos que choquen con palabras normales del español (`MES` ≈ "mes",
       `RAM` ≈ "rama", `REST` ≈ "resto").
     - **El umbral**, si alguna vez hace falta afinarlo, se edita (`word_correction_threshold`, menor =
       más estricto) en `config/handy-settings.json` y se aplica con `scripts\patch-config.ps1`.
     - **Buffer de audio**: `extra_recording_buffer_ms = 250` graba 250 ms extra al soltar el atajo para
       no cortar la última palabra (el detector de voz VAD descarta ese silencio añadido).
     ```
  d. Tabla "Aplicar esta configuración" (línea ~133): "Copia al Handy real solo `selected_model`,
     `custom_words` y `extra_recording_buffer_ms` del repo" → "Copia al Handy real solo `selected_model`,
     `custom_words`, `word_correction_threshold` y `extra_recording_buffer_ms` del repo".
  e. Estructura (línea ~151): "# PC ya configurado: solo modelo/diccionario/buffer" →
     "# PC ya configurado: solo modelo/diccionario/umbral/buffer".
  f. Solución de problemas (línea ~163): sustituir la entrada por estas dos:
     ```
     - **Las palabras raras siguen saliendo mal**: añade esa palabra al diccionario (Handy → Ajustes →
       Advanced → Custom Words, o `custom_words` en `config/handy-settings.json` + `patch-config.ps1`).
       Con Cohere el diccionario solo corrige erratas leves (umbral estricto, ver *Diccionario de términos*).
     - **Aparece un término técnico en medio de una frase que no lo pedía**: es el corrector difuso. Aquí
       ya va con umbral estricto (`0.05`); si aun así ocurre, quita ese término del diccionario y avísalo.
     ```

R6. NO tocar: `docs/specs/01-*.md` y `02-*.md` (registro histórico), `apply-config.ps1` (copia completa,
  ya arrastra el umbral), `prompts/`, `Instalar.cmd`.

R7. Aplicar a la máquina actual (requiere Handy CERRADO; comprobar `Get-Process handy`):
  - Ejecutar `scripts\patch-config.ps1` real (crea `.bak`).
  - Verificar el JSON live: `word_correction_threshold` = 0.05; `selected_microphone`,
    `post_process_prompts` (4) y el número de claves intactos; `custom_words` = 42; `selected_model` = Cohere.

## Criterios de aceptación

- [ ] `config/handy-settings.json` parsea como JSON y tiene `word_correction_threshold = 0.05`,
      `custom_words` (42) y `selected_model` sin cambios.
- [ ] Los 3 `.ps1` pasan `[System.Management.Automation.Language.Parser]::ParseFile` sin errores.
- [ ] Sandbox del merge (`settings-merge.ps1` con ficheros copiados en carpeta temporal):
      (a) con la config live actual (umbral 0.18) → queda 0.05 y se conservan micrófono, prompts y
      número de claves; (b) con una config sin la clave (simulando Handy viejo) → se añade y verifica;
      (c) acentos del micrófono/prompts intactos (UTF-8 sin BOM).
- [ ] `install.ps1 -Simular` real termina sin errores y muestra el texto actualizado del merge.
- [ ] Tras aplicar en el PC (Handy cerrado): JSON live con 0.05 + `.bak` presente + resto intacto.
- [ ] (Opcional) re-ejecutar la simulación de colisiones (script node en
      `%LOCALAPPDATA%\Temp\opencode\scan_corrector.js`, umbrales 0.06/0.05) → salida ≤ 6 sustituciones.

## Fuera de alcance

- Cambiar el modelo (Cohere 2B se mantiene; el corrector era la causa, no el modelo).
- Podar `custom_words` (se mantiene la lista; el usuario puede quitarla del todo si prefiere).
- Cambiar el corrector de Handy (es código de terceros; solo usamos su umbral).

## Dudas abiertas

- Residual mínimo e inevitable: "sacada" → "SCADA" (y variantes de caja tipo `usb`→`USB`). Se acepta;
  si molesta, quitar "SCADA" de la lista en una futura spec.
