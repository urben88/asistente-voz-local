"""Lectura de Markdown en voz alta (chats de agentes de IA, README, notas).

Convierte Markdown (o texto normal, con ``limpiar_texto``) en texto que tenga
sentido oir: sin codigo, tablas largas, URLs, HTML, emojis, iconos ni restos de
formato. Las reglas de saneado en linea viven en un solo sitio
(``limpiar_texto``) y las usan los dos caminos del lector.
"""

import html
import re
import unicodedata

MAX_FILAS_TABLA = 10
MAX_CODIGO_EN_LINEA = 30
_COLUMNAS_INDICE = {"#", "n", "nº", "n.º", "no", "num", "número", "numero", "fila", "id"}

# Abreviaturas frecuentes -> palabra hablada. Se aplican en orden; ampliar aqui.
ABREVIATURAS = (
    (r"EE\.\s*UU\.", "Estados Unidos"),
    (r"p\.\s*ej\.", "por ejemplo"),
    (r"ej\.", "ejemplo"),
    (r"etc\.(?=\s+[A-ZÁÉÍÓÚÑ¿¡])", "etcétera."),  # fin de frase: conserva la pausa
    (r"etc\.", "etcétera"),
    (r"n\.\s*[º°]", "número"),
    (r"n[º°]", "número"),
    (r"aprox\.", "aproximadamente"),
    (r"Sra\.", "señora"),
    (r"Sr\.", "señor"),
    (r"Dr\.", "doctor"),
    (r"vs\.", "frente a"),
)
_ABREVIATURAS = tuple((re.compile(p, re.IGNORECASE), s) for p, s in ABREVIATURAS)

RE_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
RE_VALLA = re.compile(r"^\s*(```|~~~)")
RE_SEPARADOR_CELDA = re.compile(r":?-{3,}:?")
RE_HERRAMIENTA = re.compile(r"^\s*(?:⎿|⏺\s*[\w.-]+\s*\()")
RE_ARBOL = re.compile(r"^\s*[│├└╭╰─┌┐┘┬┴┼╔╗╚╝║═]")
RE_PROMPT = re.compile(r"^\s*(?:\$\s+\S|PS\s+[A-Za-z]:[\\/][^>]*>|[A-Za-z]:[\\/][^>]*>)")
RE_DEF_ENLACE = re.compile(r"^\s*\[[^\]]+\]:\s*\S+")
RE_REGLA = re.compile(r"^\s*([-*_=]\s*){3,}$")

# Caracteres que no aportan nada al oido y no los cubren las categorias Unicode
_SIMBOLOS_NO_LEIDOS = set("•‧∙‣⁃›»◦▪▫■□●○◆◇«‹“”„\"")  # comillas: la voz las pronuncia raro
# Lo que si se conserva aunque su categoria sea "So"
_SIMBOLOS_PERMITIDOS = set("%€$+=·°‰")

# Rangos que no se leen: flechas, iconos tecnicos, formas, emojis, formatos...
_RANGOS_NO_LEIDOS = (
    (0x2190, 0x21FF),   # flechas
    (0x27F0, 0x27FF),   # flechas suplementarias
    (0x2900, 0x297F),   # flechas B
    (0x2300, 0x23FF),   # simbolos tecnicos: ⏺ ⎿ ⌘
    (0x2460, 0x24FF),   # numeros en circulo
    (0x25A0, 0x25FF),   # formas geometricas
    (0x2600, 0x27BF),   # simbolos varios y dingbats: ✅ ✔ ⚠
    (0x2B00, 0x2BFF),   # flechas y formas varias
    (0x1F000, 0x1FAFF),  # emoji y pictogramas
    (0xFE00, 0xFE0F),   # selectores de variacion
    (0xE0000, 0xE007F),  # etiquetas emoji
    (0x200B, 0x200F),   # anchos cero
    (0x202A, 0x202E),   # marcas de direccion
    (0x2060, 0x206F),   # formato invisible
    (0x20D0, 0x20FF),   # combinables para simbolos
)

RE_NEGRITA = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
RE_NEGRITA_ALTA = re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", re.S)
RE_CURSIVA = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", re.S)
RE_CURSIVA_ALTA = re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)", re.S)
RE_TACHADO = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S)
RE_CODIGO = re.compile(r"`+([^`]+)`+")


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


# --- Simbolos ---

