"""Pronunciacion para la voz espanola (spec 17).

Se aplica frase a frase, despues del filtro de ``leer_md`` y antes del motor:
- reescribe anglicismos con letras espanolas («deploy» -> «diplói»),
- deletrea siglas (API -> «a pe i») y lee como palabra las que lo son,
- dice numeros, versiones, unidades, horas y fechas como una persona,
- con XTTS, separa los tramos en ingles (3 palabras o mas) para decirlos en
  ingles con la misma voz.

Sin dependencias obligatorias: ``num2words`` es opcional (sin ella los
numeros se dejan como estan). El diccionario se amplia con un
``pronunciacion.json`` junto a ``lector.json``.
"""

import json
import logging
import re
from pathlib import Path

try:
    from num2words import num2words
except ImportError:  # instalaciones solo Piper sin num2words
    num2words = None

log = logging.getLogger("lector")

# --- Diccionarios (ampliables con pronunciacion.json) ---

# Palabra inglesa -> como suena escrita en espanol. Sin distinguir mayusculas.
ANGLICISMOS = {
    # agentes y desarrollo
    "pull request": "pul ricuést", "pull requests": "pul ricuésts",
    "commit": "cómit", "pull": "pul", "merge": "merch", "branch": "branch",
    "deploy": "diplói", "build": "bild", "debug": "dibág", "prompt": "prompt",
    "token": "tóquen", "script": "escrípt", "framework": "fréimguork",
    "frontend": "fróntend", "backend": "báquend", "feature": "fícher", "bug": "bag",
    "fix": "fics", "hotfix": "jótfics", "issue": "ísiu", "release": "rilís",
    "hook": "juk", "log": "log", "plugin": "plaguin", "skill": "esquil",
    "agent": "éiyent", "workflow": "guórcflou", "setup": "sétap", "update": "apdéit",
    "upload": "aplóud", "download": "dáunloud", "server": "sérver", "cloud": "claud",
    "browser": "bráuser", "email": "iméil", "mail": "méil", "online": "onláin",
    "offline": "ofláin", "link": "linc", "click": "clic", "shortcut": "shórcat",
    "software": "sófguer", "hardware": "járguer", "driver": "dráiver",
    "streaming": "estríming", "web": "güeb", "website": "güébsait", "endpoint": "éndpoint",
    "dashboard": "dáshbord", "path": "paz", "file": "fáil", "folder": "fólder",
    "default": "difólt", "output": "áutput", "input": "ínput", "pipeline": "páiplain",
    "thread": "zred", "string": "estrin", "query": "cuéri", "request": "ricuést",
    "response": "rispóns", "checkout": "chécaut", "rebase": "ribéis", "stash": "estash",
    "staging": "estéiyin", "runtime": "ránaim", "timeout": "táimaut",
    "feedback": "fídbac", "spec": "espec", "app": "ap", "workspace": "guórcspeis",
    "laptop": "láptop", "smartphone": "esmárfon", "manager": "mánayer",
    "meeting": "míting", "deadline": "dédlain", "ok": "okéi", "okay": "okéi",
    "wifi": "uáifai", "wi-fi": "uáifai", "e-mail": "iméil", "chatbot": "chátbot", "benchmark": "bénchmarc",
    "checklist": "chéclist", "layout": "léiaut", "backup": "bácap", "password": "pásguord",
    "username": "iúsernéim", "login": "loguin", "logout": "logáut", "router": "ráuter",
    "fine-tuning": "fáin tiúnin", "embedding": "imbéding", "embeddings": "imbédings",
    "machine learning": "mashín lérnin", "deep learning": "dip lérnin",
    "speech": "espich", "voice": "vois", "reader": "ríder", "shell": "shel",
    "notebook": "nóutbuc", "hub": "jab", "stack": "estac",
    "tool": "tul", "tools": "tuls", "subagent": "sab éiyent", "subagents": "sab éiyents",
    # nombres propios
    "readme": "rídmi", "markdown": "márcdaun", "github": "guíjab", "gitlab": "guítlab",
    "git": "guit", "claude": "clod", "anthropic": "anzrópic", "openai": "ópen ei ai",
    "opencode": "ópen coud", "deepseek": "dípsic", "sonnet": "sónet", "haiku": "jáicu",
    "windows": "güíndous", "python": "páizon", "ollama": "olama", "google": "gúguel",
    "chrome": "crom", "microsoft": "máicrosoft", "apple": "ápel", "youtube": "iutub",
    "docker": "dóquer", "node": "noud", "javascript": "yavascrípt",
    "typescript": "táipscript", "rust": "rast", "piper": "páiper", "whisper": "guísper",
    "handy": "jándi", "chatterbox": "cháterbox", "slack": "eslac", "notion": "nóushon",
    "visual studio code": "vísual estudio coud", "vs code": "uve ese coud",
    "powershell": "páuershel", "bash": "bash", "linux": "línux", "macos": "mac o ese",
    "iphone": "áifon", "android": "ándroid", "chatgpt": "chat ye pe te", "gemini": "yémini",
}

