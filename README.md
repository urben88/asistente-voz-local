# Asistente de voz local (Handy + Ollama)

Dictado por voz con IA **100% local** para Windows y Linux: hablas y obtienes transcripción, resúmenes, correos o lo que pidas — sin enviar nada a la nube.

## Instalación en 1 clic (Windows)

1. **Consigue la carpeta**: clona el repositorio (`git clone …`) o descarga el ZIP y descomprímelo.
2. **Doble clic en `Instalar.cmd`** (está en la raíz de la carpeta).
3. **Acepta el aviso de Windows (UAC)**: el instalador pide permisos de administrador porque Ollama se instala a nivel de sistema. Si ya ejecutas como administrador, no aparece aviso.
4. **Espera**: se descargan unos **11 GB** — Handy (~0,3 GB), el modelo de dictado Whisper Turbo (~1,5 GB, el que transcribe completos los dictados largos), el modelo de texto del asistente (~7 GB) y el modelo ligero de respaldo (~2,5 GB), más el lector de voz (~0,2 GB de modelo y ~0,5 GB de entorno Python). Según tu conexión puede tardar bastante.
5. **Al terminar**: abre Handy, elige tu micrófono en Ajustes y prueba los tres atajos (`Ctrl + Alt + Espacio`, `Ctrl + Shift + Espacio` y `Ctrl + Alt + R`). El instalador te ofrece abrirlo al final.

Puedes ejecutarlo las veces que quieras: cada paso comprueba antes de actuar y no repite lo que ya está hecho.

## Instalación en Linux (Mint / Ubuntu / Debian)

Equivalente Linux de `Instalar.cmd`: mismo Handy y Ollama, con los mismos modelos, atajos, prompts y diccionario.

1. **Consigue la carpeta**: clona el repositorio o descarga el ZIP y descomprímelo.
2. **En una terminal, dentro de la carpeta**: `./Instalar.sh`
3. **Espera**: se descargan los mismos modelos que en Windows (~11 GB). Handy se instala con `.deb` (pedirá tu contraseña de `sudo`) o, si no hay permisos de administrador, como **AppImage** en `~/.local/bin/handy`.
4. **Al terminar**: abre Handy, elige tu micrófono en Ajustes y prueba los dos atajos.

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
bash scripts/install.sh --sin-lector                 # no instalar el lector de voz (fase 6)
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
| 6. Lector de voz | Instala `uv` y un entorno Python 3.12, copia el lector, descarga el modelo Kokoro (sha256 y tamaño), crea el autoarranque y lo arranca. Se salta con `-SinLector` |

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

# no instalar el lector de voz (fase 6)
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SinLector
```

`Instalar.cmd` acepta los mismos argumentos: `Instalar.cmd -Simular`.

- En un PC **ya configurado** usa `scripts\patch-config.ps1`: solo cambia modelo de dictado, diccionario, umbral del corrector y buffer, conservando el resto (ver *Aplicar esta configuración en un PC ya configurado*).
- `scripts\apply-config.ps1` reemplaza **toda** la configuración de Handy por la del repo.

### Si algo falla

- **No tengo `winget`**: instala *Instalador de aplicaciones* (App Installer) desde Microsoft Store y repite.
- **Sin conexión**: el instalador avisa y sigue; la configuración se aplica igual y el modelo de dictado se puede recuperar repitiendo el instalador.
- **"Handy está abierto"**: ciérralo desde la bandeja del sistema (clic derecho → *Salir*) y repite. Handy reescribe su configuración al salir, por eso se exige cerrarlo.
- **El antivirus bloquea** la descarga o la instalación: permite la carpeta del repo (o `powershell`/`curl`) y repite.
- **Nada se rompe por repetir**: los scripts comprueban cada paso antes de actuar.

## Los tres atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictado puro**: transcribe lo que dices (el texto aparece al terminar la grabación) y lo pega donde tengas el cursor. |
| `Ctrl + Shift + Espacio` | **Asistente IA local**: analiza lo dictado. Si es información → resumen. Si es una petición ("escríbeme un correo formal sobre...", "explícame X", "hazme una lista de...") → la ejecuta y pega el resultado. |
| `Ctrl + Alt + R` | **Lector de voz**: lee en voz alta el portapapeles (el último texto copiado o dictado). Otra pulsación lo para. Si es Markdown (p. ej. un chat de un agente de IA), omite bloques de código, URL, líneas de herramientas y tablas largas. |

`Esc` cancela una grabación en curso.

**El texto generado (dictado o asistente) queda siempre copiado en el portapapeles**, además de pegarse donde tengas el cursor (`Ctrl+V` para reutilizarlo).

## Componentes (todo local)

| Pieza | Función | Modelo |
|---|---|---|
| [Handy](https://handy.computer) | Captura de voz + transcripción + pegado | Whisper Turbo (`ggml-large-v3-turbo.bin`, GPU vía Vulkan) |
| [Ollama](https://ollama.com) | Motor de IA de texto local | gemma4:e4b (resúmenes, correos, explicaciones...) |
| [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) | Lector de voz (texto a voz, en CPU) | Kokoro-82M fp16 (`kokoro-v1.0.fp16.onnx`) |

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

El lector (`Ctrl + Alt + R`) queda residente en segundo plano, arranca con el inicio de sesión y corre en CPU (la GPU la usa Ollama). Se instala en `%LOCALAPPDATA%\asistente-voz-local\lector` (Windows) o `~/.local/share/asistente-voz-local/lector` (Linux).

- **Config**: `lector.json` en esa carpeta. Campos: `atajo`, `voz` (`em_alex` por defecto; también `ef_dora`, `em_santa`) y `velocidad` (1.0 = normal). **Reinicia el lector** tras cambiarla (ciérralo desde el Administrador de tareas o vuelve a iniciar sesión). El instalador no sobrescribe tu `lector.json`.
- **Píldora visual**: mientras lee aparece abajo en el centro una píldora con el mismo diseño que la de Handy (gris mientras prepara la voz, rosa con barras que siguen la voz mientras habla). Clic en ella o el atajo otra vez para parar. No roba el foco de la ventana en la que estés.
- **Memoria**: el modelo de voz está siempre cargado (~450 MB de RAM, sin GPU), a la vez que el de dictado: no se descarga ni se recarga entre lecturas.
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
├── config/lector.json           # configuración del lector de voz (atajo, voz, velocidad)
├── lector/                      # lector de voz (Kokoro): lector.py, leer_md.py (Markdown), pildora.py (visual)
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
- **El lector no habla**: mira `lector.log` (carpeta del lector). Causas típicas: falta el modelo (repite el instalador), el lector no está en marcha (ábrelo desde el acceso directo *Lector de voz* de la carpeta Inicio) o el portapapeles no tiene texto (suena un pitido).
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
