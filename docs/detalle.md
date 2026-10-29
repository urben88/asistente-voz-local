# Detalle técnico

[← Volver al README](../README.md)

## Qué modelos instalar

| | 1. Recomendado (ligero) | 2. Calidad (pesado) |
|---|---|---|
| Dictado | Whisper large-v3-turbo q8_0 (~0,9 GB) | Whisper large-v3-turbo (~1,5 GB) |
| Asistente IA | Gemma 4 E2B QAT, contexto 4096 (~3 GB) | `gemma4:e4b` (~7 GB) + `qwen3:4b-instruct` de respaldo (~2,5 GB) |
| Descarga de modelos | ~4 GB | ~11 GB |
| VRAM aproximada | ~3,3 GB (todo cargado siempre) | GPU de 8 GB o más |

Además se descargan Handy (~0,3 GB) y el lector de voz (~1,3 GB entre modelos y entorno Python). El instalador elige el recomendado si no respondes en 15 s. Para no ver la pregunta: `-Modelos recomendado|calidad` en Windows, `--modelos recomendado|calidad` en Linux.

Con git en vez de ZIP: `git clone https://github.com/urben88/asistente-voz-local.git`.

## El panel

Una sola vista: arriba, la **VRAM** usada y el botón **Liberar VRAM** (descarga los modelos de Ollama y cierra Handy). Debajo, tres filas (**Dictado**, **Asistente IA** y **Lector**) con su estado, el modelo en uso y un interruptor para **encender o apagar** cada parte, más un desplegable con lo instalado. Se abre con `Ctrl + Alt + P` o desde el icono de la bandeja del sistema.

## Requisitos (detalle)

- Linux sin GPU NVIDIA: el instalador deja solo el dictado, sin IA. Otras distros: `--metodo appimage`.
- Linux, para el lector: `libportaudio2` y `xclip` (o `xsel`/`wl-paste`); sus atajos globales solo funcionan en **X11**, no en Wayland.
- El vídeo del README es una recreación generada desde [`media/demo/`](media/README.md); subtítulos en [`demo-asistente-voz.es.srt`](media/demo-asistente-voz.es.srt).

## Instalación en Linux (detalle)

Equivalente Linux de `Instalar.cmd`: mismo Handy y Ollama, con los mismos modelos, atajos, prompts y diccionario. Handy se instala con `.deb` (pedirá tu contraseña de `sudo`) o, si no hay permisos de administrador, como **AppImage** en `~/.local/bin/handy`.

Con la opción **recomendada**, además: crea `asistente-gemma4-e2b` (`ollama create` con `config/asistente-gemma4-e2b.Modelfile`) y pone `OLLAMA_KEEP_ALIVE=-1` para que los modelos queden cargados: si Ollama corre como servicio de systemd, crea `/etc/systemd/system/ollama.service.d/keep-alive.conf` (con `sudo`, avisando) y reinicia el servicio; si no, lo escribe en `~/.config/environment.d/ollama-keep-alive.conf` y en `~/.profile`.

### Rutas en Linux

| Qué | Dónde |
|---|---|
| Config de Handy | `~/.local/share/com.pais.handy/settings_store.json` |
| Modelo de dictado | `~/.local/share/com.pais.handy/models/` (`ggml-large-v3-turbo-q8_0.bin` o `ggml-large-v3-turbo.bin`) |
| Servidor de Ollama | `http://127.0.0.1:11434` |

### Opciones (Linux)

```bash
bash scripts/install.sh --simular                    # ver que haria sin tocar nada (no instala ni descarga)
bash scripts/install.sh --solo-dictado               # SOLO transcripcion: sin Ollama ni modelos de IA (alias --sin-ia)
bash scripts/install.sh --modelos recomendado        # sin preguntar: recomendado (ligero, por defecto) o calidad (pesado)
bash scripts/install.sh --modelos calidad
bash scripts/install.sh --modelo qwen3:4b-instruct   # forzar el modelo del asistente (manda sobre --modelos; sin --modelos instala calidad)
bash scripts/install.sh --metodo appimage            # instalar Handy sin sudo (en ~/.local/bin/handy)
bash scripts/install.sh --metodo deb                 # forzar la instalacion del .deb con apt
bash scripts/install.sh --no-abrir                   # no ofrecer abrir Handy al terminar
bash scripts/install.sh --sin-lector                 # no instalar el lector ni el panel (fases 6 y 7)
```

