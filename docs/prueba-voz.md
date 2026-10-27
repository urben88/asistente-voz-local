---
titulo: Prueba de voz
uso: selecciona una sección (o todo) y pulsa Ctrl+Alt+R
---

# Prueba de voz

Cada sección empieza con su número. Si algo suena mal, dime el número y lo que oyes.

## 1. Texto normal y pausas

Esto es una frase sencilla. Esta otra tiene una coma, una pausa media; y termina con punto.
¿Se nota la pregunta? ¡Y la exclamación! Aquí hay puntos suspensivos… y sigue la frase.
He revisado todo —de arriba abajo— y quedan dos cosas: la voz y el ritmo.

## 2. Formato Markdown

Texto con **negrita**, con *cursiva*, con ~~tachado~~ y con `código corto`.
Un enlace a la [documentación oficial](https://ejemplo.com/docs) y una URL suelta https://ejemplo.com/pagina.
![imagen de ejemplo](https://ejemplo.com/foto.png)
Una nota al pie[^1] y un ancla {#seccion}.

[^1]: Esta nota no debería leerse como texto raro.

## 3. Listas

- Primer elemento de la lista.
- Segundo elemento, con **negrita**.
  - Un elemento anidado.
1. Paso uno.
2. Paso dos.
3. Paso tres.

## 4. Casillas y citas

- [x] Tarea terminada.
- [ ] Tarea pendiente.

> Esto es una cita de dos líneas.
> Esta es la segunda línea de la cita.

## 5. Tablas

| Motor | Calidad | Velocidad |
| --- | --- | --- |
| Piper | media | rápida |
| Kokoro | buena | rápida |
| XTTS | muy buena | lenta |

| # | Tarea | Estado |
| --- | --- | --- |
| 1 | Instalar | hecho |
| 2 | Probar | pendiente |

## 6. Código (no debería leerse)

Antes del bloque de código.

```python
def hola():
    print("esto no se lee")
```

Después del bloque de código: no debería haberse oído nada entre medias.

## 7. Iconos y emojis (no deberían oírse)

✅ Hecho ⚠️ Aviso 🚀 Lanzado 🔗 Enlace ➜ Siguiente • Viñeta ★ Estrella
Flechas entre palabras: entrada → salida, antes -> después, causa => efecto.

## 8. Comillas

Dijo «hola» y después “adiós”. También con "comillas rectas" y con 'simples'.

## 9. Palabras inglesas sueltas

Haz commit y push del README en GitHub, y abre un pull request.
Revisa el prompt, el token y el script antes del deploy en el server.
El frontend y el backend usan el mismo framework; el bug ya tiene fix.
Descarga el software, actualiza el driver y abre el browser.
Claude, OpenAI, DeepSeek, Ollama, Python, Windows, Linux y Docker.

## 10. Frases enteras en inglés

You should run the tests first.
El agente dijo: please make sure the file is saved, y luego cerró la sesión.
This is a short test of the reader.

## 11. Siglas

La API, la GPU y la CPU. Un archivo JSON, otro YAML y un PDF.
Usa 8 GB de VRAM, un SSD y conexión por SSH o VPN.
La IA, el LLM, el MCP y la CLI. Un PR en la BBDD.
El siglo XX y el siglo XXI. La OTAN y la NASA.

## 12. Números

Hay 3 tareas, 25 archivos y 1.000 usuarios. En total, 1.234.567 líneas.
Tarda 12,5 segundos; el error es de 0,05. El valor es 3.14.
Subió un 25 % y bajó un -5 %. Es 2x más rápido.
El 1.º, la 2ª y el 3.º de la lista.

## 13. Versiones

Instala Python 3.12 y la v2.1.3. Ahora va por la v5.
El modelo kokoro-v1.0 y la versión 0.6.1 de la librería.

## 14. Unidades y monedas

Pesa 80 kg y mide 180 cm. Recorre 5 km en 20 min.
Ocupa 1 GB, 512 MB y 2 TB. Responde en 150 ms y tarda 3 s.
Hace 20 °C. Cuesta 5 €, o $10. La pantalla es de 1920x1080.
El piso tiene 80 m² y la CPU va a 3,5 GHz.

## 15. Horas, fechas y rangos

Quedamos a las 10:16 o a las 9:00.
Fechas: 2026-10-27 y 27/10/2026.
Tarda 3-5 minutos; entre 2 y 4 horas; duerme 6 a 8 horas.

## 16. Teclas y archivos

Pulsa Ctrl+Alt+R para leer y Ctrl+Shift+Espacio para resumir.
Abre lector.py, notas.md y config.json. Lee los .md del repositorio.
El script install.ps1 y el archivo es_ES-davefx-medium.onnx.
Programa en C++ y en C#. Calcula 1+1.

## 17. Abreviaturas

Vive en EE. UU. desde 2020, p. ej. en Nueva York, etc.
El piso n.º 3 mide aprox. 80 metros. El Dr. García y la Sra. López.
Python vs. JavaScript.

## 18. Salida típica de un agente

⏺ Bash(git status)
  ⎿  On branch main
│ ├── lector/
│ └── panel/
$ python lector/pruebas_filtro.py
PS C:\Users\tirol> npm install

He revisado el repositorio y he encontrado tres cosas:

1. El archivo `lector.py` no cierra bien la cola.
2. La función `trocear()` corta frases largas por comas.
3. Falta el test de `pronunciar.py`.

**Siguiente paso:** ejecuta las pruebas con `python lector/pruebas_filtro.py` y dime si pasan. ✅

## 19. Texto copiado de una web

Inicio | Noticias | Contacto
Publicado el 27/10/2026 · 5 min de lectura
La nueva versión mejora el rendimiento un 30 % y reduce el consumo a 4 GB de RAM.
Leer más »
© 2026 Ejemplo S.L. Todos los derechos reservados.
&nbsp;Texto con entidades &amp; símbolos &lt;html&gt;.

## 20. Párrafo largo

Este párrafo es largo a propósito, para comprobar que la voz no se atasca ni corta frases a la mitad cuando el texto sigue y sigue, con comas, con datos como 12,5 segundos o 8 GB de memoria, con alguna palabra en inglés como deploy o commit, y con una cita en inglés que dice you should always check the logs before restarting, para terminar con una idea sencilla: si esto se escucha bien de principio a fin, la lectura está lista.
