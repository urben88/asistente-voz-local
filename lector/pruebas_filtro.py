"""Pruebas del filtro de lectura natural (specs 08 y 17). Sin audio.

Uso:  python lector/pruebas_filtro.py
Salida: una linea "OK ..." por comprobacion; codigo 0 si todo pasa, 1 si no.
"""

import sys
import unicodedata

from leer_md import limpiar_texto, md_a_voz
from pronunciar import generar, num2words, segmentos

CORPUS = (
    r"""---
title: Demo de lectura
tags: [prueba, voz]
---

# Lectura natural

Texto con **negrita**, `lector.py`, `snake_case` y `es_ES-davefx-medium`.
El atajo es `Ctrl+Alt+R` y sirve p. ej. para leer apuntes, etc.

- [x] tarea hecha ✅
- [ ] pendiente ⚠️
- Usa Node.js y C++ sin romper e-mail.

![diagrama](https://ejemplo.com/x.png)

Enlace [documentación](https://ejemplo.com/docs) y URL suelta https://ejemplo.com/suelta.
Vive en EE. UU. desde 2020 y el piso n.º 3 es aprox. 80 m².
"""
    + "\x1b[31mTexto en rojo\x1b[0m\n"
    + r"""```python
print("hola")  # esto no se lee
```

| Voz | Idioma |
| --- | --- |
| davefx | es |
| amy | en |

| N | Valor |
|---|---|
| 1 | uno |
| 2 | dos |
| 3 | tres |
| 4 | cuatro |
| 5 | cinco |
| 6 | seis |
| 7 | siete |

⏺ Bash(python lector.py --probar)
⎿ salida del comando
│ ├── rama
PS C:\Users\tirol> dir
$ echo hola

> Esto es una cita.

Ancla {#seccion} y nota [^1].

HTML <br> y entidad &amp; lista.
Simbolos → › » y marcos │ ├ └.
"""
)

# Rangos que el filtro debe eliminar (los mismos que leer_md, resumidos)
RANGOS_PROHIBIDOS = (
    (0x2190, 0x21FF), (0x2300, 0x23FF), (0x2460, 0x24FF), (0x25A0, 0x25FF),
    (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0x1F000, 0x1FAFF), (0xFE00, 0xFE0F),
)
LISTA_NEGRA = set("✅🔗⚠️🚀→›»│├└⏺⎿•▪☑✔■□●○")

fallos = []


def comprobar(nombre, condicion, detalle=""):
    if condicion:
        print(f"OK   {nombre}")
    else:
        print(f"FALLO {nombre}" + (f" -> {detalle}" if detalle else ""))
        fallos.append(nombre)


def simbolos_prohibidos(texto):
    malos = []
    for caracter in texto:
        if caracter in "%€$+=·°":
            continue
        if caracter in LISTA_NEGRA:
            malos.append(caracter)
            continue
        codigo = ord(caracter)
        if any(a <= codigo <= b for a, b in RANGOS_PROHIBIDOS):
            malos.append(caracter)
        elif unicodedata.category(caracter) in ("So", "Sk", "Cf", "Co"):
            malos.append(caracter)
    return malos