**Sin GPU NVIDIA no hace falta la IA**: si el instalador no detecta `nvidia-smi`, activa automáticamente el **modo solo dictado** (no descarga ni requiere Ollama). Si quieres el asistente en CPU igualmente, pásale `--modelo qwen3:4b-instruct`.

- **PC ya configurado**: `bash scripts/patch-config.sh` (solo cambia modelo de dictado, diccionario y buffer; conserva micrófono, atajos y prompts).
- **Reemplazar toda la config**: `bash scripts/apply-config.sh`.

### Atajos, pegado y permisos en Linux

- **Atajos**: en Linux Handy usa por defecto el gestor de **Tauri** (`keyboard_implementation: tauri`), que **no necesita permisos especiales**; el instalador lo configura así (el valor `handy_keys` del config compartido es el default de Windows y en Linux exigiría leer `/dev/input`).
  Si algún día quieres usar `handy_keys`, añade tu usuario al grupo `input` y reinicia la sesión:
  ```bash
  sudo usermod -aG input $USER
  ```
- **Pegado automático en el cursor**: el instalador deja `paste_method: direct` (Handy teclea el texto en el cursor), el default de Handy en Linux; funciona también en terminales y apps donde `Ctrl+V` no pega. Para ello se apoya en `xdotool` en X11 (el instalador deja `xdotool` en `~/.local/bin` si no está en el sistema). Todo esto se puede cambiar en Handy → Ajustes.

### Requisitos Linux (detalle)

- Distro de 64 bits compatible con `.deb` (Linux Mint, Ubuntu, Debian) o cualquier distro usando `--metodo appimage`. `python3` y `curl` vienen de serie.
- GPU **NVIDIA opcional**: sin ella el instalador activa el modo solo dictado (con `--modelo qwen3:4b-instruct` fuerza la IA en CPU).

## Instalación en Windows (detalle)

`Instalar.cmd` se auto-eleva con UAC (Ollama se instala a nivel de sistema).

### Requisitos Windows

- **Windows 10/11 de 64 bits**.
- **~20 GB libres** en el disco del sistema (mínimo ~15 GB) e internet. El lector de voz añade ~1,3 GB (modelos ~0,6 GB + entorno Python ~0,7 GB).
- GPU **NVIDIA opcional**: acelera el dictado y el asistente. Con la opción calidad y sin GPU suficiente, el instalador elige automáticamente el modelo ligero.

### Qué hace el instalador

| Fase | Qué hace |
|---|---|
| 0. Comprobaciones | SO de 64 bits, `winget`, espacio en disco, conexión y que **Handy esté cerrado** |
| 1. Handy | Lo instala con winget (o muestra la versión si ya está); avisa si es anterior a 0.9.8 |
| 2. Ollama | Lo instala si falta y arranca su servidor local |
| 3. Modelos del asistente | Recomendado: baja el modelo base QAT y crea `asistente-gemma4-e2b` con `config/asistente-gemma4-e2b.Modelfile` (contexto 4096) y pone `OLLAMA_KEEP_ALIVE=-1`. Calidad: descarga `gemma4:e4b` y `qwen3:4b-instruct` |
| 4. Modelo de dictado | Recomendado: `ggml-large-v3-turbo-q8_0.bin` (~0,9 GB, de Hugging Face). Calidad: `ggml-large-v3-turbo.bin` (~1,5 GB). Va a la carpeta de modelos de Handy con verificación de sha256 y tamaño |
| 5. Configuración | PC nuevo: copia la config del repo. PC ya configurado: **merge de 4 campos** (modelo de dictado, diccionario, umbral del corrector y buffer) conservando tu micrófono, atajos y prompts. Con la opción recomendada pone `selected_model` a `ggml-large-v3-turbo-q8_0` y el modelo del asistente a `asistente-gemma4-e2b` |
| 6. Lector de voz | Instala `uv` y un entorno Python 3.12, copia el lector, descarga los modelos Supertonic 3 (~400 MB) y Kokoro (sha256 y tamaño), crea el autoarranque y lo arranca. Se salta con `-SinLector` (junto con la 7) |
| 7. Panel de voz | Instala `piper-tts` y `pystray` en el entorno del lector, copia el panel, descarga la voz `es_ES-davefx-medium` (~63 MB) si falta, crea el autoarranque `Panel de voz.lnk`, **borra el del lector** y arranca el panel. Se salta con `-SinLector` |

**La opción por defecto es la recomendada (ligera)**; la de calidad usa `gemma4:e4b`. Con la de calidad, en PCs sin GPU NVIDIA suficiente (menos de 8 GB de VRAM) el instalador usa y deja configurado automáticamente `qwen3:4b-instruct`.

