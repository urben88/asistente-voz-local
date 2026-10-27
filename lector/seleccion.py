"""Texto seleccionado en la ventana con el foco (para leer la selección antes que el portapapeles).

Dos caminos:
  1. UI Automation (TextPattern) sobre el control con el foco: sin efectos, pero no
     funciona dentro de ventanas de Escritorio remoto ni en apps sin accesibilidad.
  2. Ctrl+C temporal: se pulsa Ctrl+C en la ventana con el foco, se lee el
     portapapeles y se restaura el contenido anterior. Funciona casi en cualquier
     app (incluido Escritorio remoto con portapapeles redirigido).
     Aviso: en terminales Ctrl+C puede interrumpir; se puede desactivar en el panel.

Linux: selección primaria (wl-paste --primary / xclip -selection primary / xsel --primary).
Nunca lanza: si no hay selección devuelve "".
"""

import logging
import subprocess
import sys
import threading
import time

ES_WINDOWS = sys.platform == "win32"
log = logging.getLogger("lector.seleccion")

if ES_WINDOWS:
    import ctypes
    from ctypes import wintypes

MAX_NIVELES = 4        # el foco puede estar en un hijo del control de texto
MAX_PROFUNDIDAD = 3    # búsqueda hacia abajo en el árbol de accesibilidad
MAX_NODOS = 60         # tope para no tardar en ventanas enormes
ESPERA_COPIA = 1.2     # máximo esperando a que la app copie (Escritorio remoto tarda)
PASO = 0.06


# --- UI Automation ---

def _por_uia():
    """Selección por UI Automation: primero el foco y sus padres, luego sus hijos."""
    try:
        import uiautomation as auto

        def seleccion(control, niveles=0):
            patron = control.GetPattern(auto.PatternId.TextPattern)
            if patron is None:
                return ""
            try:
                rangos = patron.GetSelection() or []
            except Exception:
                return ""
            texto = "\n".join((r.GetText(-1) or "").strip() for r in rangos).strip()
            return texto

        control = auto.GetFocusedControl()
        actual = control
        for _ in range(MAX_NIVELES):
            if actual is None:
                break
            texto = seleccion(actual)
            if texto:
                return texto
            actual = actual.GetParentControl()

        # Algunas apps (navegadores, Electron) exponen el TextPattern en un hijo,
        # no en el control con el foco: se busca hacia abajo, con límite.
        raiz = control or auto.GetForegroundControl()
        if raiz is None:
            return ""
        pendientes = [(raiz, 0)]
        visitados = 0
        while pendientes and visitados < MAX_NODOS:
            nodo, nivel = pendientes.pop(0)
            visitados += 1
            texto = seleccion(nodo)
            if texto:
                return texto
            if nivel >= MAX_PROFUNDIDAD:
                continue
            try:
                pendientes.extend((hijo, nivel + 1) for hijo in nodo.GetChildren())
            except Exception:
                continue
    except Exception:
        log.debug("UI Automation no pudo leer la selección", exc_info=True)
    return ""


# --- Consola (conhost): selección nativa, sin portapapeles ---

if ES_WINDOWS:
    class _COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class _SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                    ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class _SELECCION(ctypes.Structure):
        _fields_ = [("dwFlags", wintypes.DWORD), ("dwSelectionAnchor", _COORD),
                    ("srSelection", _SMALL_RECT)]


