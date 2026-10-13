# Asistente de voz local (Handy + Ollama)

Dictado por voz con IA **100% local** para Windows: hablas y obtienes transcripción, resúmenes, correos o lo que pidas — sin enviar nada a la nube.

## Los dos atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictado puro**: transcribe lo que dices (con vista previa en vivo en pantalla) y lo pega donde tengas el cursor. |
| `Ctrl + Shift + Espacio` | **Asistente IA local**: analiza lo dictado. Si es información → resumen. Si es una petición ("escríbeme un correo formal sobre...", "explícame X", "hazme una lista de...") → la ejecuta y pega el resultado. |

`Esc` cancela una grabación en curso.

## Componentes (todo local)

| Pieza | Función | Modelo |
|---|---|---|
| [Handy](https://handy.computer) | Captura de voz + transcripción + pegado | Nemotron Streaming 3.5 (0.6B, GPU vía Vulkan) |
| [Ollama](https://ollama.com) | Motor de IA de texto local | Qwen3.5-9B (resúmenes, correos, explicaciones...) |

## Instalación en un PC nuevo

1. Copia o clona esta carpeta en el PC.
2. Ejecuta `scripts\install.ps1` (clic derecho → *Ejecutar con PowerShell*).
   - Instala Handy y Ollama (vía winget), descarga los modelos y aplica la configuración de Handy.
3. Abre **Handy** desde el menú Inicio y elige tu micrófono en Ajustes.
4. Prueba: `Ctrl + Alt + Espacio` (dictado) y `Ctrl + Shift + Espacio` (asistente).

Requisitos: Windows 11, unos 12 GB de disco libre (modelos incluidos). GPU NVIDIA con Vulkan acelera la transcripción (también funciona en CPU).

## Ejemplos de uso con `Ctrl + Shift + Espacio`

- *(información)* "...reunión de ayer: la línea 3 parada, repuesto el jueves 18, coste 2400 euros..." → **resumen** con datos clave.
- *"Escríbeme un correo formal al proveedor para confirmar la entrega del pedido 4821 antes del día 20"* → **correo formal** listo.
- *"Escríbeme un mensaje coloquial para mi compañero recordándole la reunión de mañana"* → **mensaje informal** (como si lo contaras tú).
- *"Explícame qué es una API REST, rápido"* → **explicación breve**.
- *"Genera un script de Python de una calculadora"* → **código en texto plano** (sin ``` y sin caracteres raros).

## Configuración

- **Atajos**: Handy → Ajustes → Atajos. Haz clic en el atajo y pulsa la combinación nueva.
  (No uses el botón *Reset*: volvería a `Ctrl+Espacio`, que choca con WorkspaceLauncher).
- **Modelo del asistente**: Handy → Ajustes → Post-processing → proveedor `Custom` (Ollama, `http://localhost:11434/v1`).
  Alternativas ya descargadas:
  - `hf.co/jc-builds/Qwen3.5-9B-Q4_K_M-GGUF:Q4_K_M` → mejor calidad (por defecto).
  - `qwen3:4b-instruct` → más rápido, algo menos fino en español.
  - `phi4-mini` → rápido, para resúmenes simples.
- **Prompts**: en `prompts/` de este repo y en Handy → Post-processing → Prompts.
  El activo es **Asistente inteligente (local)** (decide resumen vs petición y maneja el tono).
  Presets intercambiables: *Correo formal* y *Texto coloquial*.

## Estructura

```
asistente-voz-local/
├── README.md
├── config/handy-settings.json   # configuración de Handy lista para aplicar
├── prompts/                     # textos de los prompts (referencia/edición)
│   ├── asistente.md
│   ├── correo-formal.md
│   └── texto-coloquial.md
└── scripts/
    ├── install.ps1              # instalador completo (PC nuevo)
    └── apply-config.ps1         # solo re-aplica configuración
```

## Solución de problemas

- **La IA no responde o da error**: abre Ollama (icono de llama en la bandeja). Debe estar en ejecución.
- **Primera respuesta lenta** (20-40 s): Ollama está cargando el modelo en la GPU. Después responde en 5-15 s.
- **Respuestas más lentas de lo normal**: memoria de la GPU llena (navegador con muchas pestañas, juegos...). Cierra apps pesadas.
- **No aparece el texto**: haz clic en un campo de texto antes de dictar y usa el atajo correcto.
- **Caracteres raros (▁, ```)**: no cambies el asistente a `gemma3n` — tiene un bug conocido que inyecta caracteres de bloque.
- **Historial**: Handy guarda las últimas transcripciones (icono de bandeja → ventana principal).

## Reutilizar en otro ordenador

1. `install.ps1` instala y configura todo automáticamente.
2. Si el PC tiene menos VRAM (4-6 GB), usa `qwen3:4b-instruct` como modelo del asistente.
3. Si tienes repositorio remoto: `git push` aquí y `git clone` en el otro PC.

---

*Generado como parte de la configuración del asistente de voz local — Octubre 2026.*