Al final muestra un **resumen** con la versión instalada, los modelos presentes, el sha256 del modelo de dictado y los siguientes pasos.

### Opciones avanzadas

Desde PowerShell, en la carpeta del repo:

```powershell
# ver que haria sin tocar nada (no instala, no descarga y no copia nada)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Simular

# elegir los modelos sin que pregunte: recomendado (ligero, por defecto) o calidad (pesado)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Modelos recomendado
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Modelos calidad

# forzar el modelo del asistente (manda sobre -Modelos; sin -Modelos instala la opcion calidad)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -AsistenteModelo qwen3:4b-instruct

# no ofrecer abrir Handy al terminar
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -NoAbrir

# no instalar el lector ni el panel de voz (fases 6 y 7)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SinLector
```

`Instalar.cmd` acepta los mismos argumentos: `Instalar.cmd -Simular`.

- **Espacio extra** del lector y el panel: ~0,4 GB (modelo Supertonic, la voz por defecto) + ~0,2 GB (modelo Kokoro) + ~0,7 GB (entorno Python) + 63 MB por cada voz Piper que descargues. Los motores de alta calidad (Chatterbox, XTTS) añaden ~5 GB y solo se instalan si los quieres.

**Plug and play**: el instalador deja el equipo como una instalación ya configurada, sin tocar nada al terminar:
- La **configuración de Handy** del repo (modelo, prompts, atajos, pegado, VAD…), con Handy
  arrancando solo y oculto; en un PC ya configurado solo se mezclan modelo, diccionario, umbral y
  buffer.
- **Whisper Turbo** y la voz **Piper** `es_ES-davefx-medium` descargados y verificados.
- **Panel y lector** en Inicio, con el lector ya encendido (`Ctrl+Alt+R` funciona sin configurar).
- Los motores de alta calidad **no** se instalan por defecto (pesan ~5 GB): están en
  `lector/requirements-calidad.txt` para quien los quiera.
- **Conexión**: las voces Piper se descargan de `huggingface.co`. Sin conexión, el panel arranca igual y puedes instalarlas después con **Instalar voces…**.
- En un PC **ya configurado** usa `scripts\patch-config.ps1`: solo cambia modelo de dictado, diccionario, umbral del corrector y buffer, conservando el resto (ver *Aplicar esta configuración en un PC ya configurado*).
- `scripts\apply-config.ps1` reemplaza **toda** la configuración de Handy por la del repo.

### Si algo falla

- **No tengo `winget`**: instala *Instalador de aplicaciones* (App Installer) desde Microsoft Store y repite.
- **Sin conexión**: el instalador avisa y sigue; la configuración se aplica igual y el modelo de dictado se puede recuperar repitiendo el instalador.
- **"Handy está abierto"**: ciérralo desde la bandeja del sistema (clic derecho → *Salir*) y repite. Handy reescribe su configuración al salir, por eso se exige cerrarlo.
- **El antivirus bloquea** la descarga o la instalación: permite la carpeta del repo (o `powershell`/`curl`) y repite.
- **El panel no abre**: mira `%LOCALAPPDATA%\asistente-voz-local\panel.log`. Si ya había uno abierto, el segundo sale solo: usa el icono de la bandeja.
- **`Ctrl+Alt+P` no responde**: otra app tiene ese atajo; el panel sigue funcionando desde la bandeja (clic izquierdo). Cambia `atajo` en `%LOCALAPPDATA%\asistente-voz-local\panel.json` y reinicia el panel.
- **«No hay voces instaladas: usa Instalar voces…»**: abre **Instalar voces…** en el panel y descarga una del idioma elegido.
- **«La voz en uso no suena»**: el lector queda con aviso (píldora gris); elige una voz instalada en el panel y se recupera.
- **La GPU va cargada**: el panel solo informa; si Handy u Ollama no los estás usando, ciérralos o descarga su modelo desde sus propias apps. El lector nunca usa GPU.
- **Nada se rompe por repetir**: los scripts comprueban cada paso antes de actuar.

