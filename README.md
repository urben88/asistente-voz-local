# Asistente de voz local (Handy + Ollama)

Dictado por voz con IA **100% local** para Windows y Linux: hablas y obtienes transcripción, resúmenes, correos o lo que pidas — sin enviar nada a la nube.

## Instalación en 1 clic (Windows)

1. **Consigue la carpeta**: clona el repositorio (`git clone …`) o descarga el ZIP y descomprímelo.
2. **Doble clic en `Instalar.cmd`** (está en la raíz de la carpeta).
3. **Acepta el aviso de Windows (UAC)**: el instalador pide permisos de administrador porque Ollama se instala a nivel de sistema. Si ya ejecutas como administrador, no aparece aviso.
4. **Espera**: se descargan unos **11 GB** — Handy (~0,3 GB), el modelo de dictado Cohere Transcribe 2B (~1,7 GB, el de la transcripción precisa), el modelo de texto del asistente (~7 GB) y el modelo ligero de respaldo (~2,5 GB). Según tu conexión puede tardar bastante.
5. **Al terminar**: abre Handy, elige tu micrófono en Ajustes y prueba los dos atajos (`Ctrl + Alt + Espacio` y `Ctrl + Shift + Espacio`). El instalador te ofrece abrirlo al final.

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
- GPU **NVIDIA opcional**: sin ella el instalador usa el modelo ligero `qwen3:4b-instruct`.

### Requisitos

- **Windows 10/11 de 64 bits**.
- **~20 GB libres** en el disco del sistema (mínimo ~15 GB) e internet.
- GPU **NVIDIA opcional**: acelera el dictado y el asistente. Sin GPU suficiente, el instalador elige automáticamente el modelo ligero.

### Qué hace el instalador

| Fase | Qué hace |
|---|---|
| 0. Comprobaciones | SO de 64 bits, `winget`, espacio en disco, conexión y que **Handy esté cerrado** |
| 1. Handy | Lo instala con winget (o muestra la versión si ya está); avisa si es anterior a 0.9.8 |
| 2. Ollama | Lo instala si falta y arranca su servidor local |
| 3. Modelos del asistente | Descarga `gemma4:e4b` (estándar) y `qwen3:4b-instruct` (ligero) |
| 4. Modelo de dictado | Descarga Cohere Transcribe 2B y verifica sha256 y tamaño (Hugging Face y, si falla, su mirror) |
| 5. Configuración | PC nuevo: copia la config del repo. PC ya configurado: **merge de 3 campos** (modelo de dictado, diccionario y buffer) conservando tu micrófono, atajos y prompts |

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
```

`Instalar.cmd` acepta los mismos argumentos: `Instalar.cmd -Simular`.

- En un PC **ya configurado** usa `scripts\patch-config.ps1`: solo cambia modelo de dictado, diccionario y buffer, conservando el resto (ver *Aplicar esta configuración en un PC ya configurado*).
- `scripts\apply-config.ps1` reemplaza **toda** la configuración de Handy por la del repo.

### Si algo falla

- **No tengo `winget`**: instala *Instalador de aplicaciones* (App Installer) desde Microsoft Store y repite.
- **Sin conexión**: el instalador avisa y sigue; la configuración se aplica igual y el modelo de dictado se puede recuperar repitiendo el instalador.
- **"Handy está abierto"**: ciérralo desde la bandeja del sistema (clic derecho → *Salir*) y repite. Handy reescribe su configuración al salir, por eso se exige cerrarlo.
- **El antivirus bloquea** la descarga o la instalación: permite la carpeta del repo (o `powershell`/`curl`) y repite.
- **Nada se rompe por repetir**: los scripts comprueban cada paso antes de actuar.

## Los dos atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictado puro**: transcribe lo que dices (el texto aparece al terminar la grabación) y lo pega donde tengas el cursor. |
| `Ctrl + Shift + Espacio` | **Asistente IA local**: analiza lo dictado. Si es información → resumen. Si es una petición ("escríbeme un correo formal sobre...", "explícame X", "hazme una lista de...") → la ejecuta y pega el resultado. |

`Esc` cancela una grabación en curso.

**El texto generado (dictado o asistente) queda siempre copiado en el portapapeles**, además de pegarse donde tengas el cursor (`Ctrl+V` para reutilizarlo).

## Componentes (todo local)

| Pieza | Función | Modelo |
|---|---|---|
| [Handy](https://handy.computer) | Captura de voz + transcripción + pegado | Cohere Transcribe 2B (Q5_K_M, GPU vía Vulkan) |
| [Ollama](https://ollama.com) | Motor de IA de texto local | gemma4:e4b (resúmenes, correos, explicaciones...) |

## Ejemplos de uso con `Ctrl + Shift + Espacio`

- *(información)* "...reunión de ayer: la línea 3 parada, repuesto el jueves 18, coste 2400 euros..." → **resumen** con datos clave.
- *"Escríbeme un correo formal al proveedor para confirmar la entrega del pedido 4821 antes del día 20"* → **correo formal** listo.
- *"Escríbeme un mensaje coloquial para mi compañero recordándole la reunión de mañana"* → **mensaje informal** (como si lo contaras tú).
- *"Explícame qué es una API REST, rápido"* → **explicación breve**.
- *"Genera un script de Python de una calculadora"* → **código en texto plano** (sin ``` y sin caracteres raros).

