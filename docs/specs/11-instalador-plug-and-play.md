# Spec 11 — Instalador plug and play (config de Handy + modelos básicos) y VRAM

Estado: implementada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Que otra persona instale en otro PC y quede **como está este**: misma configuración de Handy,
Whisper Turbo y la voz Piper básica descargados, lector y panel arrancando solos, y todo
funcionando sin tocar nada. Los motores de alta calidad (Chatterbox/XTTS) quedan **opcionales**.

## R1. Configuración de Handy

- `config/handy-settings.json` es la configuración de referencia del repo. Se comprobó contra la
  viva de este PC: **63 claves y solo 4 diferencias**, todas de equipo/arranque.
- Se alinean las de arranque: `autostart_enabled: true` y `start_hidden: true` (Handy arranca solo y
  oculto, como lo tiene el usuario).
- No se versionan datos de equipo ni secretos: `selected_microphone` sigue en `null` (el merge
  conserva el micrófono local) y `post_process_api_keys` no se copia (en este PC hay una clave
  `custom` que no sale del equipo).
- En un PC nuevo, la fase 5 hace copia completa; en uno ya configurado, merge de los 4 campos
  (modelo de dictado, diccionario, umbral y buffer) conservando lo local.

## R2. Modelos básicos automáticos

- Fase 4: `ggml-large-v3-turbo.bin` (Whisper Turbo) con verificación sha256/tamaño.
- Fase 7: voz Piper `es_ES-davefx-medium` (63 MB) solo si falta; `piper-tts` y `pystray` en el venv.
- Los motores de alta calidad **no** se instalan: quedan en `lector/requirements-calidad.txt`
  (~5 GB con `torch`) y se activan a mano si el usuario los quiere.

## R3. Plug and play al primer arranque

- `estado.json` inicial pasa a `{"lector": true}`: el panel arranca, enciende el lector con la voz
  básica y `Ctrl+Alt+R` funciona sin configurar nada.
- Se mantiene: `Panel de voz.lnk` en Inicio, `Lector de voz.lnk` retirado, `lector.json` con Piper
  `es_ES-davefx-medium`, `leer_seleccion: true`, `pausa_ms: 250`.

## R4. VRAM: el dictado no se puede quedar sin tarjeta

Medido en este PC (RTX 3070 8 GB) con Handy y el escritorio en marcha:

| Motor del lector | VRAM usada | Libre | Efecto en el dictado |
|---|---|---|---|
| Piper/Kokoro (CPU) | 0 | ~4,8 GB | Ninguno |
| XTTS (GPU) | ~+1,8 GB (5,5 GB total) | ~2,5 GB | Whisper entra sin problema |
| Chatterbox (GPU) | ~+3,2 GB (7,76 GB total) | **0,26 GB** | Whisper no cabe: dictado lento |

- Con Chatterbox la GPU queda sin memoria: Handy no puede cargar Whisper en GPU y el dictado se
  ralentiza (era la causa de la queja).
- Solución aplicada: el lector queda con **XTTS** (1,8 GB) y Handy con
  `model_unload_timeout: never` (Whisper se queda cargado; no se recarga en cada dictado).
- En el panel, la guía y la ayuda avisan: Chatterbox es la más natural pero deja la GPU justa;
  si se nota lento el dictado, volver a XTTS o a Piper.

## Verificación

- [x] Diff Handy repo vs viva: 63 claves, solo `autostart_enabled`, `start_hidden`,
      `selected_microphone` y secretos distintos.
- [x] `install.ps1 -Simular -NoAbrir` y `bash -n scripts/install.sh` sin errores; fase [7/7] OK.
- [x] `model_unload_timeout: never` persiste tras reiniciar Handy; autostart y start_hidden a true.
- [x] VRAM medida con Chatterbox (0,26 GB libres) y con XTTS (2,5 GB libres).
- [ ] Prueba del usuario: dictar con normalidad ahora (Whisper ya cabe y no se descarga).
- [ ] Prueba en un PC limpio (no hay otro equipo disponible).