## Los cuatro atajos (detalle)

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictado puro**: transcribe lo que dices (el texto aparece al terminar la grabación) y lo pega donde tengas el cursor. |
| `Ctrl + Shift + Espacio` | **Resumen / asistente IA local**: dictas y, al parar, Ollama procesa el texto con el prompt activo (por defecto, resumen). Si es información → resumen; si es una petición ("escríbeme un correo formal sobre...", "explícame X", "hazme una lista de...") → la ejecuta y pega el resultado. |
| `Ctrl + Alt + R` | **Lector de voz**: lee en voz alta **el texto que tengas seleccionado** en la ventana con el foco; si no hay nada seleccionado, el portapapeles. Otra pulsación lo para. Limpia lo que no se debe oír: bloques de código, tablas largas, URLs, HTML, emojis, iconos, flechas y restos de Markdown. Lee con pausas naturales (coma, dos puntos y punto) y convive con el dictado: puedes dictar y leer a la vez. |
| `Ctrl + Alt + P` | **Panel de voz**: abre/cierra el panel (encender/apagar lector, idioma, motor, voz). La X lo deja en la bandeja del sistema. |

`Esc` cancela una grabación en curso.

**El texto generado (dictado o asistente) queda siempre copiado en el portapapeles**, además de pegarse donde tengas el cursor (`Ctrl+V` para reutilizarlo).

## Panel de voz

El **panel de voz** es el centro de control del lector: encendido, idioma, motor y voz. Se abre con el **icono de la bandeja del sistema** (clic izquierdo) o con `Ctrl + Alt + P`. La **X** cierra la ventana pero lo deja en la bandeja; para terminarlo, **Salir** en el menú de la bandeja (no toca Handy ni el lector).

Los atajos **conviven**: `Ctrl + Alt + Espacio` dicta y `Ctrl + Alt + R` lee cuando quieras, sin cambiar nada ni apagar nada. El lector trabaja en CPU y Handy/Ollama en GPU, así que no compiten.

El panel es **una sola vista** con tres filas (**Dictado**, **Asistente IA** y **Lector**): estado, modelo en uso, interruptor encender/apagar y un desplegable con lo instalado. Arriba, la VRAM usada y **Liberar VRAM**. Handy se configura en **Handy → Ajustes**.

**Reparto de memoria** (opción recomendada): la GPU (~3,3 GB) la usan Whisper q8_0 + Gemma 4 E2B (contexto 4096, `OLLAMA_KEEP_ALIVE=-1`, siempre cargados) + el sistema; la voz del lector (Supertonic) va en la RAM y no gasta VRAM.

Detalle del lector:

- **Lector Encendido / Apagado**: arranca o para el proceso del lector. Apagado no consume ni RAM ni CPU; encendido tarda ~4 s en cargar la voz. Un punto de color dice cómo va: verde (listo o leyendo), ámbar (cargando) o gris (parado).
- **Idioma** (Español / English), **Motor** (Supertonic / Piper / Kokoro; Chatterbox y XTTS si los instalas) y **Voz** (solo las voces instaladas del motor y el idioma elegidos).
- **Supertonic 3 (por defecto)**: voz natural en CPU (~550 MB de RAM, 2-3× más rápido que el tiempo real, **0 de VRAM**). 10 voces (`M1`-`M5`, `F1`-`F5`) que hablan español e inglés con la misma voz; es la que deja la GPU libre para el dictado y la IA. Licencia del modelo: OpenRAIL-M. Ver `docs/specs/18-supertonic.md`.
- **Instalar voces…**: abre el modelo Supertonic y el catálogo curado de voces Piper (nombre, descripción y tamaño) y las descarga en segundo plano sin bloquear el panel (60-120 MB cada una).
- **Motores de alta calidad (GPU, opcionales)**: `Chatterbox` (la voz más natural en español; ~3,2 GB de VRAM y genera 1,3× más lento de lo que habla, así que puede hacer pausas) y `XTTS` (58 voces y 17 idiomas; ~1,8 GB de VRAM y 1,6× más rápido que el tiempo real). No se instalan por defecto: pesan ~5 GB con `torch`. Instalación:
  ```powershell
  uv pip install -p "$env:LOCALAPPDATA\asistente-voz-local\lector\.venv\Scripts\python.exe" -r lector\requirements-calidad.txt
  ```
  Después aparecen como `Chatterbox` y `XTTS` en **Motor**.
  **Ojo con la VRAM (8 GB)**: Chatterbox + Handy + el escritorio deja la tarjeta casi sin memoria y
  el dictado se ralentiza; XTTS sí convive con Whisper. Para el día a día, Piper (CPU) no usa GPU.
