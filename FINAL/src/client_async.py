"""
Cliente asíncrono usando asyncio para procesamiento de video.

Reemplaza el patrón while True con async/await y StreamReader/StreamWriter.
"""

import asyncio
import argparse
import sys
import os
import time
import struct
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Agregar src al path
sys.path.insert(0, os.path.dirname(__file__))


# ============================================================================
# PROTOCOL HELPERS ASYNC
# ============================================================================

async def send_message_async(writer: asyncio.StreamWriter, msg: Dict[str, Any]) -> None:
    """
    Envía un mensaje JSON con prefijo de longitud (async).

    Args:
        writer: asyncio StreamWriter
        msg: Diccionario a enviar
    """
    payload = json.dumps(msg).encode('utf-8')
    length = struct.pack('!I', len(payload))

    writer.write(length + payload)
    await writer.drain()


async def recv_message_async(reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
    """
    Recibe un mensaje JSON con prefijo de longitud (async).

    Args:
        reader: asyncio StreamReader

    Returns:
        Diccionario con el mensaje o None si conexión cerrada
    """
    try:
        # Leer longitud (4 bytes big-endian)
        length_bytes = await reader.readexactly(4)
        if not length_bytes:
            return None

        length = struct.unpack('!I', length_bytes)[0]

        # Leer payload
        payload = await reader.readexactly(length)
        return json.loads(payload.decode('utf-8'))

    except asyncio.IncompleteReadError:
        return None
    except Exception as e:
        print(f"Error recibiendo mensaje: {e}")
        return None


async def recv_bytes_async(reader: asyncio.StreamReader, size: int) -> bytes:
    """
    Recibe exactamente size bytes (async).

    Args:
        reader: asyncio StreamReader
        size: Cantidad de bytes a recibir

    Returns:
        Bytes recibidos
    """
    return await reader.readexactly(size)


async def send_file_async(writer: asyncio.StreamWriter, file_path: str, chunk_size: int = 65536) -> None:
    """
    Envía un archivo en chunks (async).

    Args:
        writer: asyncio StreamWriter
        file_path: Ruta al archivo
        chunk_size: Tamaño de chunks
    """
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()


# ============================================================================
# CLIENTE ASYNC
# ============================================================================

class VideoClientAsync:
    """Cliente asíncrono para enviar videos al servidor."""

    def __init__(self, host: str, port: int, use_ipv6: bool = False, use_ipv4: bool = False):
        """
        Inicializa el cliente asíncrono.

        Args:
            host: Dirección del servidor
            port: Puerto del servidor
            use_ipv6: Forzar IPv6
            use_ipv4: Forzar IPv4
        """
        self.host = host
        self.port = port
        self.use_ipv6 = use_ipv6
        self.use_ipv4 = use_ipv4
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """Conecta al servidor de forma asíncrona."""
        # Determinar familia de dirección
        import socket
        if self.use_ipv6:
            family = socket.AF_INET6
            family_name = 'IPv6'
        elif self.use_ipv4:
            family = socket.AF_INET
            family_name = 'IPv4'
        else:
            # Auto-detectar usando getaddrinfo
            try:
                addrinfo = socket.getaddrinfo(
                    self.host,
                    self.port,
                    socket.AF_UNSPEC,
                    socket.SOCK_STREAM
                )
                if addrinfo:
                    family = addrinfo[0][0]
                    family_name = 'IPv6' if family == socket.AF_INET6 else 'IPv4'
                else:
                    family = socket.AF_INET
                    family_name = 'IPv4'
            except:
                family = socket.AF_INET
                family_name = 'IPv4'

        print(f"Conectando a {self.host}:{self.port} ({family_name})...")

        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host,
                self.port,
                family=family
            )
            print("Conectado exitosamente")

        except Exception as e:
            print(f"Error conectando: {e}")
            raise

    async def send_video(
        self,
        video_path: str,
        output_path: str,
        processing: str,
        codec: str = 'mp4v',
        filters: list = None
    ) -> Dict[str, Any]:
        """
        Envía un video al servidor para procesamiento (async).

        Args:
            video_path: Ruta al video de entrada
            output_path: Ruta donde guardar el video procesado
            processing: Tipo de procesamiento
            codec: Codec de salida
            filters: Filtros adicionales

        Returns:
            Diccionario con resultados y métricas
        """
        if not self.reader or not self.writer:
            raise RuntimeError("No conectado. Llamar connect() primero")

        # Verificar que el video existe
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video no encontrado: {video_path}")

        video_size = Path(video_path).stat().st_size
        video_name = Path(video_path).name

        print(f"Enviando video: {video_name} ({video_size / 1024 / 1024:.2f} MB)")

        # Enviar handshake
        handshake = {
            "type": "handshake",
            "mode": "stream",
            "codec": codec,
            "processing": processing,
            "video_info": {
                "filename": video_name,
                "size_bytes": video_size
            },
            "filters": filters or []
        }
        await send_message_async(self.writer, handshake)

        # Recibir ACK
        ack = await recv_message_async(self.reader)
        if not ack or not ack.get("accepted"):
            raise RuntimeError("Servidor rechazó la conexión")

        session_id = ack.get("session_id", "unknown")
        print(f"Sesión iniciada: {session_id}")

        preview_url = ack.get("preview_url")
        if preview_url:
            print(f"Preview disponible en: {preview_url}")

        # Enviar video
        print("Enviando video...")
        await send_file_async(self.writer, video_path)

        # Indicar que no se enviarán más datos
        self.writer.write_eof()
        await self.writer.drain()
        print("Video enviado, esperando procesamiento...")

        start_time = time.time()

        # Procesar mensajes de forma asíncrona
        result = await self._process_messages_async(output_path, start_time)

        return result

    async def _process_messages_async(
        self,
        output_path: str,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Procesa mensajes del servidor de forma asíncrona.

        ANTES (while True):
            while True:
                msg = messages.recv_message(self.sock)
                if not msg:
                    break
                # process msg

        DESPUÉS (asyncio):
            async for msg in self._message_stream():
                # process msg

        Args:
            output_path: Ruta donde guardar video
            start_time: Timestamp de inicio

        Returns:
            Resultado del procesamiento
        """
        async for msg in self._message_stream():
            msg_type = msg.get("type")

            if msg_type == "progress":
                await self._show_progress_async(msg)

            elif msg_type == "result":
                return await self._process_result_async(msg, output_path, start_time)

            elif msg_type == "error":
                print()
                print(f"Error del servidor: {msg.get('message')}")
                return msg

        # Si llegamos aquí, la conexión se cerró sin resultado
        return {"ok": False, "error": "Conexión cerrada inesperadamente"}

    async def _message_stream(self):
        """
        Generador asíncrono que yields mensajes del servidor.

        Esto reemplaza el while True con una estructura más Pythonic.
        """
        while True:
            msg = await recv_message_async(self.reader)
            if not msg:
                break
            yield msg

    async def _show_progress_async(self, msg: Dict[str, Any]) -> None:
        """Muestra barra de progreso (async)."""
        frames_done = msg.get("frames_processed", 0)
        frames_total = msg.get("frames_total", 0)
        fps = msg.get("fps", 0)
        eta = msg.get("eta_seconds", 0)

        if frames_total > 0:
            percent = (frames_done / frames_total) * 100
            bar_len = 40
            filled = int(bar_len * frames_done / frames_total)
            bar = '=' * filled + '-' * (bar_len - filled)
            print(
                f"\rProgreso: [{bar}] {percent:.1f}% | "
                f"{frames_done}/{frames_total} frames | "
                f"{fps:.1f} FPS | ETA: {eta:.1f}s",
                end='',
                flush=True
            )

    async def _process_result_async(
        self,
        msg: Dict[str, Any],
        output_path: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Procesa mensaje de resultado y guarda video (async)."""
        print()  # Nueva línea después de la barra de progreso

        ok = msg.get("ok", False)
        if not ok:
            print("Error procesando video")
            return msg

        size = msg.get("size_bytes", 0)
        metrics = msg.get("metrics", {})

        print(f"Recibiendo video procesado ({size / 1024 / 1024:.2f} MB)...")
        video_data = await recv_bytes_async(self.reader, size)

        # Guardar video
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(video_data)

        elapsed = time.time() - start_time
        print(f"Video guardado: {output_path}")
        print(f"Tiempo total: {elapsed:.2f}s")
        print("\nMétricas:")
        print(f"  Frames procesados: {metrics.get('frames_processed', 0)}")
        print(f"  FPS procesamiento: {metrics.get('fps_processing', 0):.2f}")
        print(f"  Latencia p50: {metrics.get('latency_p50_ms', 0):.2f} ms")
        print(f"  Latencia p95: {metrics.get('latency_p95_ms', 0):.2f} ms")
        print(f"  Latencia p99: {metrics.get('latency_p99_ms', 0):.2f} ms")
        print(f"  Reintentos: {metrics.get('retries', 0)}")
        print(f"  Workers: {metrics.get('worker_count', 0)}")

        return msg

    async def close(self) -> None:
        """Cierra la conexión (async)."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# ============================================================================
# MAIN ASYNC
# ============================================================================

async def main_async():
    """Punto de entrada asíncrono del cliente."""
    parser = argparse.ArgumentParser(
        description='Cliente asíncrono de procesamiento de video',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Blur
  %(prog)s --host ::1 --port 9090 --video input.mp4 --processing blur --out output.mp4

  # Detección de rostros
  %(prog)s --host 127.0.0.1 --video input.mp4 --processing faces --out output.mp4

  # Detección de bordes
  %(prog)s --host localhost --video input.mp4 --processing edges --out output.mp4
        """
    )

    parser.add_argument('--host', default='::1', help='Dirección del servidor (default: ::1)')
    parser.add_argument('--port', type=int, default=9090, help='Puerto del servidor (default: 9090)')
    parser.add_argument('--ipv6', action='store_true', help='Forzar IPv6')
    parser.add_argument('--ipv4', action='store_true', help='Forzar IPv4')
    parser.add_argument('--video', required=True, help='Ruta al video de entrada')
    parser.add_argument('--processing',
                       choices=['blur', 'faces', 'edges', 'motion', 'custom'],
                       default='blur',
                       help='Tipo de procesamiento (default: blur)')
    parser.add_argument('--out', default='output.mp4', help='Ruta del video de salida (default: output.mp4)')
    parser.add_argument('--codec', default='mp4v', help='Codec de salida (default: mp4v)')

    args = parser.parse_args()

    # Validaciones
    if args.ipv6 and args.ipv4:
        print("Error: --ipv6 y --ipv4 son mutuamente exclusivos")
        sys.exit(1)

    if not Path(args.video).exists():
        print(f"Error: Video no encontrado: {args.video}")
        sys.exit(1)

    # Conectar y enviar video de forma asíncrona
    try:
        async with VideoClientAsync(args.host, args.port, args.ipv6, args.ipv4) as client:
            result = await client.send_video(
                args.video,
                args.out,
                args.processing,
                args.codec
            )

            if result.get("ok"):
                print("\nProcesamiento completado exitosamente")
                sys.exit(0)
            else:
                print("\nProcesamiento falló")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nCancelado por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point que ejecuta la versión async."""
    asyncio.run(main_async())


if __name__ == '__main__':
    main()


# ============================================================================
# COMPARACIÓN: SYNC vs ASYNC
# ============================================================================

"""
COMPARACIÓN LADO A LADO:

