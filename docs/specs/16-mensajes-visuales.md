# Spec 16 — Mensajes visuales del lector (apagado, sin texto, error, carga)

Estado: implementada e instalada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Que el usuario sepa siempre **por qué** no lee: apagado, sin texto, error de voz o cargando.
Antes, si el lector estaba apagado no pasaba nada (el proceso ni existía) y un fallo de voz solo
pitaba.

## R1. Píldora con mensajes

- `dibujar()` acepta texto y, si lo hay, pinta punto de color + mensaje (sin barras ni X) y se
  ensancha. Estados:
  - `cargando`: aro girando + «Cargando voz… N s» (ya existía).
  - `aviso`: punto gris + «Nada que leer» (2 s).
  - `error`: punto rojo + «No se pudo cargar la voz» (5 s).
- El lector guarda `aviso_texto/aviso_hasta` y `error_texto/error_hasta`; la píldora los muestra
  aunque el estado ya sea `inactivo`, y los mantiene mientras se desvanece.

## R2. Lector apagado: avisa el panel

- Con el lector apagado no hay proceso que muestre la píldora, así que el **panel** registra
  `Ctrl+Alt+R` mientras el lector está apagado y muestra un **aviso flotante** abajo al centro:
  «Lector apagado. Enciéndelo en el panel (Ctrl+Alt+P).» (`panel/toast.py`, 3,5 s, sin robar foco).
- Traspaso del atajo: al **encender**, el panel suelta `Ctrl+Alt+R` (WM_QUIT a su hilo + join) y
  arranca el lector, que lo registra él. Al **apagar**, se registra el panel cuando el lector ya se
  fue. Al arrancar el panel con el lector apagado, se registra; con el lector encendido, no.
- El auto-reinicio del lector suelta el atajo antes de arrancarlo, por si acaso.

## R3. Sin elegir nada

Se retira el selector «Qué leer»: siempre **selección → si no, portapapeles**.

## Verificación

- [x] Capturas: píldora «Nada que leer» (gris) y «No se pudo cargar la voz» (roja), y aviso
      flotante «Lector apagado…».
- [x] Con `estado.json` `lector: false`: el panel arranca, registra `Ctrl+Alt+R` (otro proceso no
      puede registrarlo) y no hay lector.
- [x] Con `lector: true`: el panel arranca el lector, XTTS carga y el atajo queda registrado por el
      lector (otro proceso no puede).
- [ ] Prueba del usuario: apagar desde el panel y pulsar `Ctrl+Alt+R` (debe salir el aviso);
      encender y comprobar que lee.
