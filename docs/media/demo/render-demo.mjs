/**
 * Genera la demo visual del README a partir de storyboard.json y demo.html.
 *
 *   node docs/media/demo/render-demo.mjs            # todo
 *   node docs/media/demo/render-demo.mjs --sin-voz   # sin narración (vídeo mudo)
 *
 * Piezas que usa (autodetectadas, se pueden forzar por entorno):
 *   - Chrome/Chromium headless de Playwright  (CHROME)
 *   - narrador.py + motor del lector (XTTS…)  (LECTOR_PYTHON, LECTOR_DIR)
 *   - piper + voz del proyecto (recambio)     (PIPER_EXE, PIPER_VOZ)
 *   - ffmpeg en el PATH                       (FFMPEG)
 *
 * El motor de voz se elige en el bloque "narrador" de storyboard.json: los
 * motores del entorno del lector (xtts, chatterbox, kokoro, supertonic) van por
 * narrador.py; piper se queda como recambio; --sin-voz genera el vídeo mudo.
 *
 * Nada de esto se ejecuta al instalar el asistente: es una herramienta de
 * desarrollo para regenerar los medios de docs/media/.
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(HERE, '..', '..', '..');
const SALIDA = path.resolve(HERE, '..');
const FPS = 25;

function log(...a) { console.log(...a); }

function falla(msg) { console.error('ERROR: ' + msg); process.exit(1); }

async function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: ['pipe', 'pipe', 'pipe'], ...opts });
    let out = '', err = '';
    p.stdout.on('data', d => { out += d; });
    p.stderr.on('data', d => { err += d; });
    p.on('error', reject);
    p.on('close', code => resolve({ code, out, err }));
    if (opts.stdin) { p.stdin.end(opts.stdin); }
  });
}

async function mustRun(cmd, args, opts) {
  const r = await run(cmd, args, opts);
  if (r.code !== 0) falla(`${cmd} ${args.join(' ')}\n${r.err.slice(-2000)}`);
  return r;
}

/* ---------------- detección de herramientas ---------------- */

async function existe(p) { try { await fs.access(p); return true; } catch { return false; } }

async function buscarChrome() {
  if (process.env.CHROME && await existe(process.env.CHROME)) return process.env.CHROME;
  const raiz = path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright');
  const candidatos = [];
  let dirs = [];
  try { dirs = await fs.readdir(raiz); } catch { /* sin Playwright */ }
  for (const d of dirs.filter(d => d.startsWith('chromium-')).sort()) {
    const p = path.join(raiz, d, 'chrome-win64', 'chrome.exe');
    if (await existe(p)) candidatos.push(p);
  }
  for (const p of [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ]) if (await existe(p)) candidatos.push(p);
  if (!candidatos.length) return null;
  return candidatos[candidatos.length - 1];
}

async function buscarPiper() {
  const base = path.join(process.env.LOCALAPPDATA ?? path.join(os.homedir(), 'AppData', 'Local'),
    'asistente-voz-local', 'lector');
  const exe = process.env.PIPER_EXE ?? path.join(base, '.venv', 'Scripts', 'piper.exe');
  const voz = process.env.PIPER_VOZ ?? path.join(base, 'voces', 'piper', 'es_ES-davefx-medium.onnx');
  if (await existe(exe) && await existe(voz)) return { exe, voz };
  return null;
}

// motores de texto a voz que atiende narrador.py (los del entorno del lector)
const MOTORES_LECTOR = new Set(['xtts', 'chatterbox', 'kokoro', 'supertonic']);

async function buscarLector() {
  const base = path.join(process.env.LOCALAPPDATA ?? path.join(os.homedir(), 'AppData', 'Local'),
    'asistente-voz-local', 'lector');
  const python = process.env.LECTOR_PYTHON ?? path.join(base, '.venv', 'Scripts', 'python.exe');
  const lector = process.env.LECTOR_DIR ?? base;
  if (!await existe(python)) return null;
  if (!await existe(path.join(lector, 'motor.py'))) return null;
  if (!await existe(path.join(HERE, 'narrador.py'))) return null;
  return { python, lector };
}