def _es_simbolo(caracter):
    """True si el caracter no se debe leer (emoji, icono, flecha, formato)."""
    if caracter in _SIMBOLOS_PERMITIDOS:
        return False
    if caracter in _SIMBOLOS_NO_LEIDOS:
        return True
    codigo = ord(caracter)
    for inicio, fin in _RANGOS_NO_LEIDOS:
        if inicio <= codigo <= fin:
            return True
    return unicodedata.category(caracter) in ("So", "Sk", "Cf", "Co")


def _quitar_simbolos(texto):
    """Sustituye por espacio lo que no se lee, sin pegar palabras."""
    return "".join(" " if _es_simbolo(c) else c for c in texto)


# --- Saneado en linea (comun a Markdown y texto normal) ---

def _hablable(codigo):
    """True si el contenido de un codigo en linea se puede leer tal cual."""
    if not re.search(r"[^\W_]", codigo):
        return False
    if re.search(r"[{}\[\]();<>\\|]", codigo):
        return False
    if re.search(r"\s", codigo) and re.search(r"[-_=/]", codigo):
        return False  # p. ej. "python lector.py --probar": es un comando
    return True


def _codigo_en_linea(coincidencia):
    contenido = coincidencia.group(1).strip()
    if contenido and len(contenido) <= MAX_CODIGO_EN_LINEA and _hablable(contenido):
        return contenido
    return " "


def _quitar_marcadores(linea):
    """Quita titulos, citas, vinetas, casillas y numeracion de lista."""
    anterior = None
    while anterior != linea:
        anterior = linea
        linea = re.sub(r"^\s*#{1,6}\s+", "", linea)
        linea = re.sub(r"^\s*(?:>\s*)+", "", linea)
        linea = re.sub(r"^\s*[-*+]\s+(?:\[[ xX]\]\s*)?", "", linea)
        linea = re.sub(r"^\s*\d{1,2}[.)]\s+", "", linea)
        linea = re.sub(r"^\s*\[[ xX]\]\s*", "", linea)
    return linea


def _expandir_abreviaturas(linea):
    """Sustituye abreviaturas; solo capitaliza si abren la linea (Aprox. -> Aproximadamente)."""
    for patron, palabra in _ABREVIATURAS:
        def reemplazo(m, palabra=palabra):
            if m.start() == 0 and m.group(0)[:1].isupper():
                return palabra[:1].upper() + palabra[1:]
            return palabra
        linea = patron.sub(reemplazo, linea)
    return linea


def _limpiar_linea(linea):
    """Aplica todas las reglas de saneado a una sola linea."""
    linea = _quitar_marcadores(linea)

    linea = RE_CODIGO.sub(_codigo_en_linea, linea)                     # codigo en linea
    linea = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", linea)                # imagenes
    linea = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", linea)            # enlaces -> texto
    linea = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", linea)           # enlaces por referencia
    linea = re.sub(r"\[\^[^\]]*\]", " ", linea)                       # notas al pie
    linea = re.sub(r"\{#[^}]*\}", " ", linea)                         # anclas

    linea = _expandir_abreviaturas(linea)                             # abreviaturas

    linea = re.sub(r"(?:https?|ftp)://\S+", " ", linea, flags=re.I)   # URLs desnudas
    linea = re.sub(r"\bwww\.\S+", " ", linea, flags=re.I)

    linea = RE_NEGRITA.sub(r"\1", linea)
    linea = RE_NEGRITA_ALTA.sub(r"\1", linea)
    linea = RE_CURSIVA.sub(r"\1", linea)
    linea = RE_CURSIVA_ALTA.sub(r"\1", linea)
    linea = RE_TACHADO.sub(r"\1", linea)

    # Flechas entre palabras ("API → a pe i", "x -> y"): pausa de coma, no silencio
    linea = re.sub(r"\s*(?:→|⇒|⟶|➜|->|=>)\s*", ", ", linea)
    linea = _quitar_simbolos(linea)

    linea = linea.replace("|", " ").replace(">", " ")                 # tablas y citas
    linea = re.sub(r"`+", " ", linea)                                 # backticks
    linea = re.sub(r"(?<!\w)#+", " ", linea)                          # # de titulo (C# se queda)
    linea = re.sub(r"(?<!\w)_+|_+(?!\w)", " ", linea)                 # _ sueltos (snake_case se queda)
    linea = re.sub(r"[*~]+", " ", linea)                              # enfasis suelto
    linea = re.sub(r"[\[\]{}]", " ", linea)                           # corchetes rotos

    # Guiones largos: "3–5" -> "3 a 5"; el resto, pausa de coma.
    linea = re.sub(r"(?<=\d)\s*[–—]\s*(?=\d)", " a ", linea)
    linea = re.sub(r"\s*[–—]\s*", ", ", linea)

    # Puntuacion repetida y espacios sobrantes.
    linea = re.sub(r"\.{3,}", "…", linea)
    linea = re.sub(r"\.{2}", ".", linea)
    linea = re.sub(r"([,;:])\1+", r"\1", linea)
    linea = re.sub(r"([!?])\1+", r"\1", linea)
    linea = re.sub(r",\s*([.;:!?…])", r"\1", linea)   # "funciona,." -> "funciona."
    linea = re.sub(r"\s+([,.;:!?…%])", r"\1", linea)
    linea = re.sub(r"\(\s+", "(", linea)
    linea = re.sub(r"\s+\)", ")", linea)
    linea = re.sub(r"\s+", " ", linea)
    return linea.strip()


