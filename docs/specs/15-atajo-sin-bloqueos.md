# Spec 15 — Ctrl+Alt+R sin bloqueos y selección automática

Estado: implementada e instalada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Síntoma

El usuario: «no me va Ctrl+Alt+R». Comprobado: el atajo estaba **registrado** (nadie más podía
registrarlo), el audio funcionaba (oyó un tono de prueba) y el log tenía lecturas recientes. Pero al
pulsar no aparecía ni la píldora.

## Causa

El hilo del atajo se quedaba **bloqueado**, así que Windows seguía considerando el atajo «ocupado»
pero el mensaje no se atendía:

1. `texto_seleccionado()` llamaba a UI Automation **en el hilo del atajo**. Si la app con el foco
   tenía una implementación lenta/colgada (o la ventana de Escritorio remoto), la llamada podía
   tardar indefinidamente.
2. `_recargar_config()` (cuando el panel cambiaba `lector.json`: voz, velocidad, idioma) cargaba el
   motor **en el hilo del atajo**: con XTTS son 15-30 s sin píldora ni respuesta. Y cada pulsación
   volvía a intentarlo, porque el mtime no se actualizaba hasta terminar.

## Arreglo

- `seleccion.texto_seleccionado(..., timeout=2.0)`: UIA → consola → Ctrl+C dentro de un hilo
  daemon con **límite de 2 s**. Si no contesta, se usa el portapapeles y se registra en el log.
  El hilo del atajo solo hace comprobaciones de fichero (rápidas) y lanza hilos.
- Configuración cambiada: `_recargar_en_segundo_plano()`; la píldora muestra «Cargando voz…» y al
  terminar **se lee solo** (`_leer_cuando_listo`). Si ya hay una carga en curso, no se lanza otra.
- **Selección automática**: se quita el selector «Qué leer» del panel. Siempre: selección si la hay
  → si no, último copiado. `leer_seleccion` queda en `true` y no hay que elegir nada.

## Verificación

- [x] El atajo está registrado tras el reinicio (no se puede registrar desde fuera).
- [x] Lector con XTTS cargado y latido en `inactivo`.
- [x] `texto_seleccionado` con límite: devuelve `""` sin bloquear si UIA no contesta.
- [x] Panel sin «Qué leer»; `lector.json` con `leer_seleccion: true`.
- [ ] Prueba del usuario: seleccionar y pulsar; sin selección, debe leer el portapapeles.
