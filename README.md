# Asistente de voz local (Handy + Ollama)

Dictado por voz con IA **100% local** para Windows y Linux: hablas y obtienes transcripción, resúmenes, correos o lo que pidas — sin enviar nada a la nube.

## Instalación en 1 clic (Windows)

1. **Consigue la carpeta**: clona el repositorio (`git clone …`) o descarga el ZIP y descomprímelo.
2. **Doble clic en `Instalar.cmd`** (está en la raíz de la carpeta).
3. **Acepta el aviso de Windows (UAC)**: el instalador pide permisos de administrador porque Ollama se instala a nivel de sistema. Si ya ejecutas como administrador, no aparece aviso.
4. **Espera**: se descargan unos **11 GB** — Handy (~0,3 GB), el modelo de dictado Whisper Turbo (~1,5 GB, el que transcribe completos los dictados largos), el modelo de texto del asistente (~7 GB) y el modelo ligero de respaldo (~2,5 GB), más el lector de voz (~0,2 GB de modelo y ~0,5 GB de entorno Python). Según tu conexión puede tardar bastante.
5. **Al terminar**: abre Handy, elige tu micrófono en Ajustes y prueba los cuatro atajos (`Ctrl + Alt + Espacio`, `Ctrl + Shift + Espacio`, `Ctrl + Alt + R` y `Ctrl + Alt + P`). El instalador te ofrece abrirlo al final.

Puedes ejecutarlo las veces que quieras: cada paso comprueba antes de actuar y no repite lo que ya está hecho.

## Instalación en Linux (Mint / Ubuntu / Debian)

Equivalente Linux de `Instalar.cmd`: mismo Handy y Ollama, con los mismos modelos, atajos, prompts y diccionario.

1. **Consigue la carpeta**: clona el repositorio o descarga el ZIP y descomprímelo.
2. **En una terminal, dentro de la carpeta**: `./Instalar.sh`
3. **Espera**: se descargan los mismos modelos que en Windows (~11 GB). Handy se instala con `.deb` (pedirá tu contraseña de `sudo`) o, si no hay permisos de administrador, como **AppImage** en `~/.local/bin/handy`.
4. **Al terminar**: abre Handy, elige tu micrófono en Ajustes y prueba los atajos.

También se puede ejecutar las veces que quieras: cada paso comprueba antes de actuar y no repite lo que ya está hecho.

### Rutas en Linux

| Qué | Dónde |
|---|---|
| Config de Handy | `~/.local/share/com.pais.handy/settings_store.json` |
| Modelo de dictado | `~/.cache/huggingface/hub/models--handy-computer--cohere-transcribe-03-2026-gguf/…` |
| Servidor de Ollama | `http://127.0.0.1:11434` |

### Opciones (Linux)

```bash
bash scripts/install.sh --simular                    # ver que haria sin tocar nada (no instala ni descarga)
bash scripts/install.sh --solo-dictado               # SOLO transcripcion: sin Ollama ni modelos de IA (alias --sin-ia)
bash scripts/install.sh --modelo qwen3:4b-instruct   # forzar el modelo ligero del asistente
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

### Requisitos Linux

- Distro de 64 bits compatible con `.deb` (Linux Mint, Ubuntu, Debian) o cualquier distro usando `--metodo appimage`.
- **~20 GB libres** e internet. `python3` y `curl` (vienen de serie).
- Lector de voz (opcional): `libportaudio2` y `xclip` (o `xsel`/`wl-paste`); los atajos globales del lector solo funcionan en **X11**, no en Wayland.
- GPU **NVIDIA opcional**: sin ella el instalador usa el modelo ligero `qwen3:4b-instruct`.

### Requisitos

- **Windows 10/11 de 64 bits**.
- **~20 GB libres** en el disco del sistema (mínimo ~15 GB) e internet. El lector de voz añade ~0,7 GB (modelo ~0,2 GB + entorno Python ~0,5 GB).
- GPU **NVIDIA opcional**: acelera el dictado y el asistente. Sin GPU suficiente, el instalador elige automáticamente el modelo ligero.

### Qué hace el instalador

| Fase | Qué hace |
|---|---|
| 0. Comprobaciones | SO de 64 bits, `winget`, espacio en disco, conexión y que **Handy esté cerrado** |
| 1. Handy | Lo instala con winget (o muestra la versión si ya está); avisa si es anterior a 0.9.8 |
| 2. Ollama | Lo instala si falta y arranca su servidor local |
| 3. Modelos del asistente | Descarga `gemma4:e4b` (estándar) y `qwen3:4b-instruct` (ligero) |
| 4. Modelo de dictado | Descarga Whisper Turbo (`ggml-large-v3-turbo.bin`, ~1,5 GB) en la carpeta de modelos de Handy y verifica sha256 y tamaño |
| 5. Configuración | PC nuevo: copia la config del repo. PC ya configurado: **merge de 4 campos** (modelo de dictado, diccionario, umbral del corrector y buffer) conservando tu micrófono, atajos y prompts |
| 6. Lector de voz | Instala `uv` y un entorno Python 3.12, copia el lector, descarga el modelo Kokoro (sha256 y tamaño), crea el autoarranque y lo arranca. Se salta con `-SinLector` (junto con la 7) |
| 7. Panel de voz | Instala `piper-tts` y `pystray` en el entorno del lector, copia el panel, descarga la voz `es_ES-davefx-medium` (~63 MB) si falta, crea el autoarranque `Panel de voz.lnk`, **borra el del lector** y arranca el panel. Se salta con `-SinLector` |

**El asistente estándar es `gemma4:e4b`.** En PCs sin GPU NVIDIA suficiente (menos de 8 GB de VRAM) el instalador usa y deja configurado automáticamente `qwen3:4b-instruct`.

Al final muestra un **resumen** con la versión instalada, los modelos presentes, el sha256 del modelo de dictado y los siguientes pasos.

### Opciones avanzadas

Desde PowerShell, en la carpeta del repo:

```powershell
# ver que haria sin tocar nada (no instala, no descarga y no copia nada)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Simular

