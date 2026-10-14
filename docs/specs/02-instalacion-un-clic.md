# Spec 02 — Instalación en 1 clic (instalador robusto y a prueba de terceros)

Estado: pendiente de implementar
Fecha: 2026-10-14

## Objetivo

Que cualquier persona pueda tener exactamente este asistente (Handy + Ollama con los mismos
modelos, atajos, prompts y diccionario) **copiando la carpeta y haciendo doble clic en un único
fichero**, sin abrir PowerShell ni editar nada. El instalador debe: comprobar lo necesario antes de
empezar, ser idempotente (se puede repetir), no pisar configuración local de Handy en PCs ya
configurados, verificar todo lo que descarga y terminar con un resumen + siguientes pasos claros.

Corrección que resuelve de paso: hoy `install.ps1` descarga `Qwen3.5-9B` pero la configuración usa
**`gemma4:e4b`** como modelo del asistente → en un PC nuevo el post-proceso fallaría por modelo
ausente. El estándar pasa a ser **`gemma4:e4b`** (decisión del usuario). En PCs sin GPU NVIDIA
suficiente, el instalador elegirá y configurará automáticamente `qwen3:4b-instruct` (ligero).

## Contexto técnico (verificado)

- La máquina de referencia tiene winget y nvidia-smi disponibles; 61,7 GB libres en C:.
- Handy se instala user-scope con winget (`cjpais.Handy`) → `%LOCALAPPDATA%\Handy\handy.exe`;
  Ollama con winget instala en `Program Files` / `%LOCALAPPDATA%\Programs\Ollama` y suele requerir
  elevación. Por eso el lanzador debe auto-elevarse (UAC).
- `ollama pull` necesita el servidor de Ollama escuchando en `http://127.0.0.1:11434`
  (tras instalar, arrancar `ollama app.exe` si no responde).
- Handy debe estar CERRADO para escribir su settings (si no, lo reescribe al salir). Ya está
  implementado ese control; el instalador lo comprueba al inicio y antes de aplicar.
- Config live de Handy: `%APPDATA%\com.pais.handy\settings_store.json`. Reescritura segura:
  `File.ReadAllText/WriteAllText` con UTF-8 sin BOM (¡`Get-Content -Raw` corrompe acentos!), y
  `ConvertTo-Json -Depth 20` si se reserializa (ya resuelto en `patch-config.ps1`).
- Modelo de dictado (Cohere Q5_K_M) y su descarga verificada (HF primero, mirror
  `blob.handy.computer` de respaldo, sha256 `14d02f1a…1558`, 1770270208 bytes, refs\main
  `dfa4adeb…b421`): lógica ya implementada y validada en `install.ps1` — mantenerla sin cambios.
- La config del repo ya apunta a `gemma4:e4b` (post_process_models.custom) → no hay que tocar
  `config/handy-settings.json` en esta spec.

## Requisitos

R1. **`Instalar.cmd`** (raíz del repo) — el "botón":
   - Doble clic en el Explorador: se auto-eleva con UAC (relanza `powershell` con `-Verb RunAs`
     ejecutando `scripts\install.ps1`) y, si ya es admin, ejecuta directo.
   - Excepción: si entre los argumentos viene `-Simular`, NO se eleva (la simulación no toca nada).
   - Pasa los argumentos extra al .ps1 (`%*`), soporta rutas con espacios (`%~dp0`).
   - Al terminar hace `pause` (que la ventana no se cierre de golpe).
   - Estilo sobrio en español sin tildes.

