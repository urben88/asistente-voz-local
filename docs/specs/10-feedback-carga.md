# Spec 10 — Feedback de carga en la píldora

Estado: implementada e instalada en este PC (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Que al pulsar `Ctrl+Alt+R` se vea **qué está haciendo** el lector: si está cargando el modelo
(piper/kokoro al arrancar, o Chatterbox/XTTS que tardan 20-30 s) o generando la primera frase.
Antes, con un motor lento, el atajo no daba ninguna señal hasta que había audio.

## R1. Carga en segundo plano

- `Lector.__init__` ya no carga el motor (bloqueaba el arranque y el registro del atajo).
- `Lector.cargar_en_segundo_plano()` lanza `_cargar_motor()` en un hilo; `main()` la llama justo
  después de crear la píldora, así el atajo ya responde mientras carga.
- `_cargar_motor()` deja `estado = "cargando"` y `cargando_desde = monotonic()`; al terminar vuelve a
  `"inactivo"`. El fallo sigue siendo no fatal (pitido + log).
- `--probar` carga el motor de forma síncrona (sin píldora).

## R2. Estado «cargando» en la píldora

- Nuevo estado `cargando`: la píldora se ensancha (210-260 px) y muestra un **aro girando** y
  **«Cargando voz… N s»** (los segundos suben para verse que avanza), con la X para parar.
- Al pulsar el atajo mientras carga: `cargando_visible = True` y `_leer_cuando_listo = True`; la
  píldora aparece con ese aviso y, en cuanto el modelo termina, **empieza la lectura sola**.
- La carga inicial al iniciar sesión es silenciosa (`cargando_visible = False`): no aparece la
  píldora si el usuario no ha pedido nada.
- Al recargar la voz por un cambio de configuración (mtime de `lector.json`) también se muestra
  `cargando` (y luego se lee con la voz nueva).
- El latido `lector-vivo.json` incluye `"estado": "cargando"`, y el panel muestra
  «cargando la voz…» / «Cargando la voz (chatterbox)… en cuanto esté, lista para leer».
- La fuente del texto es la del sistema (`segoeui.ttf`; si no, `DejaVuSans`/`arial`, y si no la de
  PIL). El texto se dibuja al supermuestreo de la píldora para que no salga borroso.

## R3. Sin regresiones

- Los estados anteriores siguen igual (`preparando` gris con barras, `leyendo` rosa, `aviso` gris).
- El vigilante de la spec 07 se mantiene; para motores con `carga_lenta` (Chatterbox/XTTS) el
  margen en «preparando» sube a 240 s.

## Verificación

- [x] Con un motor falso de 6 s: pulsar el atajo mientras carga muestra «Cargando voz… 4 s» con el
      aro; al terminar arranca la lectura sola; luego `leyendo` y, al acabar, la píldora desaparece.
      Capturas: `%TEMP%\opencode\pildora-cargando-5s.png`, `pildora-leyendo.png`.
- [x] Carga real de Chatterbox al arrancar: log «Cargando Chatterbox (es) en cuda» → 28 s →
      «Listo (voz chatterbox:es, 24000 Hz)»; el latido pasa por `"estado": "cargando"` y la píldora
      no aparece sola.
- [x] El panel muestra el estado de carga y luego «En marcha con chatterbox · por defecto».
- [ ] Prueba del usuario: pulsar Ctrl+Alt+R justo al encender el lector con Chatterbox y ver el aviso.