# forzar el modelo ligero del asistente (PC con poca VRAM)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -AsistenteModelo qwen3:4b-instruct

# no ofrecer abrir Handy al terminar
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -NoAbrir

# no instalar el lector ni el panel de voz (fases 6 y 7)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SinLector
```

`Instalar.cmd` acepta los mismos argumentos: `Instalar.cmd -Simular`.

- **Espacio extra** del lector y el panel: ~0,2 GB (modelo Kokoro) + ~0,7 GB (entorno Python) + 63 MB por cada voz Piper que descargues. Los motores de alta calidad (Chatterbox, XTTS) añaden ~5 GB y solo se instalan si los quieres.

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

## Los cuatro atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictado puro**: transcribe lo que dices (el texto aparece al terminar la grabación) y lo pega donde tengas el cursor. |
| `Ctrl + Shift + Espacio` | **Resumen / asistente IA local**: dictas y, al parar, Ollama procesa el texto con el prompt activo (por defecto, resumen). Si es información → resumen; si es una petición ("escríbeme un correo formal sobre...", "explícame X", "hazme una lista de...") → la ejecuta y pega el resultado. Está explicado en el panel, pestaña **Resumen**. |
| `Ctrl + Alt + R` | **Lector de voz**: lee en voz alta **el texto que tengas seleccionado** en la ventana con el foco; si no hay nada seleccionado, el portapapeles. Otra pulsación lo para. Limpia lo que no se debe oír: bloques de código, tablas largas, URLs, HTML, emojis, iconos, flechas y restos de Markdown. Lee con pausas naturales (coma, dos puntos y punto) y convive con el dictado: puedes dictar y leer a la vez. |
| `Ctrl + Alt + P` | **Panel de voz**: abre/cierra el panel (encender/apagar lector, idioma, motor, voz). La X lo deja en la bandeja del sistema. |

`Esc` cancela una grabación en curso.

**El texto generado (dictado o asistente) queda siempre copiado en el portapapeles**, además de pegarse donde tengas el cursor (`Ctrl+V` para reutilizarlo).

## Panel de voz

El **panel de voz** es el centro de control del lector: encendido, idioma, motor y voz. Se abre con el **icono de la bandeja del sistema** (clic izquierdo) o con `Ctrl + Alt + P`. La **X** cierra la ventana pero lo deja en la bandeja; para terminarlo, **Salir** en el menú de la bandeja (no toca Handy ni el lector).

Los atajos **conviven**: `Ctrl + Alt + Espacio` dicta y `Ctrl + Alt + R` lee cuando quieras, sin cambiar nada ni apagar nada. El lector trabaja en CPU y Handy/Ollama en GPU, así que no compiten.

El panel tiene **dos pestañas**, para que no se mezcle lo de cada programa:

- **Lector de voz** (todo lo configura este panel): encendido/apagado, **qué leer** (la selección o el portapapeles), idioma, motor, velocidad, voz e instalación de voces. Los motores de alta calidad (Chatterbox, XTTS) usan la GPU.
- **Dictado (Handy)** (solo lectura): si Handy está abierto, su modelo de dictado, sus atajos y el estado de la GPU. Handy se configura en **Handy → Ajustes**; este panel no cambia nada suyo.

- **Lector Encendido / Apagado**: arranca o para el proceso del lector. Apagado no consume ni RAM ni CPU; encendido tarda ~4 s en cargar la voz.
- **Idioma** (Español / English), **Motor** (Piper / Kokoro) y **Voz** (solo las voces instaladas del motor y el idioma elegidos).
- **Instalar voces…**: abre el catálogo curado de voces Piper (nombre, descripción y tamaño) y las descarga en segundo plano sin bloquear el panel (60-120 MB cada una).
- **Motores de alta calidad (GPU, opcionales)**: `Chatterbox` (la voz más natural en español; ~3,2 GB de VRAM y genera 1,3× más lento de lo que habla, así que puede hacer pausas) y `XTTS` (58 voces y 17 idiomas; ~1,8 GB de VRAM y 1,6× más rápido que el tiempo real). No se instalan por defecto: pesan ~5 GB con `torch`. Instalación:
  ```powershell
  uv pip install -p "$env:LOCALAPPDATA\asistente-voz-local\lector\.venv\Scripts\python.exe" -r lector\requirements-calidad.txt
  ```
  Después aparecen como `Chatterbox` y `XTTS` en **Motor**.
  **Ojo con la VRAM (8 GB)**: Chatterbox + Handy + el escritorio deja la tarjeta casi sin memoria y
  el dictado se ralentiza; XTTS sí convive con Whisper. Para el día a día, Piper (CPU) no usa GPU.
- **¿Qué elijo?**: guía comparativa con **datos medidos en este PC** (calidad, tamaño, tiempo de carga y veces más rápido que el tiempo real). Resumen: la más natural en español es `es_MX-claude-high` (acento de México); la mejor de España, `es_ES-sharvard-medium`; en inglés, `en_US-lessac-high`; las más ligeras, `es_ES-davefx-medium` y `en_US-amy-medium`.
- **«?» en cada apartado**: explicación de qué es, qué cambia y cuánto ocupa (también al pasar el ratón por encima).
- **★ en el motor recomendado**, con el motivo debajo («★ Recomendado: XTTS — mejor calidad y velocidad con tu GPU…»). La recomendación depende del equipo: con GPU, XTTS; sin GPU, Piper. La voz recomendada de cada motor/idioma también lleva ★ en el desplegable.
- **Pestaña «Resumen»**: el atajo (`Ctrl+Shift+Espacio`), qué hace paso a paso (dictas → Handy transcribe → Ollama resume con el prompt activo → se pega y queda en el portapapeles), **selector de modelo** (todos los de Ollama, con ★ en los recomendados y aviso en los grandes), el prompt activo y si el post-procesado está activado. Al pulsar **Usar**, el panel cierra Handy, cambia el modelo y lo reabre (unos segundos); el prompt se sigue configurando en Handy.

**Cómo lee el Markdown**: las **tablas** se anuncian («Tabla de 3 columnas: Pieza, Estado, Notas. 6 filas.») y cada fila se lee con el nombre de su columna («Pieza: Handy; Estado: OK; Notas: Whisper Turbo.»); la columna de índice (`#`, `N`) no se lee y las tablas de más de 10 filas se resumen. Las **casillas** se leen «Hecho: …» / «Pendiente: …», las **citas** empiezan por «Cita: …» y las listas y títulos van como frases, sin leer guiones ni números.

