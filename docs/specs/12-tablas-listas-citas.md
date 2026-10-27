# Spec 12 — Leer tablas, listas y citas como se entienden (no como filas crudas)

Estado: implementada e instalada (2026-10-20), sin commit.
Fecha: 2026-10-20

## Objetivo

Con XTTS (y cualquier motor), una tabla se oía como una lista de palabras sueltas
(«Pieza, Estado, Notas. Handy, OK, Whisper Turbo.») y las tablas largas se cortaban con
«Y N filas más» sin contexto. El usuario pide que se lea **como se entiende**: anunciar la tabla,
sus columnas y leer cada fila diciendo a qué columna pertenece cada valor; listas y títulos
naturales; sin leer los números de índice ni las filas de separación.

## R1. Tablas

- La primera fila es la **cabecera**; la fila de guiones (`| --- |`) nunca se lee.
- Se anuncia: «Tabla de N columnas: Col1, Col2, Col3.» y «M filas.» (solo si hay 2+ columnas).
- Cada fila se lee como una frase con el nombre de la columna: «Col1: valor; Col2: valor.»
  Los valores vacíos se omiten (no se dice «Estado: » en blanco).
- **Columna de índice** (`#`, `N`, `Nº`, `ID`…) con números correlativos: se elimina y **no se lee**
  («1», «2»… no suenan).
- Hasta **10 filas**; si hay más: «Y K filas más.» (antes eran 5 y se cortaba antes).
- Celdas con emojis/HTML/enlaces se limpian con las reglas de la spec 08.

## R2. Listas, casillas y citas

- Listas: cada punto es una frase (sin leer el guion ni el número).
- Casillas: `- [x] …` → «Hecho: …»; `- [ ] …` → «Pendiente: …».
- Citas (`>`): se anuncia una vez al empezar el bloque → «Cita: …» (no en cada línea).
- Títulos: frase propia, con la pausa normal al final.

## R3. XTTS

- La velocidad del panel (`velocidad`) se pasa a XTTS (`speed`); si la versión no lo admite, se
  ignora sin romper. El lector queda en **XTTS en GPU** con velocidad 1.0.
- El resto (pausas por signo, limpieza, selección, píldora) sigue igual.

## Verificación

- [x] `lector/pruebas_filtro.py`: 53 comprobaciones, 0 fallos (incluye tabla con columnas, fila de
      índice fuera, tabla larga resumida, casillas y cita).
- [x] Ejemplo real de chat: «Tabla de 3 columnas: Pieza, Estado, Notas. 6 filas. Pieza: Handy;
      Estado: OK; Notas: Whisper Turbo.»; «Hecho: …», «Pendiente: …», «Cita: …».
- [x] XTTS acepta `speed` (1.0 → 5,86 s de audio; 1.15 → 5,63 s) sin errores.
- [ ] Prueba de oído del usuario con una tabla y una lista reales.