# Siglas que se deletrean letra a letra.
SIGLAS_DELETREADAS = {
    "API", "GPU", "CPU", "URL", "USB", "PDF", "HTML", "CSS", "SQL", "SSH", "IA", "PC", "TTS",
    "XTTS", "MCP", "CLI", "UI", "UX", "ID", "IP", "SSD", "HDD", "LLM", "SDK", "IDE",
    "HTTP", "HTTPS", "DNS", "VPN", "PR", "CI", "CD", "QA", "BBDD", "DB", "ONNX", "SO",
    "NPM", "AWS", "GCP", "MB", "GB", "KB", "TB", "PNG", "JPG", "SVG", "CSV", "XML", "RDP",
    "UIA", "WSL", "TV", "DNI", "EEUU", "UE", "FAQ", "CEO", "RGB", "HD", "FPS",
}

# Siglas (o palabras en mayusculas) que se leen como palabra.
SIGLAS_PALABRA = {
    "JSON": "yéison", "YAML": "yámel", "VRAM": "uve ram", "AI": "ei ai", "NASA": "nasa",
    "OTAN": "otan", "ONG": "o ene ge", "GIF": "guif", "JPEG": "yeipeg", "WAV": "uav",
    "SaaS": "sas", "OK": "okéi", "IVA": "iva", "README": "rídmi", "UNIX": "iúnix",
    "LAN": "lan", "RAM": "ram", "WAN": "uan", "ASCII": "asqui", "PIN": "pin", "SIM": "sim",
}

LETRAS = {
    "A": "a", "B": "be", "C": "ce", "D": "de", "E": "e", "F": "efe", "G": "ge", "H": "hache",
    "I": "i", "J": "jota", "K": "ka", "L": "ele", "M": "eme", "N": "ene", "Ñ": "eñe", "O": "o",
    "P": "pe", "Q": "cu", "R": "erre", "S": "ese", "T": "te", "U": "u", "V": "uve",
    "W": "uve doble", "X": "equis", "Y": "i griega", "Z": "zeta",
}

EXTENSIONES = {
    "md": "eme de", "py": "pai", "json": "yéison", "txt": "te equis te", "exe": "exe",
    "ps1": "pe ese uno", "sh": "ese hache", "js": "jota ese", "ts": "te ese",
    "html": "hache te eme ele", "css": "ce ese ese", "yaml": "yámel", "yml": "yámel",
    "csv": "ce ese uve", "log": "log", "onnx": "onix", "bin": "bin", "wav": "uav",
    "pdf": "pe de efe", "png": "pe ene ge", "jpg": "jota pe ge", "mjs": "eme jota ese",
    "toml": "tómel", "ini": "ini", "bat": "bat", "zip": "sip", "lock": "loc",
}

TECLAS = {
    "ctrl": "control", "control": "control", "alt": "alt", "shift": "shift",
    "mayus": "mayús", "mayús": "mayús", "win": "windows", "cmd": "comand", "tab": "tab",
    "esc": "escape", "enter": "enter", "intro": "intro", "espacio": "espacio",
    "space": "espacio", "supr": "suprimir", "del": "suprimir", "fn": "efe ene",
    "inicio": "inicio", "fin": "fin", "home": "inicio", "end": "fin",
}

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")