- **Guía de voces**: guía comparativa con **datos medidos en un PC de pruebas (GPU NVIDIA de 8 GB)** (calidad, tamaño, tiempo de carga y veces más rápido que el tiempo real). Resumen: la más natural en español es `es_MX-claude-high` (acento de México); la mejor de España, `es_ES-sharvard-medium`; en inglés, `en_US-lessac-high`; las más ligeras, `es_ES-davefx-medium` y `en_US-amy-medium`.
- **Bajo el motor** hay una línea que dice dónde corre (CPU o GPU), cuánto gasta y para qué sirve. **«?» en cada apartado**: explicación más larga (también al pasar el ratón por encima).
- **★ en el motor recomendado**: Supertonic, con o sin GPU (spec 18). La voz recomendada de cada motor/idioma también lleva ★ en el desplegable.
- **Fila «Asistente IA»**: **selector de modelo** (todos los de Ollama, con ★ en los recomendados y aviso en los grandes). Al elegir uno, el panel cierra Handy, cambia el modelo y lo reabre (unos segundos); el prompt se sigue configurando en Handy.

**Cómo lee el Markdown**: las **tablas** se anuncian («Tabla de 3 columnas: Pieza, Estado, Notas. 6 filas.») y cada fila se lee con el nombre de su columna («Pieza: Handy; Estado: OK; Notas: Whisper Turbo.»); la columna de índice (`#`, `N`) no se lee y las tablas de más de 10 filas se resumen. Las **casillas** se leen «Hecho: …» / «Pendiente: …», las **citas** empiezan por «Cita: …» y las listas y títulos van como frases, sin leer guiones ni números.

**Selección nativa (sin copiar)**: al pulsar `Ctrl+Alt+R`, el lector pregunta a la app por **UI Automation** (navegadores, editores, Office) y, en **consolas clásicas**, lee la selección del búfer con la API de consola de Windows. Solo si la app no lo expone —o estás dentro de Escritorio remoto— usa un `Ctrl+C` temporal y restaura el portapapeles.

**Mientras carga**: la píldora muestra un aro girando y «Cargando voz… N s» (útil con Chatterbox/XTTS, que tardan 20-30 s). Si pulsas `Ctrl+Alt+R` durante la carga, la píldora avisa y la lectura empieza sola en cuanto la voz está lista. La carga inicial al iniciar sesión es silenciosa: la píldora solo aparece si la pides.
- **Estado**: `GPU libre` o `GPU en uso (Handy / Ollama: modelo)`, y debajo el estado real del lector (`parado`, `leyendo` o `en marcha`).

Los cambios se aplican **al momento**, sin reiniciar el panel. Si cambias idioma o voz **mientras lee**, la lectura actual se corta y la siguiente usa la voz nueva.

Ficheros del panel:

- `panel/`: programa del panel (ventana, bandeja, estado, control del proceso del lector, catálogo de voces e icono).
- `config/panel.json`: atajo y rutas de Handy/Ollama. El instalador lo copia a `%LOCALAPPDATA%\asistente-voz-local\panel.json`, que es el que se usa.
- `%LOCALAPPDATA%\asistente-voz-local\`: `estado.json` (lector encendido o apagado), `lector-vivo.json` (latido del lector) y `panel.log`. La config del lector que edita el panel es `lector\lector.json`. En Linux, `~/.local/share/asistente-voz-local/`.

## Componentes (todo local)

| Pieza | Función | Modelo |
|---|---|---|
| [Handy](https://handy.computer) | Captura de voz + transcripción + pegado | Whisper large-v3-turbo (q8_0 en la opción recomendada; GPU vía Vulkan) |
| [Ollama](https://ollama.com) | Motor de IA de texto local | `asistente-gemma4-e2b` (recomendada) o `gemma4:e4b` (calidad): resúmenes, correos, explicaciones... |
| Supertonic 3 | Lector de voz por defecto (texto a voz, en CPU) | Supertonic 3 (10 voces, español e inglés) |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | Motor alternativo del lector (CPU) | Voces `es_ES` / `en_US` (`es_ES-davefx-medium` se instala siempre) |
| [Chatterbox](https://github.com/resemble-ai/chatterbox) | Motor de voz alternativo, máxima naturalidad (GPU, opcional) | Chatterbox Multilingual (500 M) |
| [XTTS-v2](https://github.com/idiap/coqui-ai-TTS) | Motor de voz alternativo, 58 voces y 17 idiomas (GPU, opcional) | XTTS-v2 |
| [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) | Motor alternativo del lector (se elige en el panel) | Kokoro-82M fp16 (`kokoro-v1.0.fp16.onnx`) |

## Ejemplos de uso con `Ctrl + Shift + Espacio`

- *(información)* "...reunión de ayer: la línea 3 parada, repuesto el jueves 18, coste 2400 euros..." → **resumen** con datos clave.
- *"Escríbeme un correo formal al proveedor para confirmar la entrega del pedido 4821 antes del día 20"* → **correo formal** listo.
- *"Escríbeme un mensaje coloquial para mi compañero recordándole la reunión de mañana"* → **mensaje informal** (como si lo contaras tú).
- *"Explícame qué es una API REST, rápido"* → **explicación breve**.
- *"Genera un script de Python de una calculadora"* → **código en texto plano** (sin ``` y sin caracteres raros).