def _por_consola():
    """Selección en una consola clásica (cmd/PowerShell): GetConsoleSelectionInfo.

    Solo funciona con consolas conhost de nuestra misma sesión; Windows Terminal y
    Escritorio remoto no lo exponen por aquí (para eso está UIA o el Ctrl+C).
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                     ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                     ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.GetConsoleSelectionInfo.argtypes = [ctypes.POINTER(_SELECCION)]
    kernel32.ReadConsoleOutputCharacterW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, wintypes.DWORD, _COORD,
        ctypes.POINTER(wintypes.DWORD)]

    hwnd = user32.GetForegroundWindow()
    clase = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, clase, 64)
    if clase.value != "ConsoleWindowClass":
        return ""

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    # Si el proceso ya tiene consola (p. ej. lanzado desde cmd), AttachConsole falla:
    # se suelta la propia y se engancha a la del foco.
    kernel32.FreeConsole()
    if not kernel32.AttachConsole(pid.value):
        return ""
    salida = None
    try:
        info = _SELECCION()
        if not kernel32.GetConsoleSelectionInfo(ctypes.byref(info)):
            return ""
        if not (info.dwFlags & 0x0002):  # CONSOLE_SELECTION_NOT_EMPTY
            return ""
        # Tras AttachConsole, GetStdHandle no sirve; CONOUT$ sí.
        salida = kernel32.CreateFileW("CONOUT$", 0xC0000000, 3, None, 3, 0, None)
        if not salida or salida == ctypes.c_void_p(-1).value:
            return ""
        r = info.srSelection
        lineas = []
        for y in range(r.Top, r.Bottom + 1):
            if y == r.Top:
                x0, n = r.Left, r.Right - r.Left + 1
            elif y == r.Bottom:
                x0, n = 0, r.Right + 1
            else:
                x0, n = 0, 512
            buffer = ctypes.create_unicode_buffer(n + 2)
            leidos = wintypes.DWORD()
            if kernel32.ReadConsoleOutputCharacterW(salida, buffer, n, _COORD(x0, y),
                                                    ctypes.byref(leidos)):
                lineas.append(buffer[:leidos.value].rstrip())
            else:
                lineas.append("")
        return "\n".join(lineas).strip()
    finally:
        if salida:
            kernel32.CloseHandle(salida)
        kernel32.FreeConsole()


# Ctrl+C temporal (Windows)

def _enviar_ctrl_c():
    import ctypes
    from ctypes import wintypes as w

    class TECLA(ctypes.Structure):
        _fields_ = [("wVk", w.WORD), ("wScan", w.WORD), ("dwFlags", w.DWORD),
                    ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class ENTRADA(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", TECLA)]
        _anonymous_ = ("u",)
        _fields_ = [("type", w.DWORD), ("u", _U)]

    user32 = ctypes.windll.user32
    user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(ENTRADA), ctypes.c_int]
    VK_CONTROL, VK_C = 0x11, 0x43

    def pulsa(vk, arriba):
        ev = ENTRADA(type=1, u=ENTRADA._U(ki=TECLA(vk, 0, 0x0002 if arriba else 0, 0, 0)))
        user32.SendInput(1, ctypes.byref(ev), ctypes.sizeof(ENTRADA))

    # El usuario puede seguir con Alt pulsado del atajo: se espera a que suelte
    time.sleep(0.2)
    pulsa(VK_CONTROL, False)
    pulsa(VK_C, False)
    time.sleep(0.05)
    pulsa(VK_C, True)
    pulsa(VK_CONTROL, True)


def _copiar_seleccion(anterior):
    """Ctrl+C y devuelve el texto nuevo; deja el portapapeles como estaba."""
    import sys

    # Sin import circular: se usan las funciones del modulo que ya esta cargado
    modulo = sys.modules.get("lector") or sys.modules.get("__main__")
    leer = getattr(modulo, "leer_portapapeles", None)
    escribir = getattr(modulo, "escribir_portapapeles", None)
    if leer is None or escribir is None:
        return ""

    _enviar_ctrl_c()
    limite = time.monotonic() + ESPERA_COPIA
    copiado = ""
    while time.monotonic() < limite:
        time.sleep(PASO)
        candidato = leer()
        if candidato and candidato != anterior:
            copiado = candidato
            break
    if copiado:
        escribir(anterior)  # se restaura lo que había antes
    return copiado


# --- Linux ---

def _seleccion_linux():
    for cmd in (["wl-paste", "--primary", "--no-newline"],
                ["xclip", "-o", "-selection", "primary"],
                ["xsel", "--primary", "--output"]):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=2)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return ""


def texto_seleccionado(portapapeles="", timeout=2.0):
    """Texto seleccionado ahora mismo ("" si no hay o si tarda demasiado).

    ``portapapeles`` es lo que ya había: sirve para detectar si Ctrl+C copió algo
    nuevo y para no confundir "no hay selección" con "la selección es el portapapeles".

    Se hace en un hilo con límite de tiempo: UI Automation puede quedarse colgada en
    una app lenta y **no debe bloquear el atajo** (si no, Ctrl+Alt+R deja de responder).
    """
    if not ES_WINDOWS:
        return _seleccion_linux()

    resultado = {}

    def trabajo():
        try:
            texto = _por_uia()
            if not texto:
                texto = _por_consola()
            if not texto:
                texto = _copiar_seleccion(portapapeles)
            resultado["texto"] = texto
        except Exception:
            log.warning("No se pudo leer la selección", exc_info=True)

    hilo = threading.Thread(target=trabajo, daemon=True)
    hilo.start()
    hilo.join(timeout)
    if hilo.is_alive():
        log.info("La selección tardó más de %.1f s: se usa el portapapeles", timeout)
    return resultado.get("texto", "")
