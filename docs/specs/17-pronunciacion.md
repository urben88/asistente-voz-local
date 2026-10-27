# Spec 17 — Pronunciación: inglés, siglas y números

Estado: implementada e instalada (2026-10-27), pendiente de la prueba de oído del usuario.
Fecha: 2026-10-27

## Objetivo

Que la voz española (XTTS «Luis Moray») diga bien lo que hay en los textos de agentes, `.md` y webs:
- palabras inglesas sueltas sonando a inglés (no leídas «a la española»),
- frases enteras en inglés dichas en inglés, con la misma voz,
- siglas, números, versiones, unidades, horas y fechas como los diría una persona.

## Por qué

XTTS no admite fonemas: solo texto. Hay dos formas de cambiar cómo suena algo:
1. **Reescribirlo con letras españolas** («deploy» → «diplói»). Vale para todos los motores y no añade espera.
2. **Pedir el trozo a XTTS con `language="en"`** y la misma voz. Solo XTTS; cada trozo es una generación más y con
   1–2 palabras no es fiable, así que solo se usa con trozos largos.
Además, el limpiador de XTTS lee «12,5» como «doce punto cinco».

No se usa la voz inglesa (`voces.en`) para los trozos en inglés: cambiaría de voz a media frase.

## Requisitos

R1. **Etapa nueva, `lector/pronunciar.py`**, que se aplica **después** de `md_a_voz`/`limpiar` y de `trocear`,
    frase a frase, **antes** del motor. No cambia `leer_md.py` ni las pruebas de la spec 08 (siguen 53/53).
    Solo actúa si `idioma == "es"`; con `en` devuelve la frase tal cual.

R2. **API**: `segmentos(frase, idioma="es", ingles=False) -> list[tuple[str, str]]` con pares `(texto, idioma)`.
    - Con `ingles=False` (Piper, Kokoro, Chatterbox o la opción apagada): un solo segmento `(frase_preparada, "es")`.
    - Con `ingles=True` (XTTS y `ingles_xtts` activo): los tramos en inglés de **3 palabras o más** salen como
      `(tramo, "en")` sin reescribir; el resto se prepara en español. Si un tramo tiene menos de 3 palabras, va en
      español con el diccionario (R3).
    - Nunca devuelve segmentos vacíos ni solo de puntuación.

R3. **Diccionario de anglicismos** (constante `ANGLICISMOS`, ampliable con un `pronunciacion.json` opcional junto a
    `lector.json`: `{"palabras": {"deploy": "diplói"}, "siglas_deletreadas": [...], "siglas_palabra": {...}}`).
    - Sin distinguir mayúsculas, palabra entera, plurales simples (`commits` → «cómits»).
    - Vocabulario de agentes y desarrollo: commit, push, pull, pull request, merge, branch, deploy, build, debug,
      prompt, token, script, framework, frontend, backend, feature, bug, fix, issue, release, tag, hook, test,
      log, plugin, skill, agent, workflow, setup, update, upload, download, server, cloud, cache, browser, chat,
      email, online, link, click, shortcut, software, hardware, driver, streaming, web, website, README,
      Markdown, GitHub, Claude, OpenAI, Windows, Linux, Python, Ollama, etc. (≥ 80 entradas).
    - Respuesta con ortografía española que suene a la pronunciación inglesa habitual en España («commit» →
      «cómit», «push» → «push» si ya suena bien; no forzar lo que XTTS ya dice bien).

R4. **Siglas**: lista de deletreadas (API → «a pe i», GPU, CPU, URL, USB, PDF, HTML, CSS, SQL, SSH, IA, PC, TTS,
    VRAM → «uve ram», MCP, CLI, UI, UX, ID, IP, RAM, SSD…) y de las que se leen como palabra (JSON → «yéison»,
    YAML → «yámel», NASA, OTAN, ONG…). Las siglas en mayúsculas de 2–5 letras que no estén en ninguna lista se
    deletrean solo si no tienen vocales. Nombres de letra en español (a, be, ce, de, e, efe, ge, hache, i, jota,
    ka, ele, eme, ene, o, pe, cu, erre, ese, te, u, uve, uve doble, equis, i griega, zeta).