## Configuración

### Modelo de dictado

El dictado usa **Whisper large-v3-turbo** (`ggml-large-v3-turbo-q8_0.bin`, ~0,9 GB, con la opción recomendada; `ggml-large-v3-turbo.bin`, ~1,5 GB, con calidad): es el único modelo del catálogo de Handy con **audio largo nativo**, así que transcribe completo un dictado largo (media hora, por ejemplo) — medido en un PC de pruebas, unas 10 veces más rápido que el tiempo real con GPU. El archivo se guarda en `%APPDATA%\com.pais.handy\models\` (Linux: `~/.local/share/com.pais.handy/models/`), que es donde Handy busca los modelos descargados.

**Por qué no Cohere**: **Handy 0.9.8 no trocea el audio** (no existe el módulo de fragmentado de versiones posteriores): cada grabación va al modelo en una sola pasada. Cohere Transcribe 2B está entrenado con fragmentos de ~35 s, así que en dictados largos **recorta contenido** (prueba con 121 s de audio: 103 palabras frente a 272 con Whisper Turbo).

Para cambiarlo: **Handy → Ajustes → Modelos**. Alternativas ya disponibles y para qué sirve cada una:

| Modelo | Para qué |
|---|---|
| `Whisper Turbo` | **Por defecto**: dictados largos completos. |
| `Cohere Transcribe` | **Máxima precisión en frases cortas**, a cambio de recortar los dictados largos. |
| `Nemotron Streaming 3.5` | La única con **vista previa en vivo** (ves las palabras mientras hablas); precisión baja. |
| `Whisper Large v3` (~1 GB) | Un poco más preciso que Turbo, pero más lento (se descarga al elegirlo). |

**Vista previa en vivo**: los modelos *streaming* (Nemotron) escriben el texto palabra a palabra mientras hablas. Whisper y Cohere **no** son streaming: durante la grabación solo se ve la píldora de estado y el texto aparece completo al terminar (rápido en GPU). Es el precio de la precisión.

### Diccionario de términos (`custom_words`) y corrector difuso

`custom_words` está **vacío a propósito** en `config/handy-settings.json`. Con los modelos Whisper (el actual) la lista no funciona como diccionario: Handy la envía al modelo como *prompt* del decodificador, lo que **sesga la transcripción** (en las pruebas, la lista de 42 términos llegó a eliminar la puntuación). Con la lista vacía, Whisper usa su comportamiento por defecto.

- **Si alguna palabra sale mal** de forma repetida: añádela al diccionario — Handy → Ajustes → **Advanced → Custom Words**, o editando `custom_words` en `config/handy-settings.json` y ejecutando `scripts\patch-config.ps1` (con Handy cerrado). Añade pocos términos y prueba: todos entran en el *prompt* del decodificador.
- **Aviso**: evita términos que choquen con palabras normales del español (`MES` ≈ "mes",
  `RAM` ≈ "rama", `REST` ≈ "resto").
- **Corrector difuso**: `word_correction_threshold = 0.05` (estricto). Con el umbral por defecto de Handy
  (`0.18`) esa corrección resulta *demasiado agresiva en español*: sustituye palabras normales por
  términos del diccionario (p. ej. «decir» → «Docker» o «copa» → «CPU»). Con `custom_words` vacío el
  corrector no tiene con qué sustituir y el umbral queda inerte; se mantiene en `0.05` por si vuelves a
  añadir términos o cambias a Cohere (que no admite la lista y solo se beneficia de esa corrección
  leve: mayúsculas y erratas de una letra, `usb` → `USB`).
- **Buffer de audio**: `extra_recording_buffer_ms = 250` graba 250 ms extra al soltar el atajo para
  no cortar la última palabra (el detector de voz VAD descarta ese silencio añadido).

### Lector de voz

El lector (`Ctrl + Alt + R`) queda residente en segundo plano y corre en CPU; lo arranca el **panel de voz**, que sí arranca con el inicio de sesión. Se instala en `%LOCALAPPDATA%\asistente-voz-local\lector` (Windows) o `~/.local/share/asistente-voz-local/lector` (Linux).

- **Config**: `lector.json` en esa carpeta; lo edita el **panel de voz** (idioma, motor y voz) y el lector lo relee en caliente, sin reiniciar. Campos: `atajo`, `idioma`, `voces` (motor y voz de cada idioma), `velocidad` (1.0 = normal) y `pausa_ms` (silencio al final de cada frase). Si cambias `atajo` a mano, reinicia el lector. El instalador no sobrescribe tu `lector.json`.
- **Píldora visual**: mientras lee aparece abajo en el centro una píldora con el mismo diseño que la de Handy (gris mientras prepara la voz, rosa con barras que siguen la voz mientras habla). Clic en ella o el atajo otra vez para parar. No roba el foco de la ventana en la que estés.
- **Memoria**: el motor de voz queda siempre cargado entre lecturas, sin GPU: con Kokoro son ~450 MB de RAM; con Piper, la voz (~63 MB en disco) también se mantiene cargada.
- **Log**: `lector.log` en la misma carpeta.
- **Probar sin atajo**: `<carpeta>\.venv\Scripts\python.exe <carpeta>\lector.py --probar "hola"`.
- La calidad del español de Kokoro es limitada: es correcta para escuchar un texto, no una voz de locutor.

### Otros ajustes

- **Atajos**: Handy → Ajustes → Atajos. Haz clic en el atajo y pulsa la combinación nueva.
  (No uses el botón *Reset*: volvería a `Ctrl+Espacio`, que choca con WorkspaceLauncher).
- **Modelo del asistente**: Handy → Ajustes → Post-processing → proveedor `Custom` (Ollama, `http://localhost:11434/v1`).
  Según la opción de modelos que elijas:
  - **Recomendado** → `asistente-gemma4-e2b` (Gemma 4 E2B QAT, contexto 4096); es el que se configura por defecto.
  - **Calidad** → `gemma4:e4b` (mejor calidad) y `qwen3:4b-instruct` de respaldo; en PCs sin GPU NVIDIA suficiente el instalador deja configurado `qwen3:4b-instruct`. También se puede forzar con `-AsistenteModelo qwen3:4b-instruct` (Linux: `--modelo`).
