# Spec 13 — Elegir el modelo del resumen desde el panel

Estado: implementada e instalada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Que el usuario pueda cambiar el **modelo de Ollama que usa el resumen** (`Ctrl+Shift+Espacio`)
desde el panel, viendo primero los que tiene instalados y cuáles se recomiendan, sin tener que
entrar en Handy. El prompt y el resto de ajustes de Handy siguen siendo suyos.

## R1. Lista de modelos

- `control.modelos_ollama()` ejecuta `ollama list` y devuelve `[{nombre, mb, nota}]` (caché 10 s).
- `RECOMENDADOS_RESUMEN` marca con ★ los que mejor van para resumir en este equipo:
  `gemma4:e4b` (el que usa), `qwen3:4b-instruct`, `phi4-mini:latest`, `qwen2.5:3b-instruct`.
- Los modelos de 4,5 GB o más llevan aviso: «⚠ grande: con el lector en la GPU puede no caber y
  tardar más».

## R2. Cambiarlo desde el panel

- Pestaña **Resumen → Modelo de resumen**: desplegable con todos los modelos instalados (el activo
  preseleccionado), botón **Usar** y una línea con la nota del modelo y su tamaño.
- `control.cambiar_modelo_resumen(modelo)`:
  1. Cierra Handy (WM_CLOSE; forzado si no se va en 5 s), porque Handy reescribe su configuración
     al salir.
  2. Copia `settings_store.json` a `.bak-panel`.
  3. Escribe `settings.post_process_models[<proveedor>] = modelo` (proveedor actual, normalmente
     `custom`), conservando el resto; escritura atómica y JSON validado.
  4. Verifica que se guardó y vuelve a abrir Handy.
- Si algo falla, se vuelve a abrir Handy y se informa; la copia `.bak-panel` queda para restaurar a
  mano.
- El panel muestra el resultado en la línea de mensajes («Resumen con X (antes: Y). Handy
  reiniciado.»).

## R3. Lo que NO cambia

- El **prompt** de post-procesado sigue configurándose en Handy (se muestra en la pestaña).
- No se tocan micrófono, atajos, claves ni el resto de ajustes.

## Verificación

- [x] `ollama list` → 16 modelos con tamaño y nota; ★ en `gemma4:e4b` y los ligeros; aviso en los
      de 6 GB.
- [x] Cambio real a `qwen3:4b-instruct`: Handy cerrado y reabierto, `post_process_models.custom`
      actualizado y verificado.
- [x] Restaurado a `gemma4:e4b` (el que usaba) y Handy en marcha.
- [x] UI: desplegable + «Usar» + nota del modelo, con la ayuda «?» correspondiente.
- [ ] Prueba del usuario haciendo un resumen con el modelo que elija.
