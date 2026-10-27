"""Control de Handy, Ollama y del proceso del lector (spec 07, R5).

Nada de aqui lanza excepciones hacia la UI: todo devuelve ``Resultado(ok, mensaje)``
o un valor neutro (lista vacia, False) si algo no esta disponible. Los comandos
externos van con timeout y las acciones lentas se llaman desde hilos del panel.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    from . import estado
except ImportError:  # ejecutado como script suelto desde panel/
    import estado

log = logging.getLogger("panel.control")

ES_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

# Solo pruebas/simulacion: las acciones reales sobre Handy/Ollama/lector no se ejecutan
SIMULAR = False

_pid_lector = None  # PID arrancado por este panel (atajo barato para apagarlo)


class Resultado:
    def __init__(self, ok, mensaje=""):
        self.ok = bool(ok)
        self.mensaje = mensaje

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"Resultado(ok={self.ok!r}, mensaje={self.mensaje!r})"


def _banderas():
    return CREATE_NO_WINDOW if ES_WINDOWS else 0


def _run(cmd, timeout=10, **kw):
    """subprocess.run sin ventana y sin excepciones: CompletedProcess o None."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                              timeout=timeout, creationflags=_banderas(),
                              stdin=subprocess.DEVNULL, **kw)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("No se pudo ejecutar %s: %s", cmd, e)
        return None


def _popen(cmd, cwd=None):
    """Proceso desacoplado (sigue vivo si se cierra el panel)."""
    return subprocess.Popen(
        cmd, cwd=str(cwd) if cwd else None,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=(DETACHED_PROCESS | CREATE_NO_WINDOW) if ES_WINDOWS else 0,
        close_fds=True,
        start_new_session=not ES_WINDOWS,
    )


# --- Handy (el panel solo cambia el modelo del resumen) ---

def gpu_disponible():
    """True si hay una GPU NVIDIA que responda (para recomendar XTTS o Piper)."""
    if SIMULAR:
        return True
    try:
        exe = shutil.which("nvidia-smi")
        if not exe and ES_WINDOWS:
            exe = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe")
        if not exe:
            return False
        r = _run([exe, "-L"], timeout=8)
        return bool(r and r.returncode == 0 and "GPU" in (r.stdout or "").upper())
    except Exception:
        log.exception("No se pudo comprobar la GPU")
        return False


def handy_en_marcha():
    if SIMULAR:
        return False
    try:
        if ES_WINDOWS:
            r = _run(["tasklist", "/FI", "IMAGENAME eq handy.exe", "/NH"], timeout=8)
            return bool(r and r.returncode == 0 and "handy.exe" in r.stdout.lower())
        r = _run(["pgrep", "-x", "handy"], timeout=5)
        return bool(r and r.returncode == 0 and r.stdout.strip())
    except Exception:
        log.exception("No se pudo comprobar si Handy esta en marcha")
        return False


# --- Ollama: modelos y modelo del resumen ---

RECOMENDADOS_RESUMEN = {
    "gemma4:e4b": "★ el que usas: rápido, cabe en la GPU y resume bien.",
    "qwen3:4b-instruct": "★ ligero y bueno para resumir textos largos.",
    "phi4-mini:latest": "★ muy rápido para resúmenes cortos.",
    "qwen2.5:3b-instruct": "★ pequeño; resúmenes sencillos.",
}


def nota_modelo_resumen(nombre, mb=0):
    """Frase corta para la lista: recomendación o aviso por tamaño."""
    if nombre in RECOMENDADOS_RESUMEN:
        return RECOMENDADOS_RESUMEN[nombre]
    if mb >= 4500:
        return "⚠ grande: con el lector en la GPU puede no caber y tardar más."
    return ""


_CACHE_MODELOS = {"cuando": 0.0, "lista": []}