**Selección nativa (sin copiar)**: al pulsar `Ctrl+Alt+R`, el lector pregunta a la app por **UI Automation** (navegadores, editores, Office) y, en **consolas clásicas**, lee la selección del búfer con la API de consola de Windows. Solo si la app no lo expone —o estás dentro de Escritorio remoto— usa un `Ctrl+C` temporal y restaura el portapapeles.

**Mientras carga**: la píldora muestra un aro girando y «Cargando voz… N s» (útil con Chatterbox/XTTS, que tardan 20-30 s). Si pulsas `Ctrl+Alt+R` durante la carga, la píldora avisa y la lectura empieza sola en cuanto la voz está lista. La carga inicial al iniciar sesión es silenciosa: la píldora solo aparece si la pides.
- **Estado**: `GPU libre` o `GPU en uso (Handy / Ollama: modelo)`, y debajo el estado real del lector (`parado`, `leyendo` o `en marcha`).

Los cambios se aplican **al momento**, sin reiniciar el panel. Si cambias idioma o voz **mientras lee**, la lectura actual se corta y la siguiente usa la voz nueva.

**Primera instalación**: `estado.json` arranca con el lector **apagado**; enciéndelo desde el panel la primera vez.

Ficheros del panel:

- `panel/`: programa del panel (ventana, bandeja, estado, control del proceso del lector, catálogo de voces e icono).
- `config/panel.json`: atajo y rutas de Handy/Ollama. El instalador lo copia a `%LOCALAPPDATA%\asistente-voz-local\panel.json`, que es el que se usa.
- `%LOCALAPPDATA%\asistente-voz-local\`: `estado.json` (lector encendido o apagado), `lector-vivo.json` (latido del lector) y `panel.log`. La config del lector que edita el panel es `lector\lector.json`. En Linux, `~/.local/share/asistente-voz-local/`.

## Componentes (todo local)

| Pieza | Función | Modelo |
|---|---|---|
| [Handy](https://handy.computer) | Captura de voz + transcripción + pegado | Whisper Turbo (`ggml-large-v3-turbo.bin`, GPU vía Vulkan) |
| [Ollama](https://ollama.com) | Motor de IA de texto local | gemma4:e4b (resúmenes, correos, explicaciones...) |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | Lector de voz por defecto (texto a voz, en CPU) | Voces `es_ES` / `en_US` (`es_ES-davefx-medium` por defecto) |
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

El dictado usa **Whisper Turbo** (`ggml-large-v3-turbo.bin`, ~1,5 GB): es el único modelo del catálogo de Handy con **audio largo nativo**, así que transcribe completo un dictado largo (media hora, por ejemplo) — medido en este PC, unas 10 veces más rápido que el tiempo real con GPU. El archivo se guarda en `%APPDATA%\com.pais.handy\models\`, que es donde Handy busca los modelos descargados.

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
  El instalador descarga dos y deja configurado el que corresponde a tu PC:
  - `gemma4:e4b` → **estándar** (mejor calidad); es el que se configura por defecto.
  - `qwen3:4b-instruct` → **ligero**, para PCs sin GPU NVIDIA suficiente (el instalador lo deja configurado automáticamente en esos PCs, y también se puede forzar con `-AsistenteModelo qwen3:4b-instruct`).
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
├── config/handy-settings.json   # configuración de Handy lista para aplicar
├── config/lector.json           # configuración del lector (atajo, idioma, motor y voz)
├── config/panel.json            # configuración del panel (atajo y rutas de Handy/Ollama)
├── lector/                      # lector de voz (Piper/Kokoro): lector.py, motor.py, leer_md.py, pildora.py; voces/piper/
├── panel/                       # panel de voz: panel.py, estado.py, control.py, voces.py, icono.py
├── docs/specs/                  # especificaciones de los cambios
├── prompts/                     # textos de los prompts (referencia/edición)
│   ├── asistente.md
│   ├── correo-formal.md
│   └── texto-coloquial.md
└── scripts/
    ├── install.ps1              # Windows: instalador (PC nuevo); -Simular/-AsistenteModelo/-NoAbrir/-SinLector
    ├── settings-merge.ps1       # Windows: merge de config compartido (funciones)
    ├── patch-config.ps1         # Windows: PC ya configurado: solo modelo/diccionario/umbral/buffer
    ├── apply-config.ps1         # Windows: reemplaza toda la configuración de Handy
    ├── install.sh               # Linux: instalador (PC nuevo); --simular/--modelo/--no-abrir/--metodo/--sin-lector
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

1. Copia la carpeta (o `git clone`) y haz doble clic en `Instalar.cmd`: instala y configura todo automáticamente.
2. Si el PC no tiene GPU NVIDIA suficiente, el instalador elige `qwen3:4b-instruct` solo; también puedes forzarlo con `-AsistenteModelo qwen3:4b-instruct`.
3. Si el PC ya tenía Handy configurado, usa `scripts\patch-config.ps1` en lugar de reinstalar la configuración.
4. Si tienes repositorio remoto: `git push` aquí y `git clone` en el otro PC.

---

*Generado como parte de la configuración del asistente de voz local — Octubre 2026.*
