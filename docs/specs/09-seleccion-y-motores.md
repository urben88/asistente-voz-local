# Spec 09 — Leer la selección, panel separado y motores de alta calidad

Estado: implementada e instalada en este PC (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Tres cambios pedidos por el usuario:

1. Al pulsar `Ctrl+Alt+R`, leer **el texto seleccionado** si hay; si no, el portapapeles.
2. Que el panel deje claro **qué configuración es del lector y cuál del dictado**.
3. Ofrecer **motores de voz más potentes** (aunque tarden más y ocupen más) e instalarlos.

## R1. Leer la selección antes que el portapapeles

- `lector/seleccion.py`, `texto_seleccionado(portapapeles)`:
  - **UI Automation** (título `TextPattern`) sobre el control con el foco y hasta 4 antecesores:
    sin efectos secundarios. No funciona dentro de Escritorio remoto ni en apps sin accesibilidad.
  - **Ctrl+C temporal**: se pulsa Ctrl+C en la ventana con el foco (se espera 200 ms por si el
    usuario aún tiene Alt pulsado), se sondea el portapapeles hasta 1,2 s hasta que cambie y se
    restaura el contenido anterior. Funciona en local y en Escritorio remoto con portapapeles
    redirigido. Aviso: en una terminal Ctrl+C puede interrumpir; por eso se puede desactivar.
  - Linux: selección primaria (`wl-paste --primary`, `xclip -selection primary`, `xsel --primary`).
- `lector.py`, `alternar()`: `portapapeles = leer_portapapeles()`; si
  `cfg["leer_seleccion"]` (por defecto `true`), intenta la selección; si no hay, usa el
  portapapeles. El log dice de dónde salió («Leyendo la selección (N caracteres)»).
- `escribir_portapapeles()` (Windows y Linux) para restaurar el portapapeles.
- Panel, pestaña Lector: sección **«Qué leer»** con `Selección` / `Portapapeles`, persistido en
  `lector.json`.

## R2. Panel con dos pestañas

- `ttk.Notebook` oscuro con **«Lector de voz»** y **«Dictado (Handy)»**.
- Lector: Lector (encendido/apagado), Qué leer, Idioma, Motor, Velocidad, Voz (+ instalar/guía),
  Estado del lector.
- Dictado (Handy), **solo lectura**: si Handy está abierto, modelo de dictado e idioma, atajos
  actuales (leídos de `%APPDATA%\com.pais.handy\settings_store.json`, función
  `estado.leer_handy_settings()`) y estado de la GPU. Nota: «se configura en Handy → Ajustes; este
  panel no cambia nada».
- Cada sección mantiene su «?» y tooltip; nuevas ayudas: `seleccion`, `handy`, `handy_modelo`,
  `handy_atajos`, `gpu`.

## R3. Motores de alta calidad (GPU)

- `lector/motor.py`:
  - `ChatterboxMotor` (`chatterbox-tts`, multilingüe): 24 kHz, una voz por idioma, GPU ~3,2 GB.
    Medido: carga ~20 s, **RTF 1,3-1,9** (genera más lento de lo que habla → puede haber pausas
    entre frases).
  - `XttsMotor` (`coqui-tts`, XTTS-v2): 58 voces, 24 kHz, GPU ~1,8 GB. Medido: carga ~15 s,
    **RTF 0,62** (1,6× más rápido que el tiempo real).
  - Ambos con `carga_lenta = True`: el vigilante del lector da hasta 240 s en «preparando» (frente
    a 25 s de Piper/Kokoro) para no cortar la carga del modelo.
  - Si no hay CUDA, arrancan en CPU (muy lentos, pero funcionan).
- `lector/requirements-calidad.txt` (opcional, ~5 GB con torch): `torch`, `torchaudio`,
  `chatterbox-tts`, `coqui-tts`. El instalador **no** los pone por defecto.
- Panel: Motor con `Piper`, `Kokoro`, `Chatterbox`, `XTTS`; voces curadas por idioma
  (`voces.VOCES_CALIDAD`) y línea informativa con VRAM y velocidad.
- Guía «¿Qué elijo?»: nueva sección **«Motores: rápido o natural»** con los cuatro motores y dos
  no instalados (Orpheus 3B, F5-TTS) y la recomendación (Piper para el día a día, Chatterbox para
  máxima naturalidad, XTTS como equilibrio GPU).

## Medidas en este PC (RTX 3070 8 GB, 48 GB RAM)

| Motor | Dónde | Carga | Velocidad | Memoria |
|---|---|---|---|---|
| Piper (high/medium) | CPU | 2-6 s | 20-37× tiempo real | 60-110 MB disco |
| Kokoro | CPU | ~3 s | 3,6× tiempo real | ~450 MB RAM |
| Chatterbox | GPU | ~20 s | 1,3-1,9× (más lento que habla) | 3,2 GB VRAM |
| XTTS-v2 | GPU | ~15 s | 1,6× más rápido | 1,8 GB VRAM |

## Verificación

- [x] `_copiar_seleccion`: copia nueva → se devuelve y el portapapeles queda como estaba;
      sin copia → `""`; copia igual → `""` (prueba con la copia simulada).
- [x] UI Automation y Ctrl+C responden sin errores; en esta sesión el foco estaba en una ventana de
      Escritorio remoto, así que la prueba con selección real queda para el usuario.
- [x] Panel con dos pestañas, 12 ayudas, «Qué leer» y lectura de la config de Handy (modelo
      Whisper Turbo, atajos Ctrl+Alt+Espacio / Ctrl+Shift+Espacio).
- [x] Motores nuevos cargan y sintetizan: Chatterbox 3,8 s de audio, XTTS 3,3 s (RTF 0,62).
- [x] Panel y lector reiniciados; el lector sigue con Piper `es_ES-davefx-medium` + Velocidad Rápida.
- [ ] Prueba del usuario: seleccionar texto en el navegador/RDP y pulsar Ctrl+Alt+R.
- [ ] Prueba del usuario con Chatterbox y XTTS (calidad y pausas).