def modelos_ollama(recargar=False):
    """Modelos instalados en Ollama: [{"nombre", "mb", "nota"}]. Cachea 10 s."""
    if SIMULAR:
        return []
    ahora = time.monotonic()
    if not recargar and (ahora - _CACHE_MODELOS["cuando"]) < 10:
        return [dict(m) for m in _CACHE_MODELOS["lista"]]
    exe = _ollama_exe()
    if exe is None:
        return []
    try:
        r = _run([str(exe), "list"], timeout=15)
        modelos = []
        for linea in (r.stdout or "").splitlines()[1:]:
            partes = linea.split()
            if len(partes) < 3 or not partes[0]:
                continue
            nombre = partes[0]
            mb = 0
            try:
                if len(partes) > 3 and partes[2].upper() == "GB":
                    mb = int(float(partes[1]) * 1024)
                elif len(partes) > 3 and partes[2].upper() == "MB":
                    mb = int(float(partes[1]))
                elif "GB" in linea:
                    mb = int(float(linea.split("GB")[0].split()[-1]) * 1024)
                elif "MB" in linea:
                    mb = int(float(linea.split("MB")[0].split()[-1]))
            except (ValueError, IndexError):
                mb = 0
            modelos.append({"nombre": nombre, "mb": mb,
                            "nota": nota_modelo_resumen(nombre, mb)})
        _CACHE_MODELOS.update(cuando=ahora, lista=modelos)
        return [dict(m) for m in modelos]
    except Exception:
        log.exception("No se pudo listar los modelos de Ollama")
        return []


def _handy_exe():
    cfg = estado.cargar_panel_json()
    candidatos = [cfg.get("handy_exe") or ""]
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        candidatos.append(str(Path(local) / "Handy" / "handy.exe"))
        candidatos.append(shutil.which("handy") or "")
    else:
        candidatos.append(shutil.which("handy") or "")
    for ruta in candidatos:
        if ruta and Path(ruta).is_file():
            return Path(ruta)
    return None


def _ollama_exe():
    cfg = estado.cargar_panel_json()
    candidatos = [cfg.get("ollama_exe") or ""]
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        candidatos.append(str(Path(local) / "Programs" / "Ollama" / "ollama.exe"))
    candidatos.append(shutil.which("ollama") or "")
    for ruta in candidatos:
        if ruta and Path(ruta).is_file():
            return Path(ruta)
    return None


def parar_handy():
    """Cierra Handy (WM_CLOSE y, si no se va, forzado). Devuelve Resultado."""
    if SIMULAR:
        return Resultado(True, "Handy cerrado (simulado)")
    if not handy_en_marcha():
        return Resultado(True, "Handy ya estaba cerrado")
    try:
        if ES_WINDOWS:
            _run(["taskkill", "/IM", "handy.exe"], timeout=8)
        else:
            _run(["pkill", "-x", "handy"], timeout=5)
        limite = time.monotonic() + 5
        while time.monotonic() < limite:
            if not handy_en_marcha():
                return Resultado(True, "Handy cerrado")
            time.sleep(0.25)
        if ES_WINDOWS:
            _run(["taskkill", "/F", "/IM", "handy.exe"], timeout=8)
        else:
            _run(["pkill", "-9", "-x", "handy"], timeout=5)
        time.sleep(0.5)
        if handy_en_marcha():
            return Resultado(False, "No consigo cerrar Handy")
        return Resultado(True, "Handy cerrado (forzado)")
    except Exception as e:
        log.exception("Error cerrando Handy")
        return Resultado(False, f"No se pudo cerrar Handy: {e}")


def arrancar_handy():
    if SIMULAR:
        return Resultado(True, "Handy abierto (simulado)")
    if handy_en_marcha():
        return Resultado(True, "Handy ya estaba abierto")
    exe = _handy_exe()
    if exe is None:
        return Resultado(False, "No encuentro Handy en %LOCALAPPDATA%\\Handy\\handy.exe")
    try:
        _popen([str(exe)], cwd=exe.parent)
        for _ in range(30):
            if handy_en_marcha():
                return Resultado(True, "Handy abierto")
            time.sleep(0.1)
        return Resultado(True, "Handy lanzado")
    except Exception as e:
        log.exception("Error arrancando Handy")
        return Resultado(False, f"No se pudo abrir Handy: {e}")