def limpiar_texto(texto):
    """Saneado comun para texto normal y para cada linea de Markdown.

    Quita simbolos, emojis, URLs, HTML y restos de formato, expande
    abreviaturas y devuelve solo las lineas que tienen algo que leer.
    """
    texto = RE_ANSI.sub("", texto)
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)
    texto = html.unescape(texto)
    texto = re.sub(r"</?[A-Za-z][^>\n]*>", " ", texto)
    lineas = []
    for linea in texto.splitlines():
        linea = _limpiar_linea(linea)
        if re.search(r"[^\W_]", linea):  # al menos una letra o un digito
            lineas.append(linea)
    return "\n".join(lineas)


# --- Markdown por bloques ---

def _cerrar(frase):
    """Cierra la frase con . ? ! o … para que haya pausa al leer.

    Los dos puntos se conservan: anuncian una lista y el motor les da una pausa
    media, más natural que un punto.
    """
    frase = frase.strip()
    if not frase:
        return frase
    if frase[-1] in ",;":
        return frase[:-1].rstrip() + "."
    if frase[-1] not in ".!?…:":
        return frase + "."
    return frase


def _es_fila_tabla(linea):
    t = linea.strip()
    if not t:
        return False
    return t.startswith("|") or " | " in t


def _celdas(fila):
    return [c.strip() for c in fila.strip().strip("|").split("|")]


def _es_separador(celdas):
    return bool(celdas) and all(RE_SEPARADOR_CELDA.fullmatch(c or "-") for c in celdas)


def _leer_tabla(filas):
    """Lee una tabla como «Tabla de N columnas: …» + una frase por fila.

    Cada fila se lee «Columna: valor; Columna: valor», así se entiende sin ver la
    tabla. La primera fila es la cabecera; la columna de índice (1, 2, 3…) no se lee.
    """
    cabecera, cuerpo = None, []
    for fila in filas:
        celdas = _celdas(fila)
        if _es_separador(celdas):
            continue
        limpias = [limpiar_texto(c) for c in celdas]
        if cabecera is None:
            cabecera = limpias
        elif any(limpias):
            cuerpo.append(limpias)
    if cabecera is None or not any(cabecera):
        return []

    # Columna de índice («#», «N»…) con números correlativos: fuera (no se lee el número)
    if len(cabecera) > 1:
        nombre_col0 = cabecera[0].strip().rstrip(".").lower()
        numeros = [f[0].strip() for f in cuerpo if f and f[0].strip()]
        if (nombre_col0 in _COLUMNAS_INDICE or not nombre_col0) and numeros \
                and all(re.fullmatch(r"\d+", n) for n in numeros):
            cabecera = cabecera[1:]
            cuerpo = [f[1:] for f in cuerpo]

    columnas = [c for c in cabecera if c]
    filas = [f for f in cuerpo if any(f)]
    if not filas:
        return []

    salida = []
    if len(columnas) >= 2:
        etiqueta_col = "columna" if len(columnas) == 1 else "columnas"
        etiqueta_fila = "fila" if len(filas) == 1 else "filas"
        salida.append(_cerrar(f"Tabla de {len(columnas)} {etiqueta_col}: {', '.join(columnas)}"))
        salida.append(_cerrar(f"{len(filas)} {etiqueta_fila}"))

    for fila in filas[:MAX_FILAS_TABLA]:
        partes = []
        for i, valor in enumerate(fila):
            if not valor:
                continue
            nombre = cabecera[i] if i < len(cabecera) else ""
            partes.append(f"{nombre}: {valor}" if nombre else valor)
        if partes:
            salida.append(_cerrar("; ".join(partes)))

    resto = len(filas) - MAX_FILAS_TABLA
    if resto > 0:
        salida.append(f"Y {resto} filas más.")
    return salida