# Unidad -> (plural, singular con 1)
UNIDADES = {
    "GB": ("gigas", "una giga"), "MB": ("megas", "un mega"), "KB": ("kilobytes", "un kilobyte"),
    "TB": ("teras", "un tera"), "ms": ("milisegundos", "un milisegundo"),
    "s": ("segundos", "un segundo"), "seg": ("segundos", "un segundo"),
    "min": ("minutos", "un minuto"), "h": ("horas", "una hora"),
    "km": ("kilómetros", "un kilómetro"), "kg": ("kilos", "un kilo"),
    "cm": ("centímetros", "un centímetro"), "mm": ("milímetros", "un milímetro"),
    "m²": ("metros cuadrados", "un metro cuadrado"), "m2": ("metros cuadrados", "un metro cuadrado"),
    "m": ("metros", "un metro"), "°C": ("grados", "un grado"), "ºC": ("grados", "un grado"),
    "°": ("grados", "un grado"), "€": ("euros", "un euro"),
    "$": ("dólares", "un dólar"), "GHz": ("gigahercios", "un gigahercio"),
    "MHz": ("megahercios", "un megahercio"), "W": ("vatios", "un vatio"),
}

# --- Palabras funcionales para detectar ingles (R6) ---

FUNCIONALES_EN = {
    "the", "is", "are", "was", "were", "of", "to", "and", "you", "with", "this", "that",
    "for", "it", "be", "not", "can", "will", "have", "has", "from", "your", "what", "how",
    "when", "we", "they", "should", "would", "there", "which", "an", "do", "does", "don't",
    "i", "my", "our", "their", "it's", "i'm", "you're", "let's", "if", "then", "but", "or",
    "just", "also", "please", "here", "now", "all", "any", "some", "more", "into", "about",
    "been", "being", "could", "must", "may", "might", "shall", "these", "those", "who",
    "why", "where", "make", "sure", "need", "want", "use", "using", "get", "got", "see",
    "first", "next", "after", "before", "only", "it'll", "won't", "can't", "isn't", "by",
    "at", "on", "in", "up", "out", "over", "than", "very", "yes", "thanks", "thank",
}
FUNCIONALES_ES = {
    "el", "la", "los", "las", "de", "del", "al", "que", "y", "e", "en", "es", "por", "para",
    "con", "un", "una", "unos", "unas", "se", "no", "lo", "le", "les", "su", "sus", "mi", "tu",
    "como", "pero", "más", "o", "u", "si", "sí", "ya", "muy", "hay", "hoy", "soy", "estoy",
    "voy", "ley", "rey", "este", "esta", "esto", "eso", "ese", "esa", "son", "está", "están",
    "fue", "ha", "han", "he", "hemos", "sin", "sobre", "entre", "cuando", "donde", "también",
    "porque", "qué", "cómo", "nos", "me", "te", "ni", "aquí", "ahora", "luego", "bien", "todo",
    "dijo", "dice", "hace", "puede", "tiene", "va", "vamos", "ser", "hacer",
}
_LETRAS_ES = set("áéíóúñü¿¡")
_RE_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][A-Za-z]+)?")


# --- Diccionario del usuario ---

_extra = {"ruta": None, "mtime": None}


def _rutas_extra():
    aqui = Path(__file__).resolve().parent
    return (aqui / "pronunciacion.json", aqui.parent / "config" / "pronunciacion.json")


def _cargar_extra():
    """Mezcla pronunciacion.json (si existe) con los diccionarios. Relee si cambia."""
    for ruta in _rutas_extra():
        if not ruta.is_file():
            continue
        try:
            mtime = ruta.stat().st_mtime
            if _extra["ruta"] == ruta and _extra["mtime"] == mtime:
                return
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            for k, v in (datos.get("palabras") or {}).items():
                ANGLICISMOS[str(k).lower()] = str(v)
            SIGLAS_DELETREADAS.update(str(s) for s in datos.get("siglas_deletreadas") or [])
            for k, v in (datos.get("siglas_palabra") or {}).items():
                SIGLAS_PALABRA[str(k)] = str(v)
            _extra.update(ruta=ruta, mtime=mtime)
            _compilar()
        except Exception:
            log.warning("No se pudo leer %s", ruta, exc_info=True)
        return


def _compilar():
    global _RE_ANGLICISMO
    claves = sorted(ANGLICISMOS, key=len, reverse=True)  # multipalabra primero
    _RE_ANGLICISMO = re.compile(
        r"(?<![\w-])(" + "|".join(re.escape(k) for k in claves) + r")(es|s)?(?![\w-])",
        re.IGNORECASE)


_RE_ANGLICISMO = None
_compilar()


# --- Numeros ---

