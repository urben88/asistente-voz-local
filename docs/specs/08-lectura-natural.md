# Spec 08 — Lectura natural: filtro de lo que no se lee + pausas

Estado: aprobada (petición del usuario 2026-10-20), pendiente de implementar.
Fecha: 2026-10-20

## Objetivo

Que el lector lea **solo lo que tiene sentido oír**, sin iconos, emojis, tablas, código, URLs ni
restos de Markdown (chats de agentes, README, notas), y con un ritmo más humano: pausas cortas tras
coma, medias tras dos puntos y punto y aparte entre frases.

## Por qué

El usuario lee chats de agentes con `Ctrl+Alt+R` y oye cosas como «barras verticales», «cuadrado»
o «flecha» cada vez que aparece un icono, una tabla o un emoji, y el texto le llega sin respirar.
La voz le gusta (`es_ES-davefx-medium`); lo que falla es el texto que se le entrega y el ritmo.

## Requisitos

R1. **`lector/leer_md.py` — `md_a_voz(texto)`** (Markdown) debe:
   - Quitar el *frontmatter* YAML del principio (`---` … `---`).
   - Quitar **bloques de código** completos (``` y ~~~) **sin anunciarlos** (nada de «Bloque de
     código, omitido»: es ruido).
   - Quitar **imágenes** (`![alt](url)`) y **URLs desnudas**; en los enlaces `[texto](url)` dejar
     solo `texto`.
   - Quitar **HTML**: etiquetas, comentarios `<!-- -->`, `<br>`; **decodificar** entidades
     (`&amp;`, `&nbsp;`, `&gt;`, `&#39;`…).
   - Quitar **símbolos que no se leen**: emoji y pictogramas (rangos Unicode y categorías `So`,
     `Sk`, `Cf`, `Co`), selectores de variación, ZWJ, flechas, viñetas decorativas (`•`, `▪`, `›`,
     `»`), *box drawing* (`│├└╭╰─`), marcas de estado (`✔ ✓ ☑ ⚠ ⏺ ⎿`). **Conservar** `% € $ + = ·`
     y la puntuación normal.
   - Quitar restos de Markdown: `#` de título, `>` de cita, `*`/`_`/`~` de énfasis, `|` de tabla,
     backticks, `---`, casillas `[ ]`/`[x]`, anclas `{#id}`, referencias `[^1]`.
   - **Código en línea**: quitar las comillas invertidas y conservar el contenido si es corto y
     «hablable» (`Ctrl+Alt+R`, `lector.py`, `API`); si es largo o parece código, omitirlo.
   - Tablas: las de hasta 5 filas se leen por filas; las largas se resumen («Y N filas más»).
   - Descartar líneas de herramienta/consola (`⏺ Bash(...)`, `⎿ …`, `│ …`, `$ comando`, `PS C:\> …`,
     `C:\ruta> …`).
   - Descartar líneas que, tras limpiar, queden vacías o solo con puntuación/símbolos.
   - **No romper palabras**: `snake_case`, `ef_dora`, `es_ES-davefx-medium`, `Ctrl+Alt+R` deben
     sobrevivir; no se comen los `_` internos ni se parten por `-` o `_`.
   - Normalizar: colapsar espacios, quitar espacio antes de `.,;:!?`, eliminar puntuación repetida
     (`..` → `.`), y cerrar cada frase con `.`/`?`/`!`/`…` para que haya pausa.
   - Abreviaturas frecuentes → palabra hablada: `p. ej.` → «por ejemplo», `ej.` → «ejemplo»,
     `etc.` → «etcétera», `n.º`/`nº` → «número», `aprox.` → «aproximadamente», `EE. UU.` →
     «Estados Unidos», `Sr.` → «señor», `Sra.` → «señora», `Dr.` → «doctor», `vs.` → «frente a».
     El diccionario va en una constante para poder ampliarlo.

R2. **Texto normal** (no Markdown): `limpiar()` del lector aplica el mismo saneado de símbolos,
   emoji y URLs, y las mismas abreviaturas. Un solo sitio para las reglas (`leer_md.limpiar_texto()`
   reutilizable por ambos caminos).

R3. **Pausas naturales** (`lector/motor.py`), sin cambiar la interfaz de los motores:
   - `PiperMotor.crear(frase)` añade silencio según el último signo de la frase:
     `.` `!` `?` `…` → `pausa_ms` (por defecto **250**); `:` `;` → 60 % de `pausa_ms`; `,` → 35 %.
   - `pausa_ms` sube a **250** en `config/lector.json`, `CONFIG_DEFECTO` y `LECTOR_DEFECTO` del panel.
   - Piper: `length_scale = 1 / velocidad` (sin cambios); Kokoro igual que ahora.

R4. **Panel**: nueva fila **Velocidad** con tres botones `Lenta` (0.9) / `Normal` (1.0) / `Rápida`
   (1.1) que escribe `velocidad` en `lector.json` (se aplica en caliente, como idioma y voz).

R5. **Pruebas**: `lector/pruebas_filtro.py`, ejecutable con `python lector/pruebas_filtro.py` (sin
   dependencias, sin audio), con un corpus realista de chat de agente y comprobaciones:
   - no quedan emojis/símbolos (comprobado por categoría Unicode y por lista negra),
   - no quedan `|`, backticks, `**`, `#`, `http`, `![`, `<!--`,
   - no aparecen las palabras «barras», «cuadrado», «flecha» (restos de iconos),
   - las frases acaban en `.`/`?`/`!`/`…`,
   - sobreviven `Ctrl+Alt+R`, `lector.py`, `snake_case`, `es_ES-davefx-medium`,
   - abreviaturas expandidas,
   - una tabla corta se lee y una larga se resume,
   - `limpiar_texto` con emojis y URLs deja texto limpio.
   Salida: una línea `OK` por comprobación y código de salida 0/1.

R6. **Sin regresiones**: el lector sigue leyendo Markdown, cortando con el atajo, con la píldora y
   el vigilante de la spec 07; el modo `--probar` sigue funcionando.

## Verificación (en este PC)

- [x] `python lector/pruebas_filtro.py` → 48 comprobaciones, 0 fallos.
- [x] Filtro sobre un corpus realista de chat (frontmatter, emojis, tablas, código, `⏺/⎿`,
      árboles, HTML, entidades, ANSI, URLs, anclas, notas): queda texto limpio, sin símbolos ni
      palabras como «barras» o «flecha».
- [x] Pausas medidas sin reproducir: Piper y Kokoro dan 250 ms tras `. ! ? …`, 150 ms tras `: ;`
      y 88 ms tras `,`.
- [x] Velocidad `Lenta`/`Normal`/`Rápida` escribe 0.9/1.0/1.1 en `lector.json` (aplicado en caliente).
- [ ] Lectura real con audio de un chat con iconos (pendiente de la prueba del usuario).
- [ ] `Ctrl+Alt+R` con el lector residente y dictado funcionando a la vez (pendiente de la prueba
      del usuario; la lógica ya no tiene modos).
