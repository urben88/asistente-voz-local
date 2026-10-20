"""Lectura de Markdown en voz alta (chats de agentes de IA, README, notas).

Detecta si un texto es Markdown y lo convierte en texto para leer:
se salta el codigo, las URL, las tablas largas y los restos de herramientas.
"""

import re

MAX_FILAS_TABLA = 5
MAX_CODIGO_EN_LINEA = 30

# Lineas de herramienta de un agente (Claude Code y similares): "⏺ Bash(...)", "⎿ ..."
RE_HERRAMIENTA = re.compile(r"^\s*(⎿|⏺\s*\w+\(|[│├└╭╰─]{2,})")
RE_VALLA = re.compile(r"^\s*(```|~~~)\s*([\w+#.-]*)")
RE_FILA_TABLA = re.compile(r"^\s*\|.*\|\s*$")
RE_SEPARADOR_TABLA = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
RE_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def es_markdown(texto):
    """Cuenta senales de Markdown; con dos o mas, se trata como Markdown."""
    senales = [
        r"^\s*(```|~~~)",               # bloque de codigo
        r"^#{1,6}\s+\S",                # titulo
        r"^\s*[-*+]\s+\S",              # lista
        r"^\s*\d+\.\s+\S",              # lista numerada
        r"\*\*[^*\n]+\*\*",             # negrita
        r"\[[^\]\n]+\]\([^)\s]+\)",     # enlace
        r"`[^`\n]+`",                   # codigo en linea
        r"^\s*\|.*\|\s*$",              # tabla
        r"^\s*>\s",                     # cita
    ]
    return sum(1 for s in senales if re.search(s, texto, re.MULTILINE)) >= 2


def _en_linea(texto):
    """Limpia el formato dentro de una linea."""
    texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texto)                 # imagenes
    texto = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", texto)             # enlaces -> texto
    texto = re.sub(r"<[^>\n]+>", " ", texto)                           # HTML
    texto = re.sub(r"https?://\S+", "enlace", texto)
    texto = re.sub(r"`([^`]+)`",
                   lambda m: m.group(1) if len(m.group(1)) <= MAX_CODIGO_EN_LINEA else "código",
                   texto)
    texto = re.sub(r"(\*\*|\*|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", texto)       # enfasis
    texto = re.sub(r"(?<!\w)(__|_)(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", texto)
    texto = RE_EMOJI.sub("", texto)
    texto = re.sub(r"[*#`>|~]+|(?<!\w)_+|_+(?!\w)", " ", texto)        # restos sueltos (ef_dora se queda)
    texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _cerrar(frase):
    """Pone punto final si no lo tiene, para que haya pausa al leer."""
    if frase and frase[-1] not in ".!?…:;,":
        frase += "."
    return frase


def _leer_tabla(filas):
    celdas = [[c.strip() for c in f.strip().strip("|").split("|")] for f in filas
              if not RE_SEPARADOR_TABLA.match(f)]
    salida = []
    for fila in celdas[:MAX_FILAS_TABLA]:
        partes = [_en_linea(c) for c in fila]
        salida.append(_cerrar(", ".join(p for p in partes if p)))
    resto = len(celdas) - MAX_FILAS_TABLA
    if resto > 0:
        salida.append(f"Y {resto} filas más.")
    return salida


def md_a_voz(texto):
    """Convierte Markdown en texto para leer, una frase o bloque por linea."""
    salida = []
    lineas = texto.splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i]

        valla = RE_VALLA.match(linea)
        if valla:
            marca, lenguaje = valla.group(1), valla.group(2)
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith(marca):
                i += 1
            salida.append(f"Bloque de código en {lenguaje}, omitido." if lenguaje
                          else "Bloque de código, omitido.")
            i += 1
            continue

        if RE_FILA_TABLA.match(linea):
            filas = []
            while i < len(lineas) and RE_FILA_TABLA.match(lineas[i]):
                filas.append(lineas[i])
                i += 1
            salida.extend(_leer_tabla(filas))
            continue

        i += 1
        if RE_HERRAMIENTA.match(linea) or re.match(r"^\s*([-*_]\s*){3,}$", linea):
            continue
        linea = re.sub(r"^\s*#{1,6}\s+", "", linea)          # titulo
        linea = re.sub(r"^\s*(>\s*)+", "", linea)            # cita
        linea = re.sub(r"^\s*[-*+]\s+(\[[ xX]\]\s+)?", "", linea)  # lista y casillas
        frase = _en_linea(linea)
        if frase:
            salida.append(_cerrar(frase))
    return "\n".join(salida)
