# Spec 07 — Panel de voz (activar/desactivar, idioma y voz) + motor Piper

Estado: aprobada (decisiones del usuario 2026-10-20), pendiente de implementar.
Fecha: 2026-10-20

## Objetivo

Un **panel propio** (Tk + icono en la bandeja) para manejar el lector de voz: encender/apagar,
elegir **idioma (español/inglés)** y **voz/motor**, e instalar voces nuevas. Los atajos de dictado
(`Ctrl+Alt+Espacio`) y lectura (`Ctrl+Alt+R`) **conviven siempre**: el lector usa la CPU y Handy/Ollama
la GPU, así que no compiten. Abre/cierra con `Ctrl+Alt+P` o con el icono de la bandeja.

## Cambio de criterio (2026-10-20, petición del usuario)

La primera versión tenía **modos alternos** (Lectura cerraba Handy + `ollama stop`; Dictado dejaba el
lector inactivo). El usuario pidió **quitar los modos**: quiere dictar y leer **a la vez**, sin
alternar. Por eso:
- `estado.json` solo guarda `lector` (encendido/apagado); el campo `modo` se ignora y se borra al
  escribir.
- El panel **no abre ni cierra Handy ni Ollama**; solo informa de si ocupan GPU.
- Se conservan `handy_en_marcha()`, `ollama_en_uso()` y `gpu_libre()` para la línea de estado.

## Decisiones del usuario (2026-10-20)

- Los dos atajos conviven; nada de modos.
- Motor para el «modelo mejor»: **Piper** (voces es_ES/en_US, CPU, más claro y con pausas).
  Kokoro se conserva como alternativa seleccionable.
- El panel se abre con **icono en la bandeja + atajo `Ctrl+Alt+P`**; cerrar la ventana lo deja en
  la bandeja (no cierra el programa).
- El lector debe **filtrar lo que no se lee** (iconos, emojis, tablas, código, URLs, restos de
  Markdown) y sonar más natural (pausas). Ver spec 08.

## Contexto verificado

- `piper-tts 1.8.0` (wheel `cp39-abi3-win_amd64`): `PiperVoice.load(ruta)`,
  `voz.synthesize(texto, SynthesisConfig(length_scale=...))` → `AudioChunk` con
  `audio_float_array` (float32) y `sample_rate`. Medido en este PC con `es_ES-davefx-medium`:
  carga 3,7 s, **6,5 s de audio en 0,28 s** (25× tiempo real), 22 050 Hz. Kokoro va ~2,5× más
  lento que real, 24 000 Hz.
- Catálogo de voces (`https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json`) y
  descarga con `python -m piper.download_voices --download-dir <dir> <voz>` (crea `<voz>.onnx` +
  `<voz>.onnx.json`, ~60-120 MB).
- `pystray 0.19.5` (necesita Pillow y six; backend win32 por ctypes). Ya instalado en el venv del
  lector junto a `piper-tts`.