def cambiar_modelo_resumen(modelo):
    """Pone ``modelo`` como modelo de post-procesado de Handy (resumen/asistente).

    Handy reescribe su configuración al salir, así que se cierra antes de editar y se
    vuelve a abrir después. Se deja una copia ``.bak-panel`` y se verifica el cambio.
    """
    modelo = (modelo or "").strip()
    if not modelo:
        return Resultado(False, "Elige un modelo")
    if SIMULAR:
        return Resultado(True, f"Modelo de resumen: {modelo} (simulado)")

    ruta = Path(estado.ruta_handy_settings())
    if not ruta.is_file():
        return Resultado(False, f"No encuentro la configuración de Handy en {ruta}")

    cerrado = parar_handy()
    if not cerrado.ok:
        return cerrado

    try:
        respaldo = Path(str(ruta) + ".bak-panel")
        respaldo.write_text(ruta.read_text(encoding="utf-8"), encoding="utf-8")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        ajustes = datos.setdefault("settings", {})
        proveedor = str(ajustes.get("post_process_provider_id") or "custom")
        modelos = ajustes.get("post_process_models")
        if not isinstance(modelos, dict):
            modelos = {}
            ajustes["post_process_models"] = modelos
        anterior = modelos.get(proveedor) or "ninguno"
        modelos[proveedor] = modelo
        tmp = Path(str(ruta) + ".tmp")
        tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, ruta)

        guardado = json.loads(ruta.read_text(encoding="utf-8"))
        if (guardado.get("settings", {}).get("post_process_models") or {}).get(proveedor) != modelo:
            raise ValueError("la configuración no se ha guardado")
    except Exception as e:
        log.exception("No se pudo cambiar el modelo de resumen")
        arrancar_handy()
        return Resultado(False, f"No se pudo cambiar el modelo: {e}")

    abierto = arrancar_handy()
    if not abierto.ok:
        return Resultado(False, f"Modelo guardado, pero no pude abrir Handy: {abierto.mensaje}")
    return Resultado(True, f"Resumen con {modelo} (antes: {anterior}). Handy reiniciado.")


def _ollama_exe():
    cfg = estado.cargar_panel_json()
    candidatos = [cfg.get("ollama_exe") or ""]
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        candidatos.append(str(Path(local) / "Programs" / "Ollama" / "ollama.exe"))
    candidatos.append(shutil.which("ollama") or "")
    for ruta in candidatos:
        if ruta and Path(ruta).is_file():
            return Path(ruta)
    return None


def ollama_en_uso():
    """Modelos cargados segun ``ollama ps`` (columna NAME); [] si no hay Ollama."""
    if SIMULAR:
        return []
    exe = _ollama_exe()
    if exe is None:
        return []
    try:
        r = _run([str(exe), "ps"], timeout=10)
        if r is None or r.returncode != 0:
            return []
        modelos = []
        for linea in r.stdout.splitlines():
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split()
            nombre = partes[0]
            if nombre.upper() == "NAME":  # cabecera
                continue
            if set(nombre) <= {"-", "="}:
                continue
            if nombre not in modelos:
                modelos.append(nombre)
        return modelos
    except Exception:
        log.exception("No se pudo consultar ollama ps")
        return []


def parar_ollama():
    """Ya no se usa: los atajos de dictado y lectura conviven, no se apaga Ollama.

    Se deja por si algun dia hace falta un boton explicito de «liberar GPU».
    """
    if SIMULAR:
        return 0
    exe = _ollama_exe()
    if exe is None:
        return 0
    parados = 0
    for modelo in ollama_en_uso():
        r = _run([str(exe), "stop", modelo], timeout=20)
        if r is not None and r.returncode == 0:
            parados += 1
        else:
            log.warning("No se pudo parar el modelo %s", modelo)
    return parados