R5. **Números y formatos** (con `num2words`, `lang="es"`; añadir `num2words` a `lector/requirements.txt` e
    importarlo con protección: si falta, se deja el número como está):
    - Decimal con coma: «12,5» → «doce coma cinco». Miles con punto: «1.000» → «mil».
    - Versiones: «v2.1», «v0.3.4», «Python 3.12» → «versión dos punto uno», «cero punto tres punto cuatro»…
    - Unidades tras número: `GB` «gigas», `MB` «megas», `KB` «kilobytes», `TB` «teras», `ms` «milisegundos»,
      `s` «segundos», `min` «minutos», `h` «horas», `km`, `kg`, `cm`, `mm`, `°C` «grados», `%` «por ciento»,
      `€` «euros», `$` «dólares», `2x` → «dos veces», `1920x1080` → «… por …». Singular con 1 («1 GB» → «una giga»/«un giga»).
    - Horas «10:16» → «diez y dieciséis»; fechas «2026-10-27» y «27/10/2026» → «veintisiete de octubre de dos mil
      veintiséis».
    - Rangos «3 a 5» y «3-5» (solo números cortos, no fechas) → «de tres a cinco».
    - Ordinales «1.º», «2ª» → «primero», «segunda».
    - Archivos y teclas: «lector.py» → «lector punto pai», extensiones (`.md` «punto eme de», `.py` «punto pai»,
      `.json` «punto yéison», `.txt`, `.exe`, `.ps1`, `.sh`, `.js`, `.ts`, `.html`); `Ctrl+Alt+R` → «control alt
      erre». `+` entre teclas → espacio.
    - El resto de números enteros → palabras (para que todos los motores suenen igual).

R6. **Detección de inglés** (sin librerías nuevas): por palabra se clasifica como inglés si está en una lista de
    palabras funcionales inglesas (the, is, are, of, to, and, you, with, this, that, for, it, be, not, can, will,
    have, from, your, what, how, when, we, they, should, would, there, which, an, do, does…) o en `ANGLICISMOS`;
    como español si está en una lista de funcionales españolas (el, la, de, que, y, en, los, es, por, para, con,
    un, una, se, no, lo, del, al…); el resto es neutro. Un tramo inglés es una racha de palabras inglesas o
    neutras, con **≥ 3 palabras**, **≥ 2 inglesas y al menos 1 funcional inglesa**, sin funcionales españolas;
    los bordes neutros se quedan en español. La puntuación final del tramo va con él.

R7. **Motor XTTS**: `XttsMotor.crear_segmentos(segmentos)` genera cada segmento con su idioma (misma voz y
    velocidad), los une con 40 ms de silencio y pone la pausa por signo solo al final. `crear(frase)` sigue igual.
    Los demás motores no cambian.

R8. **Lector**: en `_leer`, cada frase pasa por `pronunciar.segmentos(frase, idioma, ingles=...)`, con
    `ingles = motor.motor == "xtts" and cfg.get("ingles_xtts", True)`. Un segmento → `motor.crear(texto)`; varios
    → `motor.crear_segmentos(...)`. Si `pronunciar` falla, se lee la frase original (log de aviso, sin cortar).
    `ingles_xtts: true` en `config/lector.json` y en `CONFIG_DEFECTO`.

R9. **Pruebas** en `lector/pruebas_filtro.py` (sin audio): anglicismos, siglas, decimales, miles, versiones,
    unidades, horas, fechas, rangos, ordinales, archivos, `Ctrl+Alt+R`, frase española con una palabra inglesa
    (un segmento `es`), frase con «you should run the tests first» (un segmento `en`), frase solo inglesa, texto
    con idioma `en` sin tocar, y que las 53 pruebas previas siguen pasando.

R10. **Prueba de oído** `lector/probar_pronunciacion.py`: genera con XTTS tres WAV de la misma frase mezclada
    (todo en español sin preparar / preparada sin inglés / con tramos en inglés) en una carpeta dada y escribe el
    tiempo de cada uno. Se ejecuta con el venv instalado; si no hay VRAM con el lector residente, se para el
    lector, se prueba y se vuelve a arrancar.

R11. **Instalación**: se copia a `%LOCALAPPDATA%\asistente-voz-local\lector` (`pronunciar.py`, `motor.py`,
    `lector.py`, pruebas, requirements), se añade `"ingles_xtts": true` al `lector.json` instalado sin tocar el
    resto y se reinicia el lector (latido en `inactivo`).

## Verificación

- [x] `python lector/pruebas_filtro.py` → 91 OK, 0 fallos (53 previas + 38 nuevas).
- [x] Tres WAV de la prueba de oído (párrafo de ~14 s de audio): generan en 7,5 s sin preparar, 9,4 s preparada y 9,2 s con inglés (por el mismo camino que Ctrl+Alt+R).
- [x] Lector reiniciado con XTTS y `ingles_xtts` activo («Listo (voz xtts:Luis Moray)»).
- [ ] Prueba de oído del usuario con un chat real.