- **Prompts**: en `prompts/` de este repo y en Handy → Post-processing → Prompts.
  El activo es **Asistente inteligente (local)** (decide resumen vs petición y maneja el tono).
  Presets intercambiables: *Correo formal* y *Texto coloquial*.

### Aplicar esta configuración en un PC ya configurado

Ambos scripts requieren **Handy cerrado** (bandeja del sistema → *Salir*): si Handy está en ejecución avisan y no tocan la configuración (al salir, Handy reescribiría el fichero y se perdería el cambio). Los dos usan la misma lógica de merge (`scripts\settings-merge.ps1`): UTF-8 sin BOM, copia previa `.bak`, verificación posterior.

| Script | Qué hace |
|---|---|
| `scripts\patch-config.ps1` | **Recomendado**: parche selectivo. Copia al Handy real solo `selected_model`, `custom_words`, `word_correction_threshold` y `extra_recording_buffer_ms` del repo; conserva tu micrófono, atajos, prompts, etc. Crea copia previa `settings_store.json.bak`. |
| `scripts\apply-config.ps1` | ⚠️ **Reemplaza toda** la configuración de Handy por la del repo (micrófono, atajos y prompts incluidos) y descarga el modelo de dictado si falta. Úsalo solo si quieres dejar Handy exactamente como el repo. |

## Estructura

