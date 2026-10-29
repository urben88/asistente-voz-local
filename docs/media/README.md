# Medios de la demo

Material visual que se ve en el README. Todo se genera desde este directorio.

| Fichero | Qué es |
|---|---|
| `../demo-asistente-voz.mp4` | Vídeo 960×540, 25 fps, ~40 s, en español: narración con XTTS-v2 («Luis Moray») y subtítulos incrustados. |
| `../demo-asistente-voz.gif` | Bucle corto (~22 s: dictado → resumen) para el README. |
| `../demo-asistente-voz.es.srt` | Los mismos subtítulos aparte: accesibilidad y traducción. |
| `../demo-asistente-voz.png` | Fotograma de portada. |
| `storyboard.json` | **Fuente única**: textos, narración, subtítulo y duración mínima de cada escena. |
| `demo.html` | La maqueta animada (píldora, editor, atajos, panel y cierre). |
| `render-demo.mjs` | Genera el vídeo, el GIF, el `.srt` y el póster. |
| `narrador.py` | Sintetiza la narración de todas las escenas; es la pieza que llama a `lector/motor.py`. |

**No es una captura de pantalla**: es una recreación ilustrativa del flujo real (dictar → transcribir → resumir → leer → panel), hecha para que se entienda de un vistazo y para que quepa en el README. En el README se dice explícitamente.

## La voz: XTTS-v2 («Luis Moray»)

La narración del vídeo sale de **XTTS-v2** con la voz **«Luis Moray»**, idioma `es`, velocidad `1.0`. XTTS **no es un modelo de Ollama**: es un motor de texto a voz del **entorno del lector**, el mismo que usa el asistente al leer en voz alta, y se instala con `lector/requirements-calidad.txt` (paquete `TTS` + `torch`). Ollama solo interviene en el asistente que resume y redacta, no aquí.

La cadena es: `storyboard.json` (bloque `narrador`) → `render-demo.mjs` → `narrador.py` → `lector/motor.py` → XTTS. `narrador.py` carga el modelo **una sola vez** y sintetiza todas las frases de una tacada; el script normaliza después cada pista (recorte de silencios y 44,1 kHz mono) y de ahí salen los tiempos de cada escena.

Si XTTS no está disponible, `render-demo.mjs` avisa y usa **Piper** (`recambio_piper` en el storyboard); si tampoco hay Piper, genera el vídeo mudo. Forzar el motor mudo es `--sin-voz`.

## Regenerar

```bash
node docs/media/demo/render-demo.mjs             # narración con XTTS-v2 («Luis Moray»)
node docs/media/demo/render-demo.mjs --sin-voz   # vídeo mudo, sin narración
```

Necesita, en este PC:

- **El entorno del lector** (el que trae `motor.py`, el motor XTTS y sus dependencias): el intérprete y la carpeta se autodetectan en `%LOCALAPPDATA%\asistente-voz-local\lector` (`.venv\Scripts\python.exe` y `motor.py`) y se pueden forzar con `LECTOR_PYTHON` y `LECTOR_DIR`. `narrador.py` está en este mismo directorio y se ejecuta con ese intérprete. Si falta el entorno, el script avisa con un log y tira del recambio.
- **Chrome o Chromium** para pintar los fotogramas (autodetecta el de Playwright, Chrome o Edge; se puede forzar con `CHROME=/ruta/chrome.exe`).
- **ffmpeg y ffprobe** en el `PATH`, para el H.264 y el GIF. El `.srt` es texto: lo escribe el propio script.
- **piper** con una voz en español, como **recambio** de XTTS, sacado del propio proyecto (`%LOCALAPPDATA%\asistente-voz-local\lector`; se puede forzar con `PIPER_EXE` y `PIPER_VOZ`). La voz de recambio es la del `recambio_piper` del storyboard (`es_ES-davefx-medium`). Sin XTTS ni piper, el script genera el vídeo **mudo** y avisa.

Nada de esto se instala ni se ejecuta al instalar el asistente: es una herramienta de desarrollo.

## Cómo está montado

`demo.html` no usa animaciones CSS ni el reloj del sistema: expone `renderAt(t)`, que pinta el estado exacto del segundo `t`. `render-demo.mjs` recorre los fotogramas a 25 fps, los captura con Chrome por CDP y los pega con ffmpeg. Cada fotograma depende solo de `t`, así que se puede repetir y revisar uno a uno.

- Vista previa de un instante: abre `demo.html?t=17.5` en un navegador.
- Reproducción en bucle: `demo.html?play`.
- Los tiempos salen de `storyboard.json`: cada escena dura lo que dura su narración (mínimo, el `min` de la escena), así que al cambiar un texto solo hay que volver a ejecutar el script. El GIF usa el tramo `gif.desde`–`gif.hasta` (índices de escena) y `gif.offset_desde` para no arrancar en el fundido de entrada.
- El bloque `narrador` de `storyboard.json` elige motor, voz, idioma, velocidad y la voz de recambio de Piper; `render-demo.mjs` registra en el log qué motor y qué voz usó, al empezar y en el resumen final.

## Sustituirlo por una grabación real

Si algún día quieres una captura de pantalla de verdad (con tu micrófono y tu voz):

1. Graba la pantalla con **ScreenToGif** (Windows) o **Peek** (Linux) haciendo los cuatro atajos.
2. Guarda el resultado como `docs/media/demo-asistente-voz.gif` y, si grabas vídeo, como `docs/media/demo-asistente-voz.mp4`.
3. Quita del README la línea que dice que es una recreación ilustrativa.

Mientras no exista esa grabación, estos ficheros son la demo.
