# Spec 04 — Dictados largos completos: Whisper Turbo por defecto y diccionario vacío

Estado: implementada y aplicada al PC; verificación funcional OK (audio 121 s: 274 palabras y con
puntuación; sin "decir" → "Docker"). Validación: testeador (parseo + JSON + sandbox del merge +
pruebas CLI en la máquina real).
Fecha: 2026-10-16

## Objetivo

Que un dictado largo (p. ej. media hora) transcriba **todo**. En esta versión de Handy, el audio
largo se manda al modelo en una sola pasada; Cohere (entrenado con fragmentos de ~35 s) pierde
contenido, y el único modelo del catálogo con audio largo nativo es **Whisper** (ya instalado en el
PC). Se pasa a **Whisper Turbo por defecto** y se **vacía `custom_words`** (con Whisper, la lista va
como *prompt* del decodificador: sesga y en las pruebas eliminó la puntuación).

## Contexto verificado (2026-10-16)

- Handy instalado **0.9.8**, motor **transcribe-cpp 0.2.4**. El módulo de troceado
  (`managers/transcription/{chunking,policy,live}.rs`) **no existe** en el tag v0.9.8 y `winget` no
  ofrece nada más nuevo (último instalador: v0.9.8). Sin troceado, cada grabación va al modelo en
  una sola pasada.
- **Prueba A** (audios del propio PC concatenados, 121,4 s; control = suma de los textos
  individuales ≈ 256 palabras): Cohere → **103 palabras** (frases mezcladas); Whisper Turbo →
  **272 palabras** (completo).
- **Prueba B** (dictado real de 15,1 s): Cohere → frases correctas con puntuación; Whisper Turbo →
  contenido correcto pero **sin puntuación ni mayúsculas**. Causa localizada en el código de 0.9.8
  (`managers/transcription.rs`): con `custom_words` no vacío y familia Whisper, Handy manda
  `RunExtension::Whisper { initial_prompt: custom_words.join(", ") }` — los 42 términos sustituyen el
  comportamiento por defecto. Con la lista vacía → `family = None` → prompt por defecto.
- Modelo local `turbo` = "Whisper Turbo" (`ggml-large-v3-turbo.bin`, `is_downloaded: true`):
  bytes **1624555275**, sha256
  **1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69** (idéntico al de
  `https://blob.handy.computer/ggml-large-v3-turbo.bin`, Content-Length 1624555275).
- Catálogo: Whisper Turbo acc 88 / speed 35 / 100 idiomas (es ✓); Cohere acc 92 / speed 63. Solo
  Whisper expone `LONG_FORM` en transcribe.cpp.
- Velocidad medida en este PC: Whisper Turbo ≈ **10x tiempo real** (121 s → 12,4 s), carga en frío
  ~8 s. Con la lista vacía **no** se aplica corrección difusa (adiós "decir" → "Docker").

## Requisitos

R1. `config/handy-settings.json`:
   - `selected_model` = `"turbo"`.
   - `custom_words` = `[]`.
   - Se mantienen `word_correction_threshold: 0.05` (spec 03; inerte con la lista vacía y correcto
     para otros modelos), `selected_language: "es"`, `extra_recording_buffer_ms: 250` y el resto.

R2. `scripts/install.ps1` — Fase 4 (modelo de dictado):
   - Descargar `ggml-large-v3-turbo.bin` a `%APPDATA%\com.pais.handy\models\` desde
     `https://blob.handy.computer/ggml-large-v3-turbo.bin`; verificar **sha256
     `1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69`** y **tamaño 1624555275
     bytes**; si ya existe y coincide, no re-descargar; si no coincide, borrar y avisar.
   - Actualizar textos: "[4/5] Modelo de dictado (Whisper Turbo, ~1,5 GB)", cabecera de la fase y
     simulación (`-Simular`), y el aviso de conectividad de la línea ~205 si menciona el mirror del
     modelo de dictado.
   - El bloque `refs\main` (específico del cache Hugging Face de Cohere) deja de tener sentido:
     eliminarlo (o dejarlo solo como informativo si el directorio existe). El resumen final debe
     comprobar el `.bin` (sha256 + bytes) en lugar del `.gguf` de Cohere.