/* ---------------- audio: una pista por escena ---------------- */

async function duracion(archivo) {
  const r = await mustRun('ffprobe', ['-v', 'error', '-show_entries', 'format=duration',
    '-of', 'csv=p=0', archivo]);
  return Number.parseFloat(r.out.trim());
}

async function normalizarVoz(origen, destino) {
  // recorta silencios de cabeza y cola para que el ritmo no dependa del motor
  await mustRun('ffmpeg', ['-y', '-i', origen, '-af',
    'silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,' +
    'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,' +
    'aresample=44100',
    '-ac', '1', destino], {});
  return duracion(destino);
}

async function sintetizar(piper, texto, destino, tmp) {
  const crudo = path.join(tmp, path.basename(destino, '.wav') + '.crudo.wav');
  await mustRun(piper.exe, ['-m', piper.voz, '-f', crudo], { stdin: texto + '\n' });
  return normalizarVoz(crudo, destino);
}

/*
 * Narración con el motor del entorno del lector (XTTS y compañía) mediante
 * narrador.py: una sola ejecución para todas las frases, porque cargar el
 * modelo cuesta más que sintetizar. Devuelve las duraciones por escena.
 */
async function narrarConLector(lector, cfg, escenas, locutado, tmp) {
  const conVoz = escenas.map((e, i) => ({ i, texto: e.narracion })).filter(x => x.texto);
  const crudo = path.join(tmp, 'voz-lector');
  await fs.mkdir(crudo, { recursive: true });

  const textos = path.join(tmp, 'textos.json');
  await fs.writeFile(textos, JSON.stringify(conVoz.map(x => x.texto)), 'utf8');

  const r = await run(lector.python, [
    path.join(HERE, 'narrador.py'),
    '--textos', textos,
    '--salida', crudo,
    '--motor', cfg.motor,
    '--voz', cfg.voz,
    '--idioma', cfg.idioma,
    '--velocidad', String(cfg.velocidad),
    '--lector', lector.lector,
  ], { env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  for (const l of r.out.split(/\r?\n/)) if (l.trim()) log('    ' + l.trim());
  if (r.code !== 0) {
    log('  narrador.py falló: ' + r.err.trim().split(/\r?\n/).slice(-3).join(' | '));
    return null;
  }

  const duraciones = escenas.map(() => 0);
  for (const [k, { i }] of conVoz.entries()) {
    const origen = path.join(crudo, `voz_${k}.wav`);
    if (!await existe(origen)) {
      log('  falta ' + path.basename(origen));
      return null;
    }
    duraciones[i] = await normalizarVoz(origen, path.join(locutado, `voz_n_${i}.wav`));
  }
  return duraciones;
}

async function narrarConPiper(piper, escenas, locutado, tmp) {
  const duraciones = escenas.map(() => 0);
  for (const [i, e] of escenas.entries()) {
    if (!e.narracion) continue;
    duraciones[i] = await sintetizar(piper, e.narracion,
      path.join(locutado, `voz_${i}.wav`), tmp);
  }
  return duraciones;
}

/* ---------------- Chrome por CDP ---------------- */

class CDP {
  constructor(url) { this.url = url; this.id = 0; this.pend = new Map(); }

  static async conectar(wsUrl) {
    const c = new CDP(wsUrl);
    c.ws = new WebSocket(wsUrl);
    await new Promise((res, rej) => {
      c.ws.addEventListener('open', res, { once: true });
      c.ws.addEventListener('error', rej, { once: true });
    });
    c.ws.addEventListener('message', ev => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      const p = c.pend.get(msg.id);
      if (!p) return;
      c.pend.delete(msg.id);
      msg.error ? p.rej(new Error(msg.method + ': ' + JSON.stringify(msg.error))) : p.res(msg.result);
    });
    return c;
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pend.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  cerrar() { try { this.ws.close(); } catch { /* ya cerrado */ } }
}

async function esperarJson(url, intentos = 120) {
  for (let i = 0; i < intentos; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return await r.json();
    } catch { /* todavía arrancando */ }
    await new Promise(r => setTimeout(r, 100));
  }
  throw new Error('Chrome no respondió en ' + url);
}

async function renderizarFrames({ chrome, html, cfg, total, carpetaFrames, posterEn }) {
  const perfil = path.join(os.tmpdir(), 'demo-chrome-' + process.pid);
  const puerto = 9300 + (process.pid % 300);
  const args = [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
    '--no-first-run', '--no-default-browser-check', '--disable-extensions',
    '--force-device-scale-factor=1', '--window-size=960,540',
    '--remote-debugging-port=' + puerto, '--user-data-dir=' + perfil,
    'file:///' + html.replace(/\\/g, '/'),
  ];
  const proc = spawn(chrome, args, { stdio: ['ignore', 'pipe', 'pipe'] });
  let err = '';
  proc.stderr.on('data', d => { err += d; });

  try {
    let lista = [];
    for (let i = 0; i < 100; i++) {
      try { lista = await esperarJson(`http://127.0.0.1:${puerto}/json/list`, 1); } catch { lista = []; }
      if (lista.some(t => t.type === 'page' && t.webSocketDebuggerUrl)) break;
      await new Promise(r => setTimeout(r, 150));
    }
    const pagina = lista.find(t => t.type === 'page' && t.webSocketDebuggerUrl);
    if (!pagina) falla('no encontré la pestaña de Chrome.\n' + err.slice(-800));

    const cdp = await CDP.conectar(pagina.webSocketDebuggerUrl);
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride',
      { width: 960, height: 540, deviceScaleFactor: 1, mobile: false });

    for (let i = 0; i < 100; i++) {
      const r = await cdp.send('Runtime.evaluate', { expression: 'document.readyState', returnByValue: true });
      if (r.result?.value === 'complete') break;
      await new Promise(r2 => setTimeout(r2, 100));
    }

    await cdp.send('Runtime.evaluate', { expression: `window.configure(${JSON.stringify(cfg)})` });

    await fs.mkdir(carpetaFrames, { recursive: true });
    const n = Math.round(total * FPS);
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const t = i / FPS;
      await cdp.send('Runtime.evaluate', { expression: `window.renderAt(${t.toFixed(4)})` });
      const shot = await cdp.send('Page.captureScreenshot',
        { format: 'png', fromSurface: true, captureBeyondViewport: false });
      await fs.writeFile(path.join(carpetaFrames, 'frame_' + String(i + 1).padStart(5, '0') + '.png'),
        Buffer.from(shot.data, 'base64'));
      if ((i + 1) % 100 === 0 || i + 1 === n) {
        const seg = (Date.now() - t0) / 1000;
        log(`  fotogramas ${i + 1}/${n}  (${seg.toFixed(1)} s)`);
      }
    }

    if (posterEn != null) {
      await cdp.send('Runtime.evaluate', { expression: `window.renderAt(${posterEn.toFixed(4)})` });
      const shot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true });
      await fs.writeFile(path.join(SALIDA, 'demo-asistente-voz.png'), Buffer.from(shot.data, 'base64'));
      log('  póster generado');
    }

    cdp.cerrar();
    return n;
  } finally {
    proc.kill('SIGKILL');
    await fs.rm(perfil, { recursive: true, force: true }).catch(() => {});
  }
}