def gpu_libre():
    return not handy_en_marcha() and not ollama_en_uso()


# --- Proceso del lector ---

def python_venv():
    """Interprete del venv del lector (para descargar voces)."""
    if ES_WINDOWS:
        return estado.LECTOR_DIR / ".venv" / "Scripts" / "python.exe"
    return estado.LECTOR_DIR / ".venv" / "bin" / "python"


def _vivo(pid):
    """True si el proceso sigue vivo (sin lanzar excepciones)."""
    try:
        if ES_WINDOWS:
            import ctypes
            from ctypes import wintypes
            PROCESO = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.restype = ctypes.c_void_p
            handle = kernel32.OpenProcess(PROCESO, False, int(pid))
            if not handle:
                return False
            try:
                codigo = wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(codigo)):
                    return False
                return codigo.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(ctypes.c_void_p(handle))
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False
    except Exception:
        log.exception("No se pudo comprobar el proceso %s", pid)
        return False


def _pids_lector():
    """PIDs de procesos python que ejecutan el ``lector.py`` de nuestra BASE."""
    script = str(estado.LECTOR_DIR / "lector.py")
    if ES_WINDOWS:
        ps = ('Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\'" | '
              f"Where-Object {{ $_.CommandLine -like '*{script}*' }} | "
              "Select-Object -ExpandProperty ProcessId")
        r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], timeout=15)
        pids = []
        if r is not None and r.returncode == 0:
            for linea in r.stdout.splitlines():
                linea = linea.strip()
                if linea.isdigit():
                    pids.append(int(linea))
        return pids
    r = _run(["pgrep", "-f", script], timeout=5)
    if r is None or r.returncode != 0:
        return []
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]


def arrancar_lector():
    global _pid_lector
    if SIMULAR:
        return Resultado(True, "Lector arrancado (simulado)")
    # El lector sale solo si estado.json dice lector=false: se marca antes de lanzarlo
    estado.guardar_estado(lector=True)
    pids = _pids_lector()
    if pids:
        _pid_lector = pids[0]
        return Resultado(True, "El lector ya estaba en marcha")
    script = estado.LECTOR_DIR / "lector.py"
    if not script.is_file():
        return Resultado(False, f"No encuentro el lector en {script}")
    try:
        proceso = _popen([sys.executable, str(script)], cwd=estado.LECTOR_DIR)
        _pid_lector = proceso.pid
        log.info("Lector arrancado (pid %s)", proceso.pid)
        return Resultado(True, "Lector arrancado")
    except Exception as e:
        log.exception("No se pudo arrancar el lector")
        return Resultado(False, f"No se pudo arrancar el lector: {e}")


def apagar_lector():
    """Pide al lector que se cierre (``lector=false``); si no se va en 5 s, lo mata."""
    global _pid_lector
    if SIMULAR:
        estado.guardar_estado(lector=False)
        return Resultado(True, "Lector apagado (simulado)")
    # El python del venv de uv lanza un hijo con el interprete base: hay que vigilar ambos.
    # Se buscan antes de pedir el cierre (el lector se va en ~0,5 s y ya no aparecerian).
    pids = set(_pids_lector())
    if _pid_lector and _vivo(_pid_lector):
        pids.add(_pid_lector)
    pids = sorted(pids)
    estado.guardar_estado(lector=False)
    if not pids:
        return Resultado(True, "El lector no estaba en marcha")
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        if not any(_vivo(pid) for pid in pids):
            _pid_lector = None
            return Resultado(True, "Lector apagado")
        time.sleep(0.2)
    for pid in pids:
        try:
            if ES_WINDOWS:
                _run(["taskkill", "/F", "/PID", str(pid)], timeout=8)
            else:
                os.kill(int(pid), 9)
        except OSError:
            pass
    _pid_lector = None
    if any(_vivo(pid) for pid in pids):
        return Resultado(False, "No consigo cerrar el lector")
    return Resultado(True, "Lector cerrado a la fuerza")
