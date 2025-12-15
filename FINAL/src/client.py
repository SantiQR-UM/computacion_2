"""
Cliente CLI para enviar videos al servidor de procesamiento.

Soporta IPv4 e IPv6, múltiples tipos de procesamiento y muestra progreso en tiempo real.
"""

import socket
import argparse
import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Agregar src al path
sys.path.insert(0, os.path.dirname(__file__))

from protocol import messages


class VideoClient:
    """Cliente para enviar videos al servidor de procesamiento."""

    def __init__(self, host: str, port: int, use_ipv6: bool = False, use_ipv4: bool = False):
        """
        Inicializa el cliente.

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
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Conecta al servidor."""
        # Determinar familia de dirección
        if self.use_ipv6:
            family = socket.AF_INET6
        elif self.use_ipv4:
            family = socket.AF_INET
        else:
            # Auto-detectar
            try:
                addrinfo = socket.getaddrinfo(
                    self.host,
                    self.port,
                    socket.AF_UNSPEC,
                    socket.SOCK_STREAM
                )
                if addrinfo:
                    family = addrinfo[0][0]
                else:
                    family = socket.AF_INET
            except:
                family = socket.AF_INET

        # Crear socket
        self.sock = socket.socket(family, socket.SOCK_STREAM)

        # Conectar
        print(f"Conectando a {self.host}:{self.port} ({'IPv6' if family == socket.AF_INET6 else 'IPv4'})...")
        try:
            self.sock.connect((self.host, self.port))
            print("Conectado exitosamente")
        except Exception as e:
            print(f"Error conectando: {e}")
            raise

    def send_video(
        self,
        video_path: str,
        output_path: str,
        processing: str,
        codec: str = 'mp4v',
        filters: list = None
    ) -> Dict[str, Any]:
        """
        Envía un video al servidor para procesamiento.

        Args:
            video_path: Ruta al video de entrada
            output_path: Ruta donde guardar el video procesado
            processing: Tipo de procesamiento
            codec: Codec de salida
            filters: Filtros adicionales

        Returns:
            Diccionario con resultados y métricas
        """
        if not self.sock:
            raise RuntimeError("No conectado. Llamar connect() primero")

        # Verificar que el video existe
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video no encontrado: {video_path}")

        video_size = Path(video_path).stat().st_size
        video_name = Path(video_path).name

        print(f"Enviando video: {video_name} ({video_size / 1024 / 1024:.2f} MB)")

        # Enviar handshake
        handshake = messages.make_handshake(
            mode="stream",
            codec=codec,
            processing=processing,
            video_info={
                "filename": video_name,
                "size_bytes": video_size
            },
            filters=filters or []
        )
        messages.send_message(self.sock, handshake)

        # Recibir ACK
        ack = messages.recv_message(self.sock)
        if not ack or not ack.get("accepted"):
            raise RuntimeError("Servidor rechazó la conexión")

        session_id = ack.get("session_id", "unknown")
        print(f"Sesión iniciada: {session_id}")

        preview_url = ack.get("preview_url")
        if preview_url:
            print(f"Preview disponible en: {preview_url}")

        # Enviar video
        print("Enviando video...")
        with open(video_path, 'rb') as f:
            self.sock.sendall(f.read())
        
        # Indicar que no se enviarán más datos
        self.sock.shutdown(socket.SHUT_WR)
        print("Video enviado, esperando procesamiento...")

        # Recibir actualizaciones de progreso
        start_time = time.time()
        last_progress = None

        while True:
            msg = messages.recv_message(self.sock)
            if not msg:
                break

            msg_type = msg.get("type")

            if msg_type == "progress":
                # Mostrar progreso
                frames_done = msg.get("frames_processed", 0)
                frames_total = msg.get("frames_total", 0)
                fps = msg.get("fps", 0)
                eta = msg.get("eta_seconds", 0)

                if frames_total > 0:
                    percent = (frames_done / frames_total) * 100
                    bar_len = 40
                    filled = int(bar_len * frames_done / frames_total)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    print(f"\rProgreso: [{bar}] {percent:.1f}% | {frames_done}/{frames_total} frames | {fps:.1f} FPS | ETA: {eta:.1f}s", end='', flush=True)

                last_progress = msg

            elif msg_type == "result":
                print()  # Nueva línea después de la barra de progreso
                # Recibir video procesado
                ok = msg.get("ok", False)
                if not ok:
                    print("Error procesando video")
                    return msg

                size = msg.get("size_bytes", 0)
                metrics = msg.get("metrics", {})

                print(f"Recibiendo video procesado ({size / 1024 / 1024:.2f} MB)...")
                video_data = messages.recv_bytes(self.sock, size)

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

            elif msg_type == "error":
                print()
                print(f"Error del servidor: {msg.get('message')}")
                return msg

        return {"ok": False, "error": "Conexión cerrada inesperadamente"}

    def close(self) -> None:
        """Cierra la conexión."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """Punto de entrada del cliente."""
    parser = argparse.ArgumentParser(
        description='Cliente de procesamiento de video',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Blur con IPv6
  %(prog)s --host ::1 --port 9090 --ipv6 --video input.mp4 --processing blur --out output.mp4

  # Detección de rostros con IPv4
  %(prog)s --host 127.0.0.1 --ipv4 --video input.mp4 --processing faces --out output.mp4

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
    parser.add_argument('--preview', action='store_true', help='Mostrar URL de preview')

    args = parser.parse_args()

    # Validaciones
    if args.ipv6 and args.ipv4:
        print("Error: --ipv6 y --ipv4 son mutuamente exclusivos")
        sys.exit(1)

    if not Path(args.video).exists():
        print(f"Error: Video no encontrado: {args.video}")
        sys.exit(1)

    # Conectar y enviar video
    try:
        with VideoClient(args.host, args.port, args.ipv6, args.ipv4) as client:
            result = client.send_video(
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


if __name__ == '__main__':
    main()