┌─────────────────────────────────────────────────────────────────────────┐
│ SYNC (client.py) - Patrón while True                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ while True:                                                             │
│     msg = messages.recv_message(self.sock)  # BLOCKING                 │
│     if not msg:                                                         │
│         break                                                           │
│                                                                         │
│     if msg['type'] == 'progress':                                      │
│         show_progress(msg)                                              │
│     elif msg['type'] == 'result':                                      │
│         return process_result(msg)                                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ ASYNC (client_async.py) - asyncio con async for                       │
├─────────────────────────────────────────────────────────────────────────┤
│ async for msg in self._message_stream():  # NON-BLOCKING              │
│     if msg['type'] == 'progress':                                      │
│         await self._show_progress_async(msg)                            │
│     elif msg['type'] == 'result':                                      │
│         return await self._process_result_async(msg)                    │
│                                                                         │
│ # _message_stream() es un async generator:                             │
│ async def _message_stream(self):                                        │
│     while True:                                                         │
│         msg = await recv_message_async(self.reader)                     │
│         if not msg:                                                     │
│             break                                                       │
│         yield msg                                                       │
└─────────────────────────────────────────────────────────────────────────┘

VENTAJAS DE ASYNCIO:

✅ No bloquea el event loop
   - Puede manejar múltiples conexiones concurrentemente
   - El programa puede hacer otras cosas mientras espera I/O

✅ Código más escalable
   - 1000 clientes async = ~1000 KB de memoria
   - 1000 threads sync = ~1000 MB de memoria

✅ Mejor para aplicaciones interactivas
   - UI no se congela mientras espera datos
   - Puede actualizar progreso en tiempo real

✅ Más eficiente con I/O
   - No desperdicia CPU esperando
   - Cambio de contexto más barato que threads

⚠️ DESVENTAJAS:

- Más complejo de entender (async/await)
- Requiere que todo el stack sea async
- Debugging puede ser más difícil

CUÁNDO USAR QUÉ:

- Cliente CLI simple (1 video):    client.py (sync)
- Cliente GUI (múltiples videos):  client_async.py (async)
- Servidor (múltiples clientes):   SIEMPRE async (como server.py)
- Scripts batch:                   sync
- Aplicación web:                  async
"""