RE_ESTRUCTURA = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d{1,2}[.)]\s|>)")
RE_ELEMENTO = re.compile(r"^(\s*)(?:[-*+]|\d{1,2}[.)])\s+\S")

AVISO_CODIGO = "Aquí hay un bloque de código."
AVISO_CONSOLA = "Aquí hay una salida de consola."
AVISO_LISTA = "Lista."
AVISO_TAREAS = "Lista de tareas."
AVISO_SUBLISTA = "Sublista."


def _sangria(espacios):
    return len(espacios.replace("\t", "    "))


def _volcar(parrafo, salida):
    """Cierra el parrafo acumulado (lineas de texto que se envuelven)."""
    if not parrafo:
        return
    frase = limpiar_texto(" ".join(parrafo))
    if frase:
        salida.append(_cerrar(frase))
    parrafo.clear()


def md_a_voz(texto):
    """Convierte Markdown en texto para leer, una frase o bloque por linea."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    texto = RE_ANSI.sub("", texto)
    texto = re.sub(r"\A\s*---\s*\n.*?\n---[^\n]*\n", "", texto, flags=re.S)  # frontmatter
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)

    lineas = texto.split("\n")
    salida = []
    parrafo = []
    cita_abierta = False
    consola_abierta = False
    niveles = []  # sangrias de la lista abierta; vacia = fuera de lista
    i = 0
    while i < len(lineas):
        linea = lineas[i]

        valla = RE_VALLA.match(linea)
        if valla:
            _volcar(parrafo, salida)
            niveles = []
            marca = linea.strip()[:3]
            i += 1
            dentro = 0
            while i < len(lineas) and not lineas[i].strip().startswith(marca):
                dentro += bool(lineas[i].strip())
                i += 1
            i += 1  # cierre (o fin del texto)
            if dentro:  # se anuncia, no se lee
                salida.append(AVISO_CODIGO)
            continue

        if _es_fila_tabla(linea):
            _volcar(parrafo, salida)
            niveles = []
            filas = []
            while i < len(lineas) and _es_fila_tabla(lineas[i]):
                filas.append(lineas[i])
                i += 1
            salida.extend(_leer_tabla(filas))
            continue

        i += 1
        if RE_HERRAMIENTA.match(linea) or RE_ARBOL.match(linea) or RE_PROMPT.match(linea):
            _volcar(parrafo, salida)
            if not consola_abierta:  # un aviso por grupo de lineas de consola
                salida.append(AVISO_CONSOLA)
            consola_abierta = True
            continue
        # Lineas sangradas justo despues de la consola (salida del comando)
        if consola_abierta and linea.strip() and linea[:1] in " \t" \
                and not RE_ESTRUCTURA.match(linea):
            continue
        consola_abierta = False

        if RE_REGLA.match(linea) or RE_DEF_ENLACE.match(linea):
            _volcar(parrafo, salida)
            continue

        if not linea.strip():  # linea en blanco: fin de parrafo
            _volcar(parrafo, salida)
            cita_abierta = False
            continue

        elemento = RE_ELEMENTO.match(linea)
        if elemento:
            sangria = _sangria(elemento.group(1))
            if not niveles:
                _volcar(parrafo, salida)
                tareas = re.match(r"^\s*[-*+]\s+\[[ xX]\]", linea)
                salida.append(AVISO_TAREAS if tareas else AVISO_LISTA)
                niveles = [sangria]
            elif sangria > niveles[-1]:
                _volcar(parrafo, salida)
                salida.append(AVISO_SUBLISTA)
                niveles.append(sangria)
            else:
                while len(niveles) > 1 and sangria < niveles[-1]:
                    niveles.pop()
        elif not (niveles and linea[:1] in " \t"):  # texto que no continua un elemento
            niveles = []

        if RE_ESTRUCTURA.match(linea):  # titulo, lista o cita: frase propia
            _volcar(parrafo, salida)
            casilla = re.match(r"^\s*[-*+]\s+\[([ xX])\]", linea)
            es_cita = linea.lstrip().startswith(">")
            frase = limpiar_texto(linea)
            if frase:
                if casilla:
                    frase = ("Hecho: " if casilla.group(1).strip() else "Pendiente: ") + frase
                elif es_cita and not cita_abierta:
                    frase = "Cita: " + frase
                salida.append(_cerrar(frase))
            cita_abierta = es_cita
            continue

        parrafo.append(linea)  # texto normal: las lineas envueltas se juntan
        cita_abierta = False

    _volcar(parrafo, salida)
    return "\n".join(salida)