/* ---------------- utilidades de tiempo ---------------- */

const dos = n => String(n).padStart(2, '0');
function srtTime(s) {
  const ms = Math.round((s - Math.floor(s)) * 1000);
  const total = Math.floor(s);
  return `${dos(Math.floor(total / 3600))}:${dos(Math.floor(total / 60) % 60)}:${dos(total % 60)},${String(ms).padStart(3, '0')}`;
}

/* ---------------- principal ---------------- */

async function main() {
  const sinVoz = process.argv.includes('--sin-voz');
  const guion = JSON.parse(await fs.readFile(path.join(HERE, 'storyboard.json'), 'utf8'));
  const escenas = guion.escenas;
  const tmp = path.join(os.tmpdir(), 'demo-asistente-' + process.pid);
  await fs.mkdir(tmp, { recursive: true });

  /* 0. motor de voz: --sin-voz > storyboard.narrador > recambio piper > mudo */
  const narradorCfg = {
    motor: guion.narrador?.motor ?? 'piper',
    voz: guion.narrador?.voz ?? 'Luis Moray',
    idioma: guion.narrador?.idioma ?? 'es',
    velocidad: guion.narrador?.velocidad ?? 1.0,
  };
  const piperVoz = guion.narrador?.recambio_piper ?? 'es_ES-davefx-medium';
  let motor = 'mudo';
  let voz = null;
  let piper = null;
  let lector = null;

  if (!sinVoz) {
    if (narradorCfg.motor === 'piper') {
      piper = await buscarPiper();
      if (piper) { motor = 'piper'; voz = piperVoz; }
    } else if (MOTORES_LECTOR.has(narradorCfg.motor)) {
      lector = await buscarLector();
      if (lector) { motor = narradorCfg.motor; voz = narradorCfg.voz; }
      else log(`narrador.py no disponible para ${narradorCfg.motor}: recambio piper`);
    } else {
      log(`motor "${narradorCfg.motor}" desconocido: recambio piper`);
    }
    if (motor === 'mudo') {
      piper = piper ?? await buscarPiper();
      if (piper) { motor = 'piper'; voz = piperVoz; }
      else log('piper tampoco está disponible: vídeo mudo');
    }
  }
  log(`narración: ${motor === 'mudo' ? 'sin voz' : motor + ' · voz «' + voz + '»'}`);

  const chrome = await buscarChrome();
  if (!chrome) falla('no encontré Chrome/Chromium (define CHROME=/ruta/chrome.exe)');

  /* 1. narración y duración de cada escena */
  log('1/5 narración');
  const locutado = path.join(tmp, 'voz');
  await fs.mkdir(locutado, { recursive: true });
  let duraciones = escenas.map(() => 0);
  if (motor === 'piper') {
    duraciones = await narrarConPiper(piper, escenas, locutado, tmp);
  } else if (motor !== 'mudo') {
    const medidas = await narrarConLector(lector, narradorCfg, escenas, locutado, tmp);
    if (medidas) {
      duraciones = medidas;
    } else {
      log('  recambio: piper');
      piper = await buscarPiper();
      if (piper) {
        motor = 'piper'; voz = piperVoz;
        duraciones = await narrarConPiper(piper, escenas, locutado, tmp);
      } else {
        log('  piper tampoco está disponible: vídeo mudo');
        motor = 'mudo'; voz = null;
      }
    }
  }
  const tiempos = escenas.map((e, i) => {
    const d = duraciones[i];
    log(d > 0 ? `  · ${e.id}: ${d.toFixed(2)} s de voz` : `  · ${e.id}: sin voz`);
    return Math.max(e.min, d > 0 ? 0.30 + d + 0.30 : 0);
  });

  const a = [0];
  for (const t of tiempos) a.push(a[a.length - 1] + t);
  const total = a[a.length - 1];
  log(`  duración total: ${total.toFixed(2)} s`);

  const caps = escenas.map((e, i) => [a[i], a[i + 1], e.subtitulo]);
  const cfg = { a, caps, fps: FPS };

  /* 2. fotogramas */
  log('2/5 fotogramas (Chrome headless)');
  const carpetaFrames = path.join(tmp, 'frames');
  // portada: el fotograma del lector (selección + píldora rosa), el más representativo
  const posterIdx = Math.max(0, escenas.findIndex(e => e.id === 'lector'));
  const posterEn = a[posterIdx] + (a[posterIdx + 1] - a[posterIdx]) * 0.85;
  await renderizarFrames({
    chrome, html: path.join(HERE, 'demo.html'), cfg, total, carpetaFrames, posterEn,
  });

  /* 3. vídeo mudo */
  log('3/5 vídeo H.264');
  const videoMudo = path.join(tmp, 'video.mp4');
  await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS),
    '-i', path.join(carpetaFrames, 'frame_%05d.png'),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', videoMudo]);

  /* 4. narración mezclada con el vídeo */
  const mp4 = path.join(SALIDA, 'demo-asistente-voz.mp4');
  const hayNarracion = motor !== 'mudo';
  if (hayNarracion) {
    log('4/5 narración y mezcla');
    const segmentos = [];
    for (let i = 0; i < escenas.length; i++) {
      const L = tiempos[i];
      const seg = path.join(tmp, `seg_${i}.wav`);
      const pista = path.join(locutado, motor === 'piper' ? `voz_${i}.wav` : `voz_n_${i}.wav`);
      if (await existe(pista)) {
        await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-i', pista, '-af',
          `adelay=300|300,apad`, '-t', L.toFixed(3), '-ar', '44100', '-ac', '1', seg]);
      } else {
        await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'lavfi',
          '-i', 'anullsrc=r=44100:cl=mono', '-t', L.toFixed(3), seg]);
      }
      segmentos.push(`file '${seg.replace(/\\/g, '/')}'`);
    }
    const lista = path.join(tmp, 'segmentos.txt');
    await fs.writeFile(lista, segmentos.join('\n') + '\n');
    const pistaVoz = path.join(tmp, 'narracion.wav');
    await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
      '-i', lista, '-c:a', 'pcm_s16le', pistaVoz]);

    await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-i', videoMudo, '-i', pistaVoz,
      '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100',
      '-c:a', 'aac', '-b:a', '160k', '-shortest', mp4]);
  } else {
    log('4/5 sin narración: vídeo mudo');
    await fs.copyFile(videoMudo, mp4);
  }

  /* 5. GIF, subtítulos y comprobación */
  log('5/5 GIF y subtítulos');
  const g = guion.gif ?? {};
  const desde = a[Math.min(g.desde ?? 0, escenas.length - 1)] + (g.offset_desde ?? 0);
  const hasta = a[Math.min(g.hasta ?? escenas.length, escenas.length)];
  const gif = path.join(SALIDA, 'demo-asistente-voz.gif');
  await mustRun('ffmpeg', ['-y', '-loglevel', 'error', '-ss', desde.toFixed(3),
    '-t', (hasta - desde).toFixed(3), '-i', mp4, '-an',
    '-vf', `fps=${g.fps ?? 10},scale=${g.ancho ?? 800}:-1:flags=lanczos,` +
      'split[a][b];[a]palettegen=max_colors=192:stats_mode=diff[p];' +
      '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle',
    '-loop', '0', gif]);

  const srt = escenas.map((e, i) =>
    `${i + 1}\n${srtTime(a[i])} --> ${srtTime(a[i + 1])}\n${e.subtitulo}\n`).join('\n');
  await fs.writeFile(path.join(SALIDA, 'demo-asistente-voz.es.srt'), srt, 'utf8');

  const kb = async p => ((await fs.stat(p)).size / 1024).toFixed(0) + ' kB';
  for (const f of [mp4, gif, path.join(SALIDA, 'demo-asistente-voz.png'),
    path.join(SALIDA, 'demo-asistente-voz.es.srt')]) {
    if (await existe(f)) log(`  ${path.basename(f)}  ${await kb(f)}`);
  }
  log(`  vídeo: ${(await duracion(mp4)).toFixed(2)} s`);
  log(`  voz: ${motor === 'mudo' ? 'sin voz' : motor + ' · «' + voz + '»'}`);

  await fs.rm(tmp, { recursive: true, force: true }).catch(() => {});
  log('listo');
}

main().catch(e => { console.error(e); process.exit(1); });