def main():
    salida = md_a_voz(CORPUS)
    print("--- salida md_a_voz ---")
    print(salida)
    print("--- fin ---")

    malos = simbolos_prohibidos(salida)
    comprobar("sin emojis ni simbolos", not malos,
              "quedan: " + " ".join(repr(c) for c in dict.fromkeys(malos)))

    for resto, nombre in (
        ("|", "sin barras verticales"),
        ("`", "sin backticks"),
        ("**", "sin negritas"),
        ("#", "sin almohadillas"),
        ("http", "sin URLs"),
        ("![", "sin imagenes"),
        ("<!--", "sin comentarios HTML"),
    ):
        comprobar(nombre, resto not in salida, salida)

    for palabra in ("barras", "cuadrado", "flecha", "omitido"):
        comprobar(f"sin «{palabra}»", palabra not in salida.lower() if palabra.islower()
                  else palabra not in salida, salida)

    lineas = [linea for linea in salida.splitlines() if linea.strip()]
    comprobar("frases cerradas", all(linea.strip()[-1] in ".!?…" for linea in lineas),
              " | ".join(linea for linea in lineas if linea.strip()[-1] not in ".!?…"))

    for resto, nombre in (
        ("Ctrl+Alt+R", "sobrevive Ctrl+Alt+R"),
        ("lector.py", "sobrevive lector.py"),
        ("snake_case", "sobrevive snake_case"),
        ("es_ES-davefx-medium", "sobrevive es_ES-davefx-medium"),
        ("Node.js", "sobrevive Node.js"),
        ("C++", "sobrevive C++"),
        ("e-mail", "sobrevive e-mail"),
    ):
        comprobar(nombre, resto in salida, salida)

    for palabra, nombre in (
        ("por ejemplo", "p. ej. expandido"),
        ("etcétera", "etc. expandido"),
        ("Estados Unidos", "EE. UU. expandido"),
        ("número", "n.º expandido"),
        ("aproximadamente", "aprox. expandido"),
    ):
        comprobar(nombre, palabra in salida, salida)
    for resto in ("p. ej.", "etc.", "EE. UU.", "n.º", "aprox."):
        comprobar(f"sin abreviatura {resto}", resto not in salida, salida)

    comprobar("bloque de codigo sin leer", "print" not in salida, salida)
    comprobar("bloque de codigo anunciado una vez",
              salida.count("Aquí hay un bloque de código.") == 1, salida)
    comprobar("consola anunciada una vez",
              salida.count("Aquí hay una salida de consola.") == 1, salida)
    comprobar("salida del comando sin leer",
              "salida del comando" not in salida and "echo hola" not in salida, salida)
    comprobar("texto rojo (ANSI) conservado", "Texto en rojo" in salida, salida)
    comprobar("sin secuencias ANSI", "\x1b" not in salida, repr(salida))
    comprobar("frontmatter fuera", "title: Demo" not in salida, salida)
    comprobar("cita leida", "Esto es una cita" in salida, salida)
    comprobar("ancla y nota al pie fuera", "seccion" not in salida and "^1" not in salida, salida)
    comprobar("entidad decodificada", "entidad & lista" in salida, salida)

    corta = md_a_voz("| Voz | Idioma |\n| --- | --- |\n| davefx | es |\n| amy | en |\n")
    comprobar("tabla anuncia columnas", "Tabla de 2 columnas: Voz, Idioma." in corta, corta)
    comprobar("tabla con nombre de columna", "Voz: davefx; Idioma: es." in corta, corta)
    comprobar("tabla sin guiones", "---" not in corta, corta)

    con_indice = md_a_voz("| # | Tarea |\n| --- | --- |\n| 1 | comprar |\n| 2 | vender |\n")
    comprobar("columna de indice fuera",
              "1:" not in con_indice and "Tarea: comprar" in con_indice, con_indice)

    casillas = md_a_voz("- [x] tarea hecha\n- [ ] tarea pendiente\n")
    comprobar("casillas hechas/pendientes",
              "Hecho: tarea hecha." in casillas and "Pendiente: tarea pendiente." in casillas,
              casillas)

    cita = md_a_voz("> Primera linea de la cita\n> segunda linea\n\nTexto normal.\n")
    comprobar("cita se anuncia una vez",
              "Cita: Primera linea de la cita" in cita and "Cita: segunda" not in cita, cita)

    filas = "\n".join(f"| {i} | valor {i} |" for i in range(1, 14))
    larga = md_a_voz("| N | Valor |\n| --- | --- |\n" + filas + "\n")
    comprobar("tabla larga se resume",
              "Y 3 filas más." in larga and "valor 13" not in larga, larga)

    limpio = limpiar_texto("Hola ✅ https://ejemplo.com/a 🔗 mundo ⚠️ 🚀")
    comprobar("limpiar_texto sin emojis", not simbolos_prohibidos(limpio), limpio)
    comprobar("limpiar_texto sin URLs", "http" not in limpio, limpio)
    comprobar("limpiar_texto conserva palabras", "Hola" in limpio and "mundo" in limpio, limpio)
    comprobar("limpiar_texto no deja lineas vacias",
              all(linea.strip() for linea in limpio.splitlines()), repr(limpio))

    # Regresiones del ritmo y la puntuacion (2026-10-20)
    guion = md_a_voz("He revisado todo —de arriba abajo—. Quedan dos cosas:")
    comprobar("guion largo sin coma+punto", ",." not in guion and "funciona,." not in guion, guion)
    comprobar("dos puntos conservados", guion.rstrip().endswith(":"), guion)

    abreviado = md_a_voz("Aprox. 25 metros y el Dr. Perez llego tarde.")
    comprobar("abreviatura al inicio capitalizada", abreviado.startswith("Aproximadamente"), abreviado)
    comprobar("abreviatura en medio en minuscula", "el doctor Perez" in abreviado, abreviado)

    # Pronunciacion (spec 17)
    def es(frase):
        partes = segmentos(frase, "es")
        return partes[0][0] if len(partes) == 1 and partes[0][1] == "es" else repr(partes)

    def dice(nombre, frase, esperado):
        salida = es(frase)
        comprobar(nombre, esperado in salida, salida)

    dice("anglicismo reescrito", "Haz commit del README en GitHub.", "cómit del Rídmi en Guíjab")
    dice("anglicismo en plural", "Revisa los commits.", "cómits")
    dice("multipalabra", "Abre un pull request.", "pul ricuést")
    dice("sigla deletreada", "La API y la GPU.", "a pe i y la ge pe u")
    dice("sigla como palabra", "Un archivo JSON.", "yéison")
    dice("sigla sin vocales", "Usa BBDD.", "be be de de")
    dice("teclas", "Pulsa Ctrl+Alt+R.", "control alt erre")
    dice("archivo", "Abre lector.py.", "lector punto pai")
    dice("extension suelta", "Lee los .md del repo.", "punto eme de")
    dice("unidades", "Usa 8 GB y tarda 150 ms.", "gigas")
    dice("porcentaje", "Un 25 %.", "por ciento")
    dice("C++ y suma", "C++ y 1+1.", "ce más más")
    if num2words is not None:
        dice("decimal con coma", "En 12,5 segundos.", "doce coma cinco")
        dice("decimal con ceros", "Vale 0,05.", "cero coma cero cinco")
        dice("miles con punto", "Hay 1.000 usuarios.", "mil usuarios")
        dice("version", "Instala la v2.1.3.", "versión dos punto uno punto tres")
        dice("version corta", "Ahora v5.", "versión cinco")
        dice("unidad en singular", "Ocupa 1 GB.", "una giga")
        dice("hora", "A las 10:16.", "diez y dieciséis")
        dice("fecha ISO", "El 2026-10-27.", "veintisiete de octubre de dos mil veintiséis")
        dice("fecha con barras", "El 27/10/2026.", "veintisiete de octubre")
        dice("rango con guion", "Tarda 3-5 minutos.", "de tres a cinco minutos")
        dice("rango con a", "Duerme 3 a 5 horas.", "de tres a cinco horas")
        dice("rango con de", "Pasa de 3 a 5.", "de tres a cinco")
        dice("ordinales", "El 1.º y la 2ª.", "primero y la segunda")
        dice("multiplicador", "Es 2x más rápido.", "dos veces")
        dice("enteros", "Son 53 pruebas.", "cincuenta y tres")
    dice("nombres con guiones intactos", "Voz es_ES-davefx-medium.", "es_ES-davefx-medium")

    una = segmentos("Haz el deploy en el server.", "es", ingles=True)
    comprobar("palabra inglesa suelta va en espanol",
              len(una) == 1 and una[0][1] == "es" and "diplói" in una[0][0], una)
    mixta = segmentos("Claude dijo: you should run the tests first, luego revisa.", "es", ingles=True)
    comprobar("tramo ingles separado",
              [i for _, i in mixta] == ["es", "en", "es"]
              and mixta[1][0] == "you should run the tests first,", mixta)
    solo = segmentos("This is a test of the reader.", "es", ingles=True)
    comprobar("frase inglesa entera", solo == [("This is a test of the reader.", "en")], solo)
    sin = segmentos("Claude dijo: you should run the tests first.", "es", ingles=False)
    comprobar("sin XTTS no se separa", len(sin) == 1 and sin[0][1] == "es", sin)
    comprobar("idioma en sin tocar",
              segmentos("Run the API on 8 GB.", "en") == [("Run the API on 8 GB.", "en")])
    comprobar("nada que leer", segmentos("…", "es", ingles=True) == [])
    dice("siglo en romanos", "El siglo XX.", "siglo XX")

    listas = md_a_voz("Intro:\n\n- uno\n- dos\n  - dos a\n  - dos b\n- tres\n\nFin.\n\n1. paso\n2. paso\n")
    lineas_l = listas.splitlines()
    comprobar("aviso de lista", lineas_l.count("Lista.") == 2, listas)
    comprobar("aviso de sublista antes del anidado",
              "Sublista." in lineas_l and lineas_l[lineas_l.index("Sublista.") + 1] == "dos a.", listas)
    comprobar("una sola sublista", lineas_l.count("Sublista.") == 1, listas)
    tareas = md_a_voz("- [x] hecha\n- [ ] pendiente\n")
    comprobar("aviso de lista de tareas", tareas.startswith("Lista de tareas."), tareas)

    import lector as _lector
    tabla = md_a_voz("| Motor | Calidad | Velocidad |\n| --- | --- | --- |\n"
                     "| Piper | media | rápida |\n| Kokoro | buena | rápida |\n| XTTS | muy buena | lenta |\n")
    trozos_t = _lector.trocear(tabla)
    comprobar("tabla en trozos cortos", len(trozos_t) >= 4 and max(map(len, trozos_t)) <= 120, trozos_t)

    import numpy as _np
    from motor import _recortar
    sr = 24000
    voz = _np.sin(_np.linspace(0, 400 * _np.pi, sr // 2)).astype(_np.float32) * 0.5
    respiro = (_np.random.default_rng(0).standard_normal(sr // 2) * 0.01).astype(_np.float32)
    recortado = _recortar(_np.concatenate([voz, respiro]), sr)
    comprobar("respiracion final recortada", len(recortado) < sr * 0.6, len(recortado) / sr)
    comprobar("fundido sin chasquido", abs(float(recortado[-1])) < 1e-3, recortado[-1])
    dice("miles con varios puntos", "Son 1.234.567 líneas.", "un millón doscientos")
    dice("RAM como palabra", "Tiene 4 GB de RAM.", "de ram")
    dice("punto medio como pausa", "Publicado hoy · 5 min de lectura.", "hoy, cinco minutos")
    dice("comillas simples", "Con 'simples' y don't.", "Con simples y don't")
    dice("ampersand", "Texto & símbolos.", "Texto y símbolos")
    dice("sociedad limitada", "Ejemplo S.L. y Otra S.A.", "Ejemplo ese ele y Otra ese a")
    fin = md_a_voz("En Nueva York, etc. El piso es grande.")
    comprobar("etc. al final de frase conserva el punto", "etcétera. El piso" in fin, fin)
    citas = limpiar_texto('Siglas: «API» → «a pe i», “JSON” -> "yéison".')
    comprobar("sin comillas", not any(c in citas for c in '«»“”"'), citas)
    comprobar("flecha como pausa", "API, a pe i, JSON, yéison" in citas, citas)

    # Reparto real: trocear -> generar con un motor falso tipo XTTS
    import re as _re

    class MotorFalso:
        def __init__(self):
            self.llamadas = []

        def crear(self, frase):
            self.llamadas.append([(frase, "es")])
            return frase

        def crear_segmentos(self, partes):
            self.llamadas.append(list(partes))
            return partes

    motor = MotorFalso()
    texto = ("Claude dijo: you should run the tests first. Luego haz commit y push del README.")
    for frase in (p.strip() for p in _re.split(r"(?<=[.!?…:;])\s+", texto) if p.strip()):
        generar(motor, frase, "es", ingles=True)
    idiomas = [[i for _, i in llamada] for llamada in motor.llamadas]
    comprobar("frase inglesa sola se dice en ingles", ["en"] in idiomas, motor.llamadas)
    comprobar("frase espanola sigue en espanol", ["es"] in idiomas, motor.llamadas)
    motor = MotorFalso()
    generar(motor, "you should run the tests first.", "es", ingles=False)
    comprobar("sin ingles todo en espanol", motor.llamadas[0][0][1] == "es", motor.llamadas)

    print(f"\n{len(fallos)} fallo(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