R3. `scripts/apply-config.ps1`: mismo cambio del bloque de modelo (mismo destino, URL, sha256 y
   tamaño; mismos textos de "Descargando modelo de dictado (Whisper Turbo, ~1,5 GB)").

R4. `README.md`: actualizar todo lo que diga que el dictado usa Cohere:
   - Tabla de componentes y tabla del instalador (fase 4) y pasos de instalación (tamaños).
   - Sección "Modelo de dictado": Whisper Turbo por defecto (ya instalado, `ggml-large-v3-turbo.bin`,
     ~1,5 GB), y por qué: **Handy 0.9.8 no trocea el audio largo**; Cohere recorta contenido en
     dictados largos. Cohere pasa a alternativa ("máxima precisión en frases cortas, a cambio de
     recortar los largos").
   - Sección del diccionario: explicar que `custom_words` está **vacío** a propósito (con Whisper la
     lista se envía como *prompt* del decodificador y sesga la transcripción) y cómo añadir términos
     puntuales si alguno sale mal.
   - Troubleshooting: añadir "dictado largo incompleto → comprueba que el modelo es Whisper" y
     "máxima precisión en frases cortas → cambia a Cohere en Ajustes → Modelos (los dictados largos
     se recortarán)".

R5. NO tocar: `docs/specs/01-*.md`, `02-*.md` y `03-*.md` (histórico), `prompts/`, `Instalar.cmd`,
   `scripts/settings-merge.ps1` (ya fusiona modelo, diccionario, umbral y buffer),
   `scripts/patch-config.ps1` (sus textos ya son genéricos).

R6. Aplicar al PC (requiere **Handy cerrado**): `scripts\patch-config.ps1`; verificar en el JSON live:
   `selected_model = "turbo"`, `custom_words` con 0 elementos, `word_correction_threshold = 0.05`,
   micrófono/prompts/nº de claves intactos y `.bak` creado.

R7. Verificación funcional (CLI, sin micrófono) tras aplicar:
   - Audio largo de prueba (121,4 s; reconstruible concatenando los WAV de `recordings\` como en el
     informe del Cerebro): `handy.exe --transcribe-file <wav> --json` → **≥ 250 palabras** (Cohere
     daba 103) y sin el fallo "decir" → "Docker".
   - Dictado corto (p. ej. 15 s): contenido correcto; comprobar si con la lista vacía recupera
     puntuación y mayúsculas.
   - Pegar ambos textos y recuentos en el informe.

## Criterios de aceptación

- [ ] `config/handy-settings.json` parsea; `selected_model="turbo"`; `custom_words=[]`.
- [ ] Los 3 `.ps1` (`install`, `apply-config`, `settings-merge`) pasan el parser de PowerShell sin
      errores.
- [ ] Sandbox del merge (carpeta temporal): copia de la config live → modelo `turbo`, 0 términos,
      umbral 0.05, resto intacto, `.bak` creado.
- [ ] `install.ps1 -Simular` termina sin errores y muestra el texto actualizado del modelo.
- [ ] Tras aplicar en el PC: JSON live correcto (modelo `turbo`, 0 términos) + `.bak`.
- [ ] Prueba funcional: audio largo ≥ 250 palabras (vs 103 con Cohere); sin "Docker" espurio.
- [ ] README sin referencias obsoletas a Cohere como modelo por defecto.

## Fuera de alcance

- Compilar o instalar una Handy más nueva con troceado (cuando se publique, Cohere volverá a ser
  opción válida para dictados largos).
- Descargar `whisper-large-v3` GGUF (queda documentado como alternativa; ~1 GB, algo más preciso y
  más lento).
- Modificar el código de Handy (es de terceros: solo configuración).

## Dudas abiertas

- Si con la lista vacía la puntuación de Whisper sigue siendo pobre: (a) probar el GGUF de Whisper
  Turbo/Large v3 (ruta nativa GGUF) y/o (b) usar el atajo de asistente (Ctrl+Shift+Espacio) con el
  prompt "Improve Transcriptions" para limpiar puntuación y mayúsculas.