R2. **`scripts/install.ps1`** — reestructurado, con `param([switch]$Simular, [string]$AsistenteModelo = "", [switch]$NoAbrir)`:
   - **Preflight (antes de instalar nada)**; avisos claros y salida ordenada:
     - Windows 10/11 64 bits (si no, aviso).
     - `winget` presente; si no, mensaje con cómo conseguirlo ("Microsoft App Installer") y `exit 1`.
     - Espacio libre en la unidad del sistema ≥ 20 GB (si menos: aviso + confirmación `Read-Host`
       "Continuar de todas formas? (s/n)"; en `-Simular` no preguntar).
     - Conectividad básica (p. ej. `https://huggingface.co` y `https://ollama.com`): si falla,
       aviso (el mirror de dictado puede seguir funcionando) pero no bloquear.
     - Handy NO en ejecución: si está abierto, explicar (bandeja → Salir) y `exit 1` ANTES de nada.
   - **Modelo del asistente**: si `-AsistenteModelo` viene informado, usarlo; si no, detectar VRAM
     con `nvidia-smi` (≥ 8000 MiB → `gemma4:e4b`; sin NVIDIA/VRAM insuficiente/no disponible →
     `qwen3:4b-instruct`). Imprimir la elección y el motivo. En ambos casos se descarga también
     `qwen3:4b-instruct` como alternativa ligera.
   - **Fases** (renumerar y renombrar con claridad):
     1. Handy (winget; omitir si ya está; mostrar versión instalada; si < 0.9.8 avisar de
        `winget upgrade cjpais.Handy`).
     2. Ollama (winget si falta) + **asegurar servidor**: sondear `http://127.0.0.1:11434/api/tags`;
        si no responde, arrancar `"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"` (o `ollama serve`
        oculto) y reintentar hasta ~60 s; si no arranca, aviso claro con qué hacer.
     3. Modelos del asistente: `ollama pull <elegido>` + `ollama pull qwen3:4b-instruct`.
     4. Modelo de dictado (Cohere): lógica actual sin cambios (HF → mirror, sha256 + bytes,
        `refs\main` solo tras verificar, aviso rojo visible si no se pudo).
     5. Configuración de Handy (Handy cerrado, re-comprobar):
        - Si NO existe `settings_store.json` → copia completa de `config\handy-settings.json`.
        - Si existe → **merge de 3 campos** (`selected_model`, `custom_words`,
          `extra_recording_buffer_ms`) conservando el resto (micrófono, atajos, prompts) — mismo
          comportamiento ya validado en `patch-config.ps1` (backup `.bak`, UTF-8 sin BOM, -Depth 20,
          verificación posterior). Informar de qué camino se tomó.
        - Si el modelo de asistente elegido NO es `gemma4:e4b` (PC ligero), actualizar también
          `post_process_models.custom` en el live/config aplicada, para que ese PC quede coherente.
     - **Refactor permitido**: extraer la lógica de merge a `scripts/settings-merge.ps1`
       (dot-sourceable, función única) y que `patch-config.ps1` e `install.ps1` la compartan.
       Si el refactor complica, duplicar el bloque y anotarlo en el informe.
   - **Verificación final** (resumen legible): versión de Handy; modelo de dictado presente + sha256;
     `refs\main`; modelo elegido del asistente + `qwen3:4b-instruct` presentes en `ollama list`;
     campos aplicados del settings; y "siguientes pasos" (abrir Handy → elegir micrófono → probar
     los dos atajos), recordatorio de cómo cambiar de modelo y de que el README tiene el resto.
   - Al final (salvo `-Simular` o `-NoAbrir`): "Pulsa INTRO para abrir Handy ahora" → `Start-Process`.
   - **`-Simular`**: SOLO comprobaciones + informe de lo que haría (incluido qué modelo elegiría y
     si haría copia o merge). Prohibido descargar, instalar, copiar o tocar el settings live.
     Debe funcionar sin preguntas y sin efectos en la máquina del usuario.
   - Códigos de salida correctos (0 ok; 1 aborto por preflight/Handy abierto/fallo crítico).
   - Estilo del repo: español sin tildes, `Write-Host` con color, `$ErrorActionPreference = "Continue"`.

R3. **`README.md`** — reorganizado para terceros:
   - Arriba del todo, nueva sección **"Instalación en 1 clic"**: 1) consigue la carpeta (git clone o
     ZIP), 2) doble clic en `Instalar.cmd`, 3) acepta el UAC (Windows pedirá permisos), 4) espera
     (se descargan ~11 GB: qué es cada cosa y por qué), 5) al terminar: abre Handy, elige tu
     micrófono y prueba los dos atajos.
   - **Requisitos**: Windows 10/11 de 64 bits, ~20 GB libres recomendados (mínimo ~15), internet,
     GPU NVIDIA opcional (mejora velocidad).
   - **Qué hace el instalador** (resumen de fases) y **opciones avanzadas**:
     `-Simular`, `-AsistenteModelo qwen3:4b-instruct`, `-NoAbrir`; y cuándo usar
     `patch-config.ps1` / `apply-config.ps1` (la sección ya existe; enlazarla).
   - **Si algo falla**: sin winget, sin conexión, Handy abierto, antivirus bloqueando; y que el
     instalador se puede ejecutar de nuevo sin romper nada.
   - Dejar claro que el asistente estándar es **gemma4:e4b** y que en PCs sin GPU el instalador
     elige automáticamente `qwen3:4b-instruct`.
   - Mantener y no romper lo ya escrito (modelos de dictado, diccionario, troubleshooting).

R4. No tocar: `config/handy-settings.json` (ya correcto), `prompts/`, la lógica del modelo de
   dictado, atajos, `apply-config.ps1` (salvo lo del refactor de R2 si aplica).

R5. La configuración live de ESTA máquina no se toca en este trabajo (el parche de la spec 01 ya
   está aplicado y probado).

## Criterios de aceptación

- [ ] `Instalar.cmd` existe en la raíz, con auto-elevación (excepto `-Simular`), `pause` final y
      paso de argumentos; lógica revisada línea a línea.
- [ ] `scripts/install.ps1 -Simular` se ejecuta en esta máquina SIN efectos ni preguntas y reporta:
      SO, winget, disco, conectividad, estado de Handy (¿instalado? ¿versión? ¿abierto?),
      estado de Ollama (¿instalado? ¿servidor arriba?), modelos presentes/ausentes, modelo de
      asistente que elegiría y por qué, estado del modelo de dictado, y si haría copia o merge.
- [ ] Los `.ps1` parsean sin errores (`Parser::ParseFile`) y no hay rutas relativas frágiles.
- [ ] El merge de config conserva `selected_microphone`, atajos y prompts (probar en un
      sandbox con `$env:APPDATA` redirigido; nunca el fichero real).
- [ ] README con la sección de 1 clic y opciones avanzadas.
- [ ] Informe final: ficheros y líneas, comandos, salidas reales de `-Simular`, dudas.

## Fuera de alcance

- Firmar digitalmente el instalador, crear releases/instalador .exe, desinstalador.
- Cambiar modelos de dictado alternativos o el diccionario.
- Automatizar la selección de micrófono (depende de cada PC).
