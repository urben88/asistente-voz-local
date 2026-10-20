# Spec 06 — Lector de voz local (Kokoro): fase 6 del instalador

Estado: implementada e instalada en Windows (fase 6 real ejecutada: modelo verificado, autoarranque, atajo y píldora probados). Linux solo validado con `--simular`.
Fecha: 2026-10-20

## Objetivo

Añadir un tercer atajo global, `Ctrl + Alt + R`, que **lee en voz alta el
portapapeles** (último texto copiado o dictado) con una voz local; otra pulsación lo para. Si el
texto es Markdown (p. ej. un chat de un agente de IA), omite bloques de código, URL, líneas de
herramientas y tablas largas. Todo local, en CPU (la GPU la usa Ollama).

## Contexto verificado

- Motor: **Kokoro-82M** vía `kokoro-onnx 0.6.1`, que exige **Python < 3.14**. En este PC `py` es
  3.14, así que se usa **`uv` con Python 3.12 gestionado**: `uv venv -p 3.12 <dir>\.venv` y
  `uv pip install -p <python del venv> -r requirements.txt`.
- Modelo (release `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/`):
  - `kokoro-v1.0.fp16.onnx` — 163527961 bytes — sha256
    `f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96`
  - `voices-v1.0.bin` — 28214398 bytes — sha256
    `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`
- Se elige **fp16**: el int8 en CPU es 2,5x **más lento** que el tiempo real; fp16 ≈ 3,4x más
  rápido que el tiempo real.
- Atajo `Ctrl+Alt+R` probado libre con `RegisterHotKey` (Windows); no choca con AltGr en teclado español (AltGr+R no escribe nada). Primero se usó `Ctrl+Alt+Shift+Espacio`; el usuario lo cambió por uno más sencillo.
- Voces en español: `ef_dora`, `em_alex`, `em_santa` (por defecto `em_alex`). La calidad del
  español de Kokoro es limitada (según su VOICES.md).
- Windows: el instalador corre elevado (UAC); el lector se arranca vía Explorer sobre el acceso
  directo de Inicio para que corra **sin privilegios de administrador**.
- Linux: `sounddevice` necesita `libportaudio2`; el portapapeles necesita `xclip`, `xsel` o
  `wl-paste`; los atajos globales (`pynput`) solo funcionan en **X11**, no en Wayland.

## Requisitos

R1. Archivos del repo: `lector/*.py` (`lector.py`, `leer_md.py`, `pildora.py`), `lector/requirements.txt` y
   `config/lector.json` (atajo, voz, velocidad, idioma, modelo, voces, `max_caracteres`).

R2. `scripts/install.ps1` y `scripts/install.sh` añaden la fase **[6/6] Lector de voz (Kokoro)**
   (resto de fases renumeradas a /6), idempotente y con `-Simular` / `--simular` (solo SIMULA).
   Opción para saltarla: `-SinLector` / `--sin-lector` (documentada en la cabecera; `Instalar.cmd`
   e `Instalar.sh` ya pasan los argumentos).

R3. Carpeta de instalación: Windows `%LOCALAPPDATA%\asistente-voz-local\lector`; Linux
   `${XDG_DATA_HOME:-~/.local/share}/asistente-voz-local/lector`.

R4. Pasos de la fase: (1) parar el lector si está en marcha; (2) copiar siempre todos los `lector/*.py`
   y `requirements.txt`, y `lector.json` **solo si no existe** (se conservan los
   cambios del usuario); (3) instalar `uv` si falta (winget / script oficial), crear el venv 3.12
   si falta e instalar los requisitos; (4) descargar/verificar los 2 archivos del modelo en
   `modelo\` (sha256 + tamaño; si coinciden no se descargan; si no, se borran y se descargan con
   `curl --fail --retry 3`); (5) autoarranque; (6) arrancar el lector.

R5. Autoarranque: Windows, acceso directo `Lector de voz.lnk` en la carpeta Inicio → `pythonw.exe`
   del venv con `"<carpeta>\lector.py"`. Linux, `~/.config/autostart/lector-voz.desktop`.

R6. Avisos en Linux (no bloquean): sesión Wayland (atajos globales solo en X11), falta de
   `libportaudio2` y falta de `xclip`/`xsel`/`wl-paste`, cada uno con el comando `apt` para
   resolverlo.

R7. Preflight: conectividad con `github.com` (aviso, no bloquea). Resumen final: línea «Lector de
   voz: modelo verificado sí/no, autoarranque sí/no». «Siguientes pasos»: menciona el tercer atajo.

R8. Los fallos de la fase no son fatales: se muestran con `Mostrar-Fallo` / `fallo` y el resto del
   instalador continúa.

R9. README: «Los tres atajos», Kokoro en Componentes, espacio extra (~0,2 GB de modelo + ~0,5 GB
   de entorno Python), opción `-SinLector`/`--sin-lector`, subsección «Lector de voz», estructura y
   solución de problemas.

## Verificación

- [ ] `install.ps1 -Simular -NoAbrir` termina sin errores de parseo y muestra la fase [6/6] con
      líneas SIMULA.
- [ ] `install.ps1 -Simular -SinLector` muestra que se salta la fase.
- [ ] `bash -n scripts/install.sh scripts/comun.sh` sin errores; `install.sh --simular` muestra la
      fase [6/6].
- [ ] Instalación real en Windows: venv 3.12 creado, modelo verificado, `.lnk` creado, lector sin
      privilegios de admin, el atajo lee el portapapeles y una 2.ª pulsación lo para.
- [ ] Segunda ejecución del instalador: no re-descarga el modelo y conserva `lector.json`.
- [ ] Instalación real en Linux (X11): `.desktop` creado, avisos correctos si faltan dependencias.