def _n(numero):
    """Entero (str o int) -> palabras; sin num2words se deja como esta."""
    texto = str(numero)
    if num2words is None:
        return texto
    if len(texto.lstrip("0")) >= 10:  # telefonos, identificadores: cifra a cifra
        return " ".join(num2words(int(c), lang="es") for c in texto)
    return num2words(int(texto), lang="es")


def _cifras(parte):
    """Parte decimal: los ceros iniciales se dicen («05» -> «cero cinco»)."""
    ceros = len(parte) - len(parte.lstrip("0"))
    resto = parte.lstrip("0")
    palabras = ["cero"] * ceros
    if resto:
        palabras.append(_n(resto))
    return " ".join(palabras)


def _deletrear(sigla):
    return " ".join(LETRAS.get(c, c.lower()) for c in sigla.upper())


def _capitalizar_como(original, nuevo):
    return nuevo[:1].upper() + nuevo[1:] if original[:1].isupper() else nuevo


# --- Reglas del texto en espanol (R3-R5) ---

def _teclas(m):
    partes = m.group(0).split("+")
    if not any(p.lower() in TECLAS for p in partes) or not all(
            p.lower() in TECLAS or re.fullmatch(r"[A-Za-z0-9]|[Ff]\d{1,2}", p) for p in partes):
        return m.group(0)
    dichas = []
    for p in partes:
        if p.lower() in TECLAS:
            dichas.append(TECLAS[p.lower()])
        elif len(p) == 1 and p.isalpha():
            dichas.append(LETRAS.get(p.upper(), p))
        elif p[0] in "Ff" and len(p) > 1:
            dichas.append("efe " + _n(p[1:]))
        else:
            dichas.append(_n(p))
    return " ".join(dichas)


def _archivo(m):
    return f"{m.group(1)} punto {EXTENSIONES[m.group(2).lower()]}"


def _fecha(dia, mes, anyo):
    dia, mes = int(dia), int(mes)
    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        return None
    return f"{_n(dia) if dia != 1 else 'uno'} de {MESES[mes - 1]} de {_n(anyo)}"


def _version(partes):
    return " punto ".join(_n(p) for p in partes)


def _unidad(m):
    numero, unidad = m.group(1), m.group(2)
    plural, singular = UNIDADES[unidad]
    if numero == "1":
        return singular
    return f"{numero} {plural}"


def _decimal(m, separador):
    return f"{_n(m.group(1))} {separador} {_cifras(m.group(2))}"


def _sigla(m):
    sigla, plural = m.group(1), m.group(2) or ""
    if sigla in SIGLAS_PALABRA:
        return SIGLAS_PALABRA[sigla] + plural
    sin_vocales = not re.search(r"[AEIOUÁÉÍÓÚ]", sigla) and not re.fullmatch(r"[IVXLCDM]+", sigla)
    if sigla in SIGLAS_DELETREADAS or sin_vocales:  # «siglo XX» no se deletrea
        return _deletrear(sigla) + plural
    return m.group(0)


def _anglicismo(m):
    palabra, plural = m.group(1), m.group(2) or ""
    dicha = ANGLICISMOS.get(palabra.lower())
    if dicha is None:
        return m.group(0)
    return _capitalizar_como(palabra, dicha + plural.lower())


_UNIDADES_RE = "|".join(re.escape(u) for u in sorted(UNIDADES, key=len, reverse=True))