## Configuración

### Modelo de dictado

El dictado usa **Cohere Transcribe 2B (Q5_K_M)**: máxima precisión en español, con 14 idiomas soportados y acelerado por GPU (Vulkan). El archivo se guarda en el caché de Hugging Face (`%USERPROFILE%\.cache\huggingface\hub\models--handy-computer--cohere-transcribe-03-2026-gguf\`), que es donde Handy busca los modelos descargados.

Para cambiarlo: **Handy → Ajustes → Modelos**. Alternativas ya disponibles y para qué sirve cada una:

| Modelo | Para qué |
|---|---|
| `Cohere Transcribe` | **Máxima precisión** (por defecto). |
| `Nemotron Streaming 3.5` | La única con **vista previa en vivo** (ves las palabras mientras hablas); precisión baja. |
| `Whisper Turbo` | Ya está el archivo descargado en el PC (`ggml-large-v3-turbo.bin`); alternativa probada. |
| `Whisper Large v3` (~1 GB) | Un poco más preciso que Turbo, pero más lento (se descarga al elegirlo). |

**Vista previa en vivo**: los modelos *streaming* (Nemotron) escriben el texto palabra a palabra mientras hablas. Cohere y Whisper **no** son streaming: durante la grabación solo se ve la píldora de estado y el texto aparece completo al terminar (rápido en GPU). Es el precio de la precisión.

### Diccionario de términos (`custom_words`)

Lista de términos que Handy corrige de forma difusa (Levenshtein + Soundex) al transcribir. Sirve para que los términos técnicos y las mayúsculas salgan bien: `PLC`, `Modbus`, `SCADA`, `PostgreSQL`, `PowerShell`... Está definido en `config/handy-settings.json`.

- **Añadir o quitar términos**: Handy → Ajustes → **Advanced → Custom Words**, o editando `custom_words` en `config/handy-settings.json` y ejecutando `scripts\patch-config.ps1` (con Handy cerrado).
- **Aviso importante**: no metas palabras que choquen con palabras normales del español (`MES` ≈ "mes", `RAM` ≈ "rama", `REST` ≈ "resto"): la corrección difusa las cambiaría también en frases normales y corrompería el texto.
- **Buffer de audio**: `extra_recording_buffer_ms = 250` graba 250 ms extra al soltar el atajo para no cortar la última palabra (el detector de voz VAD descarta ese silencio añadido).

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
| `scripts\patch-config.ps1` | **Recomendado**: parche selectivo. Copia al Handy real solo `selected_model`, `custom_words` y `extra_recording_buffer_ms` del repo; conserva tu micrófono, atajos, prompts, etc. Crea copia previa `settings_store.json.bak`. |
| `scripts\apply-config.ps1` | ⚠️ **Reemplaza toda** la configuración de Handy por la del repo (micrófono, atajos y prompts incluidos) y descarga el modelo de dictado si falta. Úsalo solo si quieres dejar Handy exactamente como el repo. |

## Estructura

```
asistente-voz-local/
├── Instalar.cmd                 # Windows: doble clic: instala todo (se auto-eleva con UAC)
├── Instalar.sh                  # Linux: ./Instalar.sh (mismas opciones que install.sh)
├── README.md
├── config/handy-settings.json   # configuración de Handy lista para aplicar
├── docs/specs/                  # especificaciones de los cambios
├── prompts/                     # textos de los prompts (referencia/edición)
│   ├── asistente.md
│   ├── correo-formal.md
│   └── texto-coloquial.md
└── scripts/
    ├── install.ps1              # Windows: instalador (PC nuevo); -Simular/-AsistenteModelo/-NoAbrir
    ├── settings-merge.ps1       # Windows: merge de config compartido (funciones)
    ├── patch-config.ps1         # Windows: PC ya configurado: solo modelo/diccionario/buffer
    ├── apply-config.ps1         # Windows: reemplaza toda la configuración de Handy
    ├── install.sh               # Linux: instalador (PC nuevo); --simular/--modelo/--no-abrir/--metodo
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
- **Las palabras raras siguen saliendo mal**: añade esa palabra al diccionario (Handy → Ajustes → Advanced → Custom Words, o `custom_words` en `config/handy-settings.json` + `patch-config.ps1`).
- **Quiero la vista previa en vivo mientras hablo**: cambia a `Nemotron Streaming 3.5` en Handy → Ajustes → Modelos (a cambio de bastante menos precisión).

## Reutilizar en otro ordenador

1. Copia la carpeta (o `git clone`) y haz doble clic en `Instalar.cmd`: instala y configura todo automáticamente.
2. Si el PC no tiene GPU NVIDIA suficiente, el instalador elige `qwen3:4b-instruct` solo; también puedes forzarlo con `-AsistenteModelo qwen3:4b-instruct`.
3. Si el PC ya tenía Handy configurado, usa `scripts\patch-config.ps1` en lugar de reinstalar la configuración.
4. Si tienes repositorio remoto: `git push` aquí y `git clone` en el otro PC.

---

*Generado como parte de la configuración del asistente de voz local — Octubre 2026.*