- Handy: `%LOCALAPPDATA%\Handy\handy.exe`, proceso `handy.exe`, autostart en
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` («Handy»). Ollama:
  `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`; descargar modelos con `ollama ps` (lista NAME) y
  `ollama stop <modelo>`.
- Handy guarda su configuración al salir: hay que cerrarlo con `taskkill /IM handy.exe` **sin
  `/F`** (WM_CLOSE) y forzar solo si no se va en 5 s.

## Requisitos

R1. **Motor de voz abstraído**: `lector/motor.py` con `cargar_motor(cfg, dir_lector)` que devuelve
   un motor con `.sr`, `.nombre` y `.crear(frase) -> np.ndarray float32 mono`:
   - `PiperMotor`: voces en `<dir_lector>/voces/piper/<voz>.onnx`; `length_scale = 1/velocidad`;
     añade `pausa_ms` (por defecto 120 ms) de silencio al final de cada frase; NaN → 0.
   - `KokoroMotor`: el comportamiento actual (modelo y voces en `<dir_lector>/modelo/`).
   - `lector.py` deja de tener el modelo incrustado y usa `motor.sr` al abrir el `OutputStream`
     (ya no 24 000 fijo).

R2. **`config/lector.json` (nuevo esquema, el panel es su editor y el lector lo relee)**:
   ```json
   {
     "atajo": "ctrl+alt+r",
     "idioma": "es",
     "voces": {
       "es": {"motor": "piper", "voz": "es_ES-davefx-medium"},
       "en": {"motor": "piper", "voz": "en_US-lessac-high"}
     },
     "velocidad": 1.0,
     "pausa_ms": 120,
     "max_caracteres": 20000,
     "kokoro": {"modelo": "kokoro-v1.0.fp16.onnx", "voces": "voices-v1.0.bin"}
   }
   ```
   Compatibilidad: si falta `voces`, se migra del esquema viejo (`voz`, `modelo`, `voces`, `idioma`
   → Kokoro) al cargar. `cargar_config()` no debe romper con el fichero antiguo.

R3. **Recarga en caliente**: el lector comprueba la fecha de `lector.json` antes de cada lectura y
   cada ~0,5 s mientras lee; si cambió, recarga la config y **reinicia el motor** la próxima vez.
   Si el cambio llega leyendo, corta la lectura en el siguiente bloque (la píldora se oculta) y lo
   registra en el log («Configuración nueva: se aplicará en la próxima lectura»).

R4. **Estado compartido** (runtime, no se versiona). Rutas: Windows
   `%LOCALAPPDATA%\asistente-voz-local\`, Linux `${XDG_DATA_HOME:-~/.local/share}/asistente-voz-local/`.
   - `estado.json` (**lo escribe el panel**, atómico: `.tmp` + `os.replace`):
     `{"lector": true|false, "actualizado": <epoch>}`
   - `lector-vivo.json` (**lo escribe el lector** cada 2 s, atómico):
     `{"vivo": <epoch>, "estado": "inactivo"|"preparando"|"leyendo"|"aviso", "motor": "piper",
       "voz": "es_ES-davefx-medium"}`
   - Si `estado.json` no existe, el lector funciona como hasta ahora (encendido).
   - Primera instalación: el instalador crea `{"lector": false}` (nada cargado hasta que se encienda
     el lector desde el panel).
   - El modo `--probar` del lector ignora `estado.json` (sirve para comprobar voces sin panel).
   - Lector: si `lector` es `false` → cierra la aplicación limpiamente (`raíz.quit`/destroy). Sondeo
     cada ~0,5 s desde el hilo de Tk (una comprobación de fecha; sin hilos nuevos por tick).
   - Panel: «lector en marcha» = `lector-vivo.json` con `vivo` de hace menos de 6 s.

R5. **Handy y Ollama: solo lectura** (`panel/control.py`). El panel ya no los abre ni los cierra;
   solo informa (`handy_en_marcha()`, `ollama_en_uso()`, `gpu_libre()`) para la línea de estado.

R6. **Panel** (`panel/panel.py`, `panel/estado.py`, `panel/control.py`, `panel/voces.py`,
   `panel/icono.py`). Ventana Tk ~430×420, tema oscuro como la píldora, sin consola (pythonw):
   - **Lector**: interruptor `Encendido` / `Apagado` (arranca/para el proceso del lector y guarda
     `lector` en `estado.json`). Estado real debajo: `parado`, `leyendo` o `en marcha`.
   - **Idioma**: `Español` / `English` → escribe `idioma` en `lector.json`.
   - **Motor**: `Piper` / `Kokoro` → escribe `voces[idioma].motor`.
   - **Voz**: desplegable con las voces **instaladas** del motor e idioma elegidos (Piper: ficheros
     `voces/piper/*.onnx`; Kokoro: lista curada de su bin). Botón `Instalar voces…` → ventana con
     el catálogo curado (R7) y descarga en segundo plano con progreso y refresco del desplegable.
   - **Ayuda**: botón «?» en cada apartado (Lector, Idioma, Motor, Velocidad, Voz, Estado) que abre
     una ventana con qué es y qué cambia, y tooltip al pasar el ratón; textos en `panel/ayuda.py`
     (`AYUDAS`). Botón **«¿Qué elijo?»** → guía comparativa generada desde `panel/voces.py`
     (`CATALOGO`/`KOKORO_INFO`) con datos medidos (calidad, tamaño, carga, veces más rápido que el
     tiempo real), «La respuesta rápida» al principio y nota sobre la falta de voces `high` de
     España. Línea informativa bajo el desplegable (calidad · acento · MB · velocidad).
   - **Estado GPU**: `GPU libre` / `en uso (Handy)` / `en uso (Ollama: <modelo>)`.
   - Pie: `Ctrl+Alt+R lee · Ctrl+Alt+Espacio dicta · Ctrl+Alt+P abre/cierra`.
   - Botones y desplegables deshabilitados mientras hay una acción en curso; los errores se
     muestran en una línea de estado (nunca un traceback en la cara).
   - Cerrar la ventana (`WM_DELETE_WINDOW`) → `withdraw` a la bandeja. `Salir` (menú de la
     bandeja) termina el panel **sin** tocar Handy ni el lector.
   - Una sola instancia (mutex de Windows / lock en Linux); si ya hay una, sale.

R7. **Catálogo curado de voces Piper** (nombre, idioma, sexo, calidad, tamaño aproximado):
   - Español (por orden de recomendación): `es_MX-claude-high` (hombre, México, 60 MB),
     `es_ES-sharvard-medium` (hombre/mujer, España, 73 MB), `es_ES-davefx-medium` (hombre, España,
     60 MB), `es_AR-daniela-high` (mujer, Argentina, 114 MB).
   - Inglés (por orden de recomendación): `en_US-lessac-high` (mujer, EE. UU., 109 MB),
     `en_US-ryan-high` (hombre, EE. UU., 114 MB), `en_GB-cori-high` (mujer, R. U., 114 MB),
     `en_US-amy-medium` (mujer, EE. UU., 60 MB).
   - Datos medidos en este PC (los usa la guía): carga y veces más rápido que el tiempo real;
     ver `panel/voces.py` (`carga_s`, `rtf`, `calidad`, `acento`, `nota`, `orden`).
   - Descarga: `python -m piper.download_voices --download-dir <dir_lector>/voces/piper <voz>` con
     el mismo intérprete del venv; se comprueba que existen `.onnx` y `.onnx.json`.
   - Voces Kokoro curadas: es → `em_alex`, `ef_dora`, `em_santa`; en → `af_heart`, `am_michael`,
     `af_bella`, `am_onyx`.

R8. **Bandeja + atajo** (`panel/icono.py`, `panel/panel.py`):
   - `pystray` en un hilo; icono generado con Pillow (mismo rosa de la píldora).
   - Clic izquierdo → mostrar ventana. Menú: `Abrir panel`, `Lector: encendido/apagado`, `Salir`.
   - `Ctrl+Alt+P` global (mismo patrón ctypes `RegisterHotKey` + `GetMessageW` en su propio hilo,
     id distinto al del lector). Si el atajo está ocupado, se registra en el log y el panel sigue
     funcionando con la bandeja.

R9. **Arranque**: el instalador pone en Inicio `Panel de voz.lnk` (pythonw base +
   `panel/panel.py`, como el lector) y **elimina** `Lector de voz.lnk` (el panel gestiona el
   lector). Al arrancar, el panel aplica el `estado.json` guardado: si es `lectura`, para Handy y
   Ollama (reintentando 3 veces por si Handy acaba de arrancar por su cuenta) y arranca el lector
   si `lector` es `true`.

R10. **Instalador**: nueva fase **[7/7] Panel de voz** en `scripts/install.ps1` y
   `scripts/install.sh` (idempotente, `-Simular`/`--simular`, se salta con `-SinLector`/
   `--sin-lector` junto con la fase 6): copia `panel/*.py` y `config/panel.json`, instala
   `piper-tts` y `pystray` en el venv existente, crea/reemplaza el acceso directo, arranca el
   panel y resumen final. Renumerar las fases a /7.

R11. **Dependencias**: `lector/requirements.txt` += `piper-tts>=1.8,<2`, `pystray>=0.19,<1`
   (Kokoro, numpy, sounddevice, pillow, onnxruntime ya están).

R12. **Docs**: `README.md` (sección «Panel de voz», tabla de atajos con `Ctrl+Alt+P`, componentes
   con Piper, opciones del instalador) y esta spec.

R13. **Robustez**: ningún fallo de Handy/Ollama/descarga puede tumbar el panel ni el lector; los
   errores van al log (`lector/lector.log` y `panel/panel.log`) y a la línea de estado del panel.
   El lector mantiene las garantías de la spec 06 y del arreglo de la píldora (nunca se queda en
   pantalla).

## Verificación

Verificado en este PC (2026-10-20), salvo lo marcado:

- [x] `piper-tts` y `pystray` importan en el venv 3.12 del lector.
- [x] Con `es_ES-davefx-medium`, una frase se oye clara, con pausa al final y muy por debajo de
      1 s de síntesis (RTF 0,04; la carga inicial de la voz tarda ~3,7 s una sola vez).
- [x] Cambiar idioma y voz en el panel se aplica en la siguiente lectura sin reiniciar el panel
      (recarga en caliente de `lector.json`; probado con `es_ES-davefx-medium` y `en_US-amy-medium`).
- [ ] Cambiar de idioma **mientras lee** corta la lectura y aplica la voz nueva (implementado y
      probado el corte por config; falta la prueba con audio real en curso).
- [x] `Lector: Apagado` cierra el proceso del lector; `Encendido` lo vuelve a arrancar en ≤5 s
      (medido: arranque del proceso en <1 s, voz lista en ~3 s).
- [x] Sin modos (2026-10-20): `estado.json` solo lleva `lector`; el panel ya no abre/cierra Handy
      ni Ollama; `Ctrl+Alt+R` y `Ctrl+Alt+Espacio` conviven (probado dictando y leyendo seguido).
- [x] Cerrar la ventana deja el icono en la bandeja; `Ctrl+Alt+P` se registra (atajo en el log).
- [x] `install.ps1 -Simular` y `install.sh --simular` muestran la fase [7/7] sin errores de parseo;
      `-SinLector`/`--sin-lector` salta las fases 6 y 7.
- [x] Autoarranque real: `Panel de voz.lnk` arranca el panel y este levanta el lector según
      `estado.json`; `Lector de voz.lnk` retirado.
- [ ] Segunda ejecución real del instalador (no duplica accesos directos ni re-descarga la voz).