def preparar_es(texto):
    """Texto en espanol listo para la voz: anglicismos, siglas, numeros y formatos."""
    t = texto
    t = re.sub(r"\s*·\s*", ", ", t)                       # «Publicado hoy · 5 min»
    t = re.sub(r"\s&\s", " y ", t)
    t = re.sub(r"(?<!\w)['‘’]|['‘’](?!\w)", "", t)          # comillas simples, no apóstrofos
    t = re.sub(r"\bS\.\s?L\.", "ese ele", t)
    t = re.sub(r"\bS\.\s?A\.", "ese a", t)
    # Teclas: Ctrl+Alt+R, Ctrl+Shift+Espacio, Win+F5
    t = re.sub(r"(?<![\w+])(?:[A-Za-zÁÉÍÓÚáéíóú0-9]+\+)+[A-Za-zÁÉÍÓÚáéíóú0-9]+(?![\w+])",
               _teclas, t)
    # Archivos y extensiones: lector.py, notas.md, .json
    ext = "|".join(sorted(EXTENSIONES, key=len, reverse=True))
    t = re.sub(rf"(?<![\w.])([\w-]+)\.({ext})(?![\w])", _archivo, t, flags=re.I)
    t = re.sub(rf"(?<![\w.])\.({ext})(?![\w])",
               lambda m: f"punto {EXTENSIONES[m.group(1).lower()]}", t, flags=re.I)
    # Fechas: 2026-10-27 y 27/10/2026
    t = re.sub(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
               lambda m: _fecha(m.group(3), m.group(2), m.group(1)) or m.group(0), t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
               lambda m: _fecha(m.group(1), m.group(2), m.group(3)) or m.group(0), t)
    # Horas: 10:16, 9:00
    t = re.sub(r"(?<![\w:])([01]?\d|2[0-3]):([0-5]\d)(?![\w:])",
               lambda m: f"{_n(m.group(1))} en punto" if m.group(2) == "00"
               else f"{_n(m.group(1))} y {_n(m.group(2))}", t)
    # Versiones: v2.1, v0.3.4, 1.2.3, v5
    t = re.sub(r"(?<![\w.])[vV](\d+(?:\.\d+)*)(?![\w]|\.\d)",
               lambda m: "versión " + _version(m.group(1).split(".")), t)
    t = re.sub(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+)(?![\w]|[.,]\d)",
               lambda m: m.group(1).replace(".", ""), t)
    t = re.sub(r"(?<![\w.])(\d+(?:\.\d+){2,})(?![\w]|\.\d)",
               lambda m: _version(m.group(1).split(".")), t)
    # Ordinales: 1.º, 2ª
    if num2words is not None:
        t = re.sub(r"\b(\d{1,3})\.?º(?![CF\w])",
                   lambda m: num2words(int(m.group(1)), lang="es", to="ordinal"), t)
        t = re.sub(r"\b(\d{1,3})\.?ª",
                   lambda m: num2words(int(m.group(1)), lang="es", to="ordinal")[:-1] + "a", t)
    # Miles con punto: 1.000, 20.000.000
    t = re.sub(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+)(?![\w]|[.,]\d)",
               lambda m: m.group(1).replace(".", ""), t)
    # Resoluciones y multiplicadores: 1920x1080, 2x
    t = re.sub(r"\b(\d+)x(\d+)\b", r"\1 por \2", t)
    t = re.sub(r"\b(\d+(?:[.,]\d+)?)x(?![\w])", r"\1 veces", t)
    # Moneda delante: €5, $10
    t = re.sub(r"([€$])\s?(\d+(?:[.,]\d+)?)(?![\w])", r"\2 \1", t)
    # Unidades tras numero: 8 GB, 150 ms, 80 m², 20 °C
    t = re.sub(rf"(\d+(?:[.,]\d+)?)\s?({_UNIDADES_RE})(?![\w²])", _unidad, t)
    t = re.sub(r"(\d)\s?%", r"\1 por ciento", t)
    # Rangos: 3-5 -> de 3 a 5; «3 a 5» sin «de/entre» delante -> «de 3 a 5»
    t = re.sub(r"(?<![\w.,/-])(\d{1,4})-(\d{1,4})(?![\w.,/-])", r"\1 a \2", t)
    t = re.sub(r"(?<!\bde )(?<!\bdel )(?<!\bentre )(?<!\bdesde )(?<![\w.,])(\d{1,4}) a (\d{1,4})\b",
               r"de \1 a \2", t, flags=re.I)
    # Lenguajes y operaciones: C++, C#, 1+1
    t = re.sub(r"(?<![\w+])C\+\+(?![\w+])", "ce más más", t)
    t = re.sub(r"(?<![\w#])C#(?![\w#])", "ce sharp", t)
    t = re.sub(r"(\d)\s?\+\s?(?=\d)", r"\1 más ", t)
    # Negativos: -5
    t = re.sub(r"(?<![\w.,-])-(\d)", r"menos \1", t)
    # Decimales: 12,5 (coma) y 3.12 (punto)
    t = re.sub(r"(?<![\w.,])(\d+),(\d+)(?![\w]|,\d)", lambda m: _decimal(m, "coma"), t)
    t = re.sub(r"(?<![\w.,])(\d+)\.(\d+)(?![\w]|\.\d)", lambda m: _decimal(m, "punto"), t)
    # Anglicismos y siglas
    _cargar_extra()
    t = _RE_ANGLICISMO.sub(_anglicismo, t)
    t = re.sub(r"(?<![\w-])([A-ZÑ][A-ZÑ]{1,5}|SaaS)(s)?(?![\w-])", _sigla, t)
    # Enteros sueltos
    t = re.sub(r"(?<![\w])(\d+)(?![\w])", lambda m: _n(m.group(1)), t)
    return re.sub(r"\s+", " ", t).strip()


