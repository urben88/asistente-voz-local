# Asistente de voz local

Hablas y tu PC escribe, resume o te lee el texto en voz alta. **100% local**: nada sale de tu ordenador. Windows y Linux.

**[Instalar](#instalar)** · **[Atajos](#atajos)** · **[Requisitos](#requisitos)** · **[Detalle técnico](docs/detalle.md)**

## Míralo en 40 segundos

https://github.com/user-attachments/assets/08749ab9-f51f-4cf2-a3bb-0c554fefeab9

Recreación del uso real, con sonido y subtítulos. ¿No se reproduce? [Abre el MP4](docs/media/demo-asistente-voz.mp4) o mira el [GIF](docs/media/demo-asistente-voz.gif).

## Instalar

1. **Descarga**: botón verde **Code → Download ZIP** y descomprime.
2. **Ejecuta el instalador**:
   - **Windows**: doble clic en **`Instalar.cmd`** y acepta el aviso de administrador.
   - **Linux**: en una terminal dentro de la carpeta, `./Instalar.sh`.
3. **Elige modelos**: pulsa **Intro** para el recomendado (ligero, ~4 GB). La opción 2 es más pesada y precisa (~11 GB).

Listo: el panel y el lector arrancan solos con tu sesión. Si algo falla, vuelve a ejecutarlo; no repite lo ya hecho.

## Atajos

| Atajo | Qué hace |
|---|---|
| `Ctrl + Alt + Espacio` | **Dictar** donde está el cursor. |
| `Ctrl + Shift + Espacio` | **Pedir a la IA**: «resume esto», «escribe un correo…». |
| `Ctrl + Alt + R` | **Leer en voz alta** lo seleccionado. Otra vez, para. |
| `Ctrl + Alt + P` | **Panel**: encender o apagar cada parte y liberar la GPU. |

`Esc` cancela. El resultado queda también en el portapapeles.

## Requisitos

- Windows 10/11 o Linux (Mint, Ubuntu, Debian) de 64 bits.
- GPU NVIDIA recomendada.
- ~20 GB libres e internet durante la instalación.

¿Algo más? Opciones, configuración y solución de problemas en el **[detalle técnico](docs/detalle.md)**.
