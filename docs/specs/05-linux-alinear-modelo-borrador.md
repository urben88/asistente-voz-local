# Spec 05 — Alinear la parte Linux con el modelo de dictado actual (borrador)

Estado: **borrador, sin implementar** (decisión del usuario 2026-10-16: dejar Linux como está hasta
poder probarlo en esa máquina).
Fecha: 2026-10-16

## Motivo

El `config/handy-settings.json` es **compartido** por Windows y Linux, pero:

- El 2026-10-16 (spec 04) la config pasó a `selected_model = "turbo"` (Whisper Turbo,
  `ggml-large-v3-turbo.bin`) y `custom_words = []` (diccionario vacío), y `README.md`/`install.ps1` de
  Windows descargan ese `.bin`.
- La parte Linux del repo (commits `dc88ad5`, `2ccabb3`, `d560625`, del 15/10) descarga el GGUF de
  **Cohere** (`~/.cache/huggingface/hub/models--handy-computer--cohere-transcribe-03-2026-gguf/`) y
  documenta Cohere como modelo de dictado.

Consecuencia actual en Linux: el `install.sh` descarga Cohere, pero la config compartida pide `turbo`
(un id de modelo local basado en `ggml-large-v3-turbo.bin`); si el `.bin` no está, Handy limpia la
selección y auto-selecciona otro modelo. No rompe, pero no queda el modelo previsto.

## Requisitos propuestos (a validar en una máquina Linux antes de implementar)

- R1. `scripts/install.sh` (Linux): descargar `ggml-large-v3-turbo.bin` a
  `~/.local/share/com.pais.handy/models/` (misma URL `https://blob.handy.computer/ggml-large-v3-turbo.bin`,
  sha256 `1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69`, 1624555275 bytes) en lugar
  del GGUF de Cohere, o bien ofrecer ambos y dejar el `.bin` por defecto.
- R2. `scripts/handy-config.py` y `scripts/patch-config.sh`: nada que cambiar si ya escriben
  `selected_model`, `custom_words`, `word_correction_threshold` y `extra_recording_buffer_ms` desde la
  config compartida; verificar que aceptan `custom_words: []` y el umbral 0.05.
- R3. `README.md` (sección Linux): actualizar la fila "Modelo de dictado" de "Rutas en Linux" y las
  menciones a Cohere, y explicar el porqué (Handy 0.9.8 no trocea el audio; Whisper es el único
  modelo con audio largo nativo).
- R4. Probar en la máquina Linux: dictado corto y dictado largo (2-5 min) con
  `selected_model = "turbo"`; comprobar que el `.bin` se localiza y que Handy lo carga
  (`handy --list-models` equivalente / log).

## Notas

- En Linux, Handy usa por defecto el gestor de atajos de Tauri (`keyboard_implementation: tauri`) —
  detalle ya documentado por su parte; no lo toca esta spec.
- Si la máquina Linux no tiene GPU, medir el rendimiento de Whisper Turbo antes de cambiar el
  modelo por defecto (en la RTX 3070 rinde ~10-14× tiempo real; en CPU puede no servir para dictados
  largos si es más lento que el tiempo real).