# --- Deteccion de tramos en ingles (R6) ---

def _clase(palabra):
    """'en', 'es' o 'neutra'."""
    p = palabra.lower().replace("’", "'")
    if p == "a":  # articulo ingles y preposicion espanola
        return "neutra"
    if p in FUNCIONALES_ES or any(c in _LETRAS_ES for c in p):
        return "es"
    if p in FUNCIONALES_EN or p in ANGLICISMOS or p.rstrip("s") in ANGLICISMOS:
        return "en"
    if re.search(r"th|sh|ck|ee|oo|w|k|ing$|ght|y$", p):
        return "en"
    if re.search(r"(o|a|os|as|ar|ir|ción|mente|ado|ido|ía)$", p):
        return "es"
    return "neutra"


def _tramos_ingles(frase):
    """Lista de (inicio, fin) de los tramos en ingles que cumplen R6."""
    palabras = [(m.start(), m.end(), _clase(m.group(0))) for m in _RE_PALABRA.finditer(frase)]
    tramos = []
    i = 0
    while i < len(palabras):
        if palabras[i][2] == "es":
            i += 1
            continue
        j = i
        while j < len(palabras) and palabras[j][2] != "es":
            j += 1
        run = palabras[i:j]
        # Bordes neutros: fuera si al otro lado hay espanol sin puntuacion en medio
        while run and run[0][2] == "neutra" and i > 0 and \
                not re.search(r"[.,;:!?…«»\"()]", frase[palabras[i - 1][1]:run[0][0]]):
            run = run[1:]
        while run and run[-1][2] == "neutra" and j < len(palabras) and \
                not re.search(r"[.,;:!?…«»\"()]", frase[run[-1][1]:palabras[j][0]]):
            run = run[:-1]
        ingles = [w for w in run if w[2] == "en"]
        funcional = any(frase[w[0]:w[1]].lower().replace("’", "'") in FUNCIONALES_EN
                        for w in run)
        if len(run) >= 3 and len(ingles) >= 2 and funcional:
            tramos.append((run[0][0], run[-1][1]))
        i = j
    return tramos


def _hablable(texto):
    return bool(re.search(r"[^\W_]", texto))


def segmentos(frase, idioma="es", ingles=False):
    """Frase -> [(texto, idioma)] lista para el motor (R2). Nunca vacia si hay algo que leer."""
    if (idioma or "es").lower() != "es":
        return [(frase, idioma)] if _hablable(frase) else []
    if not ingles:
        texto = preparar_es(frase)
        return [(texto, "es")] if _hablable(texto) else []

    _cargar_extra()
    salida = []
    pos = 0
    for inicio, fin in _tramos_ingles(frase):
        # La puntuacion que cierra el tramo va con el
        cola = re.match(r"[.,;:!?…'\"»)]*", frase[fin:])
        fin += cola.end()
        antes = preparar_es(frase[pos:inicio])
        if _hablable(antes):
            salida.append((antes, "es"))
        salida.append((frase[inicio:fin].strip(), "en"))
        pos = fin
    resto = preparar_es(frase[pos:])
    if _hablable(resto):
        salida.append((resto, "es"))
    return salida


def generar(motor, frase, idioma="es", ingles=False):
    """Frase -> audio con el motor; None si no queda nada que leer (R8).

    Un segmento en otro idioma (frase inglesa entera) tambien va por
    ``crear_segmentos`` para que se diga en ese idioma.
    """
    try:
        partes = segmentos(frase, idioma, ingles=ingles)
    except Exception:
        log.warning("No se pudo preparar la pronunciación; se lee tal cual", exc_info=True)
        partes = [(frase, idioma)]
    if not partes:
        return None
    if hasattr(motor, "crear_segmentos") and (len(partes) > 1 or partes[0][1] != idioma):
        return motor.crear_segmentos(partes)
    return motor.crear(" ".join(t for t, _ in partes))
