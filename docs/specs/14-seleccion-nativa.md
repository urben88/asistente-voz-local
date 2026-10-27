# Spec 14 — Detectar la selección de forma nativa en Windows (sin copiar)

Estado: implementada e instalada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Investigación (lo que dice Windows)

No existe una API global de «texto seleccionado»: la selección es cosa de cada aplicación.
Lo nativo y correcto es, por este orden:

1. **UI Automation · `IUIAutomationTextPattern::GetSelection`** (MS Learn,
   `uiautomationclient.h`): devuelve los rangos seleccionados del control de texto con el foco, sin
   efectos secundarios. Requiere que la app exponga `TextPattern` (Chrome/Edge/Electron, Office,
   Notepad, WinUI…). Algunas apps lo exponen en un hijo (el documento), no en el control con el foco.
2. **Consola clásica (conhost)**: `GetConsoleSelectionInfo` da la selección (ancla y rectángulo) y
   `ReadConsoleOutputCharacter` lee esas celdas del búfer. Nativo, sin portapapeles. Requiere
   `AttachConsole(pid)` y un handle a `CONOUT$` (tras `AttachConsole`, `GetStdHandle` no sirve).
3. **Respaldo universal**: `Ctrl+C` simulado + lectura del portapapeles + restauración (lo que ya
   había). Es lo único que funciona con apps sin accesibilidad y con visores de PDF.

Referencias: MS Learn (`GetSelection`, `GetConsoleSelectionInfo`, `ReadConsoleOutputCharacter`),
StackOverflow («get selected text from any window», «read current text selected in console
window») y el proyecto `0xfullex/selection-hook` (UIA + consola + Ctrl+C como último recurso).

Límites reales:
- **Escritorio remoto**: la sesión remota es otro escritorio; UI Automation y la consola locales solo
  ven la ventana `TscShellContainerClass`. Ahí solo funciona el Ctrl+C (que RDP redirige).
- **Windows Terminal**: no es conhost; su texto va por UIA (si lo expone) o por Ctrl+C.
- **Apps sin accesibilidad** (algunos Electron/PDF): Ctrl+C.

## Implementación (`lector/seleccion.py`)

- `_por_uia()`: foco y hasta 4 padres; si no hay, baja por el árbol (hasta 3 niveles, 60 nodos)
  buscando un `TextPattern` con selección. Sin efectos.
- `_por_consola()`: si la ventana con el foco es `ConsoleWindowClass`, `FreeConsole` (por si el
  proceso ya tiene una), `AttachConsole(pid)`, `GetConsoleSelectionInfo` (exige
  `CONSOLE_SELECTION_NOT_EMPTY`), lectura por filas con `ReadConsoleOutputCharacterW` desde
  `CONOUT$`, y `FreeConsole` al terminar.
- `texto_seleccionado()`: UIA → consola → Ctrl+C (con restauración). El lector ya lo usa antes del
  portapapeles (`leer_seleccion`).

## Verificación

- [x] Consola real (conhost + `cmd.exe`): arrastre de ratón y `_por_consola()` devuelve el texto
      **sin tocar el portapapeles** (se leyó «E TEXTO D» de una selección parcial del arrastre).
- [x] `AttachConsole` + `CONOUT$` funcionan; con `GetStdHandle(-11)` la lectura falla (por eso se
      usa `CONOUT$`).
- [x] Sin selección: devuelve `""` sin errores (UIA, consola y Ctrl+C).
- [x] El foco en una ventana de Escritorio remoto no rompe nada: UIA/consola devuelven `""` y queda
      el Ctrl+C.
- [ ] Prueba del usuario: seleccionar en Chrome/consola y pulsar `Ctrl+Alt+R`.