```
asistente-voz-local/
├── Instalar.cmd                 # Windows: doble clic: instala todo (se auto-eleva con UAC)
├── Instalar.sh                  # Linux: ./Instalar.sh (mismas opciones que install.sh)
├── README.md
├── .gitattributes               # los .sh se guardan siempre con LF
├── config/handy-settings.json   # configuración de Handy lista para aplicar
├── config/asistente-gemma4-e2b.Modelfile  # modelo recomendado del asistente (ollama create)
├── config/lector.json           # configuración del lector (atajo, idioma, motor y voz)
├── config/panel.json            # configuración del panel (atajo y rutas de Handy/Ollama)
├── lector/                      # lector de voz (Supertonic/Piper/Kokoro): lector.py, motor.py, leer_md.py, pildora.py; voces/piper/
├── panel/                       # panel de voz: panel.py, estado.py, control.py, voces.py, icono.py
├── docs/specs/                  # especificaciones de los cambios
├── prompts/                     # textos de los prompts (referencia/edición)
│   ├── asistente.md
│   ├── correo-formal.md
│   └── texto-coloquial.md
└── scripts/
    ├── install.ps1              # Windows: instalador (PC nuevo); -Simular/-Modelos/-AsistenteModelo/-NoAbrir/-SinLector
    ├── settings-merge.ps1       # Windows: merge de config compartido (funciones)
    ├── patch-config.ps1         # Windows: PC ya configurado: solo modelo/diccionario/umbral/buffer
    ├── apply-config.ps1         # Windows: reemplaza toda la configuración de Handy
    ├── install.sh               # Linux: instalador (PC nuevo); --simular/--modelos/--modelo/--solo-dictado/--no-abrir/--metodo/--sin-lector
    ├── comun.sh                 # Linux: funciones y constantes compartidas
    ├── handy-config.py          # Linux: merge de config (equivalente a settings-merge.ps1)
    ├── patch-config.sh          # Linux: PC ya configurado: solo modelo/diccionario/buffer
    └── apply-config.sh          # Linux: reemplaza toda la configuración de Handy
```

## Solución de problemas

- **La IA no responde o da error**: abre Ollama (icono de llama en la bandeja). Debe estar en ejecución.
- **Primera respuesta lenta** (20-40 s): Ollama está cargando el modelo en la GPU. Después responde en 5-15 s.
- **Respuestas más lentas de lo normal**: memoria de la GPU llena (navegador con muchas pestañas, juegos...). Cierra apps pesadas.
- **No aparece el texto**: haz clic en un campo de texto antes de dictar y usa el atajo correcto.
- **Caracteres raros (▁, ```)**: no cambies el asistente a `gemma3n` — tiene un bug conocido que inyecta caracteres de bloque.
- **Historial**: Handy guarda las últimas transcripciones (icono de bandeja → ventana principal).
- **Un dictado largo sale incompleto** (se corta o falta contenido): comprueba que el modelo de dictado
  es **Whisper Turbo** (Handy → Ajustes → Modelos). Handy 0.9.8 no trocea el audio y Cohere Transcribe
  recorta los dictados largos.
- **Quiero la máxima precisión en frases cortas**: cambia a **Cohere Transcribe** en Handy → Ajustes →
  Modelos (a cambio de que los dictados largos se recorten).
- **Las palabras raras siguen saliendo mal**: añade esa palabra al diccionario (Handy → Ajustes →
  Advanced → Custom Words, o `custom_words` en `config/handy-settings.json` + `patch-config.ps1`).
  Añade pocos términos: con Whisper entran como *prompt* del decodificador y sesgan la transcripción
  (ver *Diccionario de términos*).
- **Aparece un término técnico en medio de una frase que no lo pedía**: es el corrector difuso actuando
  sobre un término que hayas añadido al diccionario. Aquí ya va con umbral estricto (`0.05`); si aun
  así ocurre, quita ese término del diccionario y avísalo.
- **El lector no habla**: mira `lector.log` (carpeta del lector). Causas típicas: falta la voz (instálala desde el panel), el lector está apagado (enciéndelo en el panel de voz) o el portapapeles no tiene texto (suena un pitido y la píldora se pone gris).
- **El atajo del lector no responde / "ya está en uso"**: otra app tiene `Ctrl+Alt+R` o hay otro lector abierto. Cambia `atajo` en `lector.json` y reinicia el lector.
- **Linux: el lector no funciona en Wayland**: los atajos globales solo van en X11; inicia sesión con Xorg. Si falta sonido: `sudo apt install libportaudio2`; si no lee el portapapeles: `sudo apt install xclip`.
- **Quiero la vista previa en vivo mientras hablo**: cambia a `Nemotron Streaming 3.5` en Handy → Ajustes → Modelos (a cambio de bastante menos precisión).

## Reutilizar en otro ordenador

1. Descarga el ZIP o haz `git clone` y ejecuta `Instalar.cmd` (Windows) o `./Instalar.sh` (Linux): instala y configura todo automáticamente.
2. Si el PC no tiene GPU NVIDIA suficiente, en Linux el instalador deja solo el dictado; en Windows, con la opción calidad, elige `qwen3:4b-instruct`. También puedes forzarlo con `-AsistenteModelo qwen3:4b-instruct` (Linux: `--modelo`).
3. Si el PC ya tenía Handy configurado, usa `scripts\patch-config.ps1` (Linux: `scripts/patch-config.sh`) en lugar de reinstalar la configuración.
