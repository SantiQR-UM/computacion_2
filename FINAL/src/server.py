"""
Servidor asíncrono de procesamiento de video.

Recibe videos de clientes vía TCP dual-stack, extrae frames con OpenCV,
los distribuye a workers de Celery, y reensambla el video procesado.
"""

import asyncio
import socket
import argparse
import uuid
import cv2
import numpy as np
import tempfile
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import time
import redis

# Agregar src al path
sys.path.insert(0, os.path.dirname(__file__))

from protocol import messages
from storage.writer import VideoWriter, VideoFrameBuffer
from metrics.stats import MetricsCollector

# Importar la aplicación Celery y la tarea
from worker import app as celery_app, process_frame

# Asegurar que Celery esté configurado
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = None  # No usar result backend
celery_app.conf.update(
    task_serializer='pickle',
    accept_content=['json', 'pickle'],
    broker_transport_options={
        'socket_timeout': 30.0,
        'socket_keepalive': True,
    },
)

# Cliente Redis para metadata del preview server
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=5.0, socket_connect_timeout=5.0)
    redis_client.ping()
    print("Conexión a Redis establecida correctamente")
except Exception as e:
    print(f"Advertencia: No se pudo conectar a Redis: {e}")
    redis_client = None


class VideoProcessor:
    """Orquesta el procesamiento de video: despacha tareas y procesa resultados."""

    def __init__(self, session_id: str, processing_type: str, metadata: Dict[str, Any]):
        self.session_id = session_id
        self.processing_type = processing_type
        self.metadata = metadata
        self.metrics = MetricsCollector()

    def _extract_and_dispatch_frames_sync(self, video_path: str) -> Tuple[list, dict, dict]:
        """
        Extrae frames de forma SÍNCRONA y los despacha a Celery.
        Esta función se ejecutará en un executor para no bloquear el event loop.

        Returns:
            Tuple: (lista de tareas, dict de frames originales, dict de propiedades del video)
        """
        # Crear directorio de frames único para esta sesión (para soportar múltiples clientes concurrentes)
        frames_dir = f'/app/data/frames/{self.session_id}'
        if os.path.exists(frames_dir):
            import shutil
            shutil.rmtree(frames_dir)
        os.makedirs(frames_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"No se pudo abrir el video: {video_path}")

        video_props = {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
        self.metrics.set_total_frames(video_props["total_frames"])
        print(f"[{self.session_id}] Video: {video_props['total_frames']} frames, {video_props['fps']} FPS")

        tasks = []
        original_frames = {}
        frame_number = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            original_frames[frame_number] = frame
            success, encoded = cv2.imencode('.png', frame)
            if not success:
                print(f"[{self.session_id}] Error codificando frame {frame_number}")
                continue

            # Pasar session_id en metadata para que el worker sepa dónde guardar
            metadata_with_session = dict(self.metadata)
            metadata_with_session['session_id'] = self.session_id

            task = process_frame.apply_async(
                args=(encoded.tobytes(), frame_number, self.processing_type, metadata_with_session),
                queue='frames'
            )
            tasks.append((frame_number, task))
            frame_number += 1

        cap.release()
        print(f"[{self.session_id}] Extraídos y despachados {frame_number} frames.")
        return tasks, original_frames, video_props

    async def dispatch_tasks(self, video_path: str) -> Tuple[list, dict, dict]:
        """
        Extrae frames, los despacha a Celery y retorna las tareas.
        Ejecuta la extracción en un executor para no bloquear el event loop.

        Returns:
            Tuple: (lista de tareas, dict de frames originales, dict de propiedades del video)
        """
        loop = asyncio.get_event_loop()
        # Ejecutar la extracción bloqueante en un thread pool
        return await loop.run_in_executor(
            None,  # Usa el default ThreadPoolExecutor
            self._extract_and_dispatch_frames_sync,
            video_path
        )

    async def get_celery_results(self, tasks: list, executor=None) -> list:
        """Espera a que todos los frames se procesen chequeando el sistema de archivos."""
        frames_dir = f'/app/data/frames/{self.session_id}'

        async def wait_for_frame(frame_number):
            """Espera a que un frame específico aparezca en disco."""
            frame_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.png')
            stats_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.json')
            max_wait = 300  # 5 minutos timeout
            check_interval = 0.1  # Chequear cada 100ms
            waited = 0

            while waited < max_wait:
                if os.path.exists(frame_path) and os.path.exists(stats_path):
                    # Leer stats desde el archivo JSON
                    import json
                    try:
                        with open(stats_path, 'r') as f:
                            stats = json.load(f)
                    except Exception:
                        # Si falla, usar stats por defecto
                        stats = {
                            'processing_time_ms': 0,
                            'memory_mb': 0,
                            'memory_delta_mb': 0,
                            'filter_applied': 'unknown',
                            'worker_id': 'unknown',
                            'hostname': 'unknown'
                        }

                    return {
                        'frame_path': frame_path,
                        'frame_number': frame_number,
                        'stats': stats
                    }
                await asyncio.sleep(check_interval)
                waited += check_interval

            # Timeout - retornar error
            raise TimeoutError(f"Frame {frame_number} no apareció en {max_wait}s")

        print("Esperando que todos los frames se procesen en disco...")
        awaiting_coroutines = [wait_for_frame(frame_num) for frame_num, _ in tasks]
        all_results = await asyncio.gather(*awaiting_coroutines, return_exceptions=True)
        print("Todos los frames procesados.")
        return all_results

    def _process_results_sync(
        self,
        all_results: list,
        tasks: list,
        original_frames: dict,
        video_props: dict,
        output_path: str,
        codec: str = 'mp4v'
    ) -> Dict[str, Any]:
        """
        Procesa los resultados y escribe el video (función síncrona).
        Esta función se ejecutará en un executor para no bloquear el event loop.
        """
        writer = VideoWriter(
            output_path, codec, video_props['fps'],
            (video_props['width'], video_props['height'])
        )
        frame_buffer = VideoFrameBuffer(writer)

        print(f"Procesando {len(all_results)} resultados...")
        for i, result in enumerate(all_results):
            frame_num = tasks[i][0]
            processed_frame = None
            stats = {}
            is_fallback = False

            if isinstance(result, Exception):
                print(f"Error de timeout/worker en frame {frame_num}: {type(result).__name__}: {result}")
                print(f"  Usando fallback.")
                processed_frame = original_frames.get(frame_num)
                is_fallback = True
            else:
                stats = result.get("stats", {})
                if "error" in stats:
                    print(f"Error de procesamiento en frame {frame_num}, usando fallback.")
                    processed_frame = original_frames.get(frame_num)
                    is_fallback = True
                else:
                    # Leer frame desde el volumen compartido
                    frame_path = result.get("frame_path")
                    if frame_path and os.path.exists(frame_path):
                        processed_frame = cv2.imread(frame_path)
                        if processed_frame is None:
                            print(f"Error leyendo frame {frame_num} desde {frame_path}, usando fallback.")
                            processed_frame = original_frames.get(frame_num)
                            is_fallback = True
                    else:
                        print(f"Frame {frame_num} no encontrado en {frame_path}, usando fallback.")
                        processed_frame = original_frames.get(frame_num)
                        is_fallback = True

            if processed_frame is None:
                print(f"Fallback fallido para frame {frame_num}, usando negro.")
                processed_frame = np.zeros((video_props['height'], video_props['width'], 3), dtype=np.uint8)
                is_fallback = True

            frame_buffer.add_frame(frame_num, processed_frame)

            self.metrics.record_frame(
                frame_num,
                stats.get("processing_time_ms", 0),
                stats.get("hostname"),  # Usar hostname en lugar de worker_id para contar workers únicos
                "fallback" if is_fallback else stats.get("filter_applied"),
                stats.get("memory_mb", 0),
                failed=is_fallback
            )

            # Logging de progreso cada 30 frames
            if (frame_num + 1) % 30 == 0:
                print(f"[{self.session_id}] Progreso: {frame_num + 1}/{video_props['total_frames']} frames procesados")

        print(f"[{self.session_id}] Finalizando buffer y escribiendo video...")
        frame_buffer.flush_remaining(video_props['total_frames'])
        print(f"[{self.session_id}] Cerrando escritor de video...")
        writer.close()
        print(f"[{self.session_id}] Video procesado exitosamente.")

        metrics_summary = self.metrics.get_summary()

        return {
            "ok": True,
            "output_path": output_path,
            "metrics": metrics_summary
        }

    async def process_results(
        self,
        all_results: list,
        tasks: list,
        original_frames: dict,
        video_props: dict,
        output_path: str,
        codec: str = 'mp4v',
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Procesa los resultados, escribe el video y retorna las métricas.
        Ejecuta en un executor para no bloquear el event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._process_results_sync,
            all_results,
            tasks,
            original_frames,
            video_props,
            output_path,
            codec
        )


class ClientHandler:
    """Maneja la conexión con un cliente."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.session_id = str(uuid.uuid4())[:8]

    async def handle(self):
        """Maneja la conexión del cliente."""
        addr = self.writer.get_extra_info('peername')
        sock = self.writer.get_extra_info('socket')
        family = sock.family if sock else None
        family_name = 'IPv6' if family == socket.AF_INET6 else 'IPv4' if family == socket.AF_INET else 'Unknown'
        print(f"[{self.session_id}] Cliente conectado desde {addr} usando {family_name}")

        try:
            # 1. Handshake y recepción de video
            handshake = await self._recv_message()
            if not handshake or handshake.get("type") != "handshake":
                await self._send_error("INVALID_HANDSHAKE", "Se esperaba handshake")
                return

            print(f"[{self.session_id}] Handshake recibido: {handshake.get('processing')}")
            ack = messages.make_handshake_ack(True, self.session_id)
            await self._send_message(ack)

            video_path = await self._receive_video(handshake)
            output_path = f"output_{self.session_id}.mp4"

            # 2. Despachar tareas (ahora async, no bloquea el event loop)
            processor = VideoProcessor(
                self.session_id,
                handshake.get("processing", "blur"),
                handshake
            )
            tasks, original_frames, video_props = await processor.dispatch_tasks(video_path)

            # Guardar metadata en Redis para el preview server
            if redis_client:
                try:
                    video_info = handshake.get('video_info', {})
                    redis_client.set(f'session:{self.session_id}:total_frames', video_props['total_frames'])
                    redis_client.set(f'session:{self.session_id}:fps', f"{video_props['fps']:.2f}")
                    redis_client.set(f'session:{self.session_id}:resolution', f"{video_props['width']}x{video_props['height']}")
                    redis_client.set(f'session:{self.session_id}:status', 'processing')
                    redis_client.set(f'session:{self.session_id}:processing_type', handshake.get('processing', 'none'))
                    redis_client.set(f'session:{self.session_id}:video_name', video_info.get('filename', 'unknown'))
                    redis_client.set(f'session:{self.session_id}:start_time', str(time.time()))
                    # TTL de 1 hora para la metadata
                    for key in ['total_frames', 'fps', 'resolution', 'status', 'processing_type', 'video_name', 'start_time']:
                        redis_client.expire(f'session:{self.session_id}:{key}', 3600)
                    print(f"[{self.session_id}] Metadata guardada en Redis")
                except Exception as e:
                    print(f"[{self.session_id}] Error guardando metadata en Redis: {e}")

            # 3. Obtener resultados esperando que los archivos aparezcan en disco
            all_results = await processor.get_celery_results(tasks, None)

            # 4. Procesar resultados y enviar progreso (ahora seguro)
            async def progress_callback(progress):
                msg = messages.make_progress(
                    progress["frames_processed"],
                    progress["frames_total"],
                    progress["fps"],
                    progress["eta_seconds"]
                )
                await self._send_message(msg)

                # Guardar progreso en Redis para el preview server
                if redis_client:
                    try:
                        redis_client.set(f'session:{self.session_id}:processed_frames', progress["frames_processed"])
                        redis_client.set(f'session:{self.session_id}:current_fps', f"{progress['fps']:.2f}")
                        redis_client.set(f'session:{self.session_id}:eta_seconds', f"{progress['eta_seconds']:.1f}")
                        # TTL de 1 hora
                        for key in ['processed_frames', 'current_fps', 'eta_seconds']:
                            redis_client.expire(f'session:{self.session_id}:{key}', 3600)
                    except Exception as e:
                        pass  # No bloquear por errores de Redis
            
            result = await processor.process_results(
                all_results,
                tasks,
                original_frames,
                video_props,
                output_path,
                handshake.get("codec", "mp4v"),
                progress_callback
            )

            # Actualizar estado a completado en Redis
            if redis_client and result.get("ok"):
                try:
                    redis_client.set(f'session:{self.session_id}:status', 'completed')
                    redis_client.set(f'session:{self.session_id}:end_time', str(time.time()))
                    redis_client.expire(f'session:{self.session_id}:end_time', 3600)
                    print(f"[{self.session_id}] Estado actualizado a 'completed' en Redis")
                except Exception as e:
                    print(f"[{self.session_id}] Error actualizando estado en Redis: {e}")

            # 5. Enviar resultado final
            print(f"[{self.session_id}] Abriendo video procesado: {output_path}")
            sys.stdout.flush()

            # Leer video en executor (operación bloqueante)
            loop = asyncio.get_event_loop()
            video_data = await loop.run_in_executor(
                None,
                self._read_video_file,
                output_path
            )
            print(f"[{self.session_id}] Video leído: {len(video_data)} bytes")

            print(f"[{self.session_id}] Creando mensaje de resultado...")
            result_msg = messages.make_result(
                ok=result["ok"],
                output_path=os.path.basename(output_path),
                size_bytes=len(video_data),
                metrics=result["metrics"]
            )
            print(f"[{self.session_id}] Enviando mensaje de resultado al cliente...")
            await self._send_message(result_msg)
            print(f"[{self.session_id}] Mensaje enviado, ahora enviando datos del video...")

            self.writer.write(video_data)
            await self.writer.drain()
            print(f"[{self.session_id}] Video procesado y enviado ({len(video_data)} bytes)")

        except Exception as e:
            print(f"[{self.session_id}] Error: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error("PROCESSING_ERROR", str(e))

        finally:
            self.writer.close()
            await self.writer.wait_closed()
            print(f"[{self.session_id}] Conexión cerrada")

    async def _receive_video(self, handshake: Dict[str, Any]) -> str:
        """
        Recibe el video del cliente como un stream de bytes.
        Usa un executor para la escritura a disco (no bloquea el event loop).

        Args:
            handshake: Mensaje de handshake con info del video

        Returns:
            Ruta al archivo de video guardado
        """
        video_path = f"input_{self.session_id}.mp4"
        print(f"[{self.session_id}] Recibiendo video por streaming a {video_path}...")

        bytes_received = 0
        chunks = []

        # Primero recibir todos los chunks (esto es async, no bloquea)
        while True:
            chunk = await self.reader.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
            bytes_received += len(chunk)

        # Ahora escribir a disco en un executor (operación bloqueante)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_video_to_disk,
            video_path,
            chunks
        )

        print(f"[{self.session_id}] Video recibido ({bytes_received} bytes).")
        return video_path

    def _write_video_to_disk(self, video_path: str, chunks: list) -> None:
        """Escribe chunks a disco (función síncrona para executor)."""
        with open(video_path, 'wb') as f:
            for chunk in chunks:
                f.write(chunk)

    def _read_video_file(self, video_path: str) -> bytes:
        """Lee video desde disco (función síncrona para executor)."""
        with open(video_path, 'rb') as f:
            return f.read()

    async def _recv_message(self) -> Optional[Dict[str, Any]]:
        """Recibe un mensaje JSON."""
        try:
            # Leer longitud (4 bytes)
            length_bytes = await self.reader.readexactly(4)
            import struct
            length = struct.unpack('!I', length_bytes)[0]

            # Leer payload
            payload = await self.reader.readexactly(length)

            import json
            return json.loads(payload.decode('utf-8'))

        except asyncio.IncompleteReadError:
            return None
        except Exception as e:
            print(f"Error recibiendo mensaje: {e}")
            return None

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Envía un mensaje JSON."""
        import json
        import struct
        payload = json.dumps(message).encode('utf-8')
        length = struct.pack('!I', len(payload))
        self.writer.write(length + payload)
        await self.writer.drain()

    async def _recv_bytes(self, size: int) -> bytes:
        """Recibe exactamente size bytes."""
        return await self.reader.readexactly(size)

    async def _send_error(self, code: str, message: str) -> None:
        """Envía mensaje de error al cliente."""
        error = messages.make_error(code, message, recoverable=False)
        await self._send_message(error)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handler para conexiones de clientes."""
    handler = ClientHandler(reader, writer)
    await handler.handle()


async def start_server(bind_addr: str, port: int):
    """
    Inicia el servidor TCP dual-stack.

    Crea sockets separados para IPv4 e IPv6 usando getaddrinfo().

    Args:
        bind_addr: Dirección de bind (:: para todas las interfaces, 0.0.0.0 para IPv4 only)
        port: Puerto de escucha
    """
    # Usar getaddrinfo para descubrir todas las direcciones disponibles
    try:
        # Si bind_addr es '::', queremos bind a todas las interfaces (IPv4 y IPv6)
        # Pasamos None a getaddrinfo para que devuelva todas las familias
        host_for_getaddrinfo = None if bind_addr == '::' else bind_addr

        print(f"DEBUG: Resolviendo direcciones para host={host_for_getaddrinfo}, port={port}")
        addrinfos = socket.getaddrinfo(
            host_for_getaddrinfo,
            port,
            socket.AF_UNSPEC,  # Aceptar tanto IPv4 como IPv6
            socket.SOCK_STREAM, # TCP
            0,
            socket.AI_PASSIVE  # Para bind
        )
        print(f"DEBUG: getaddrinfo devolvió {len(addrinfos)} direcciones")
    except socket.gaierror as e:
        print(f"Error obteniendo direcciones: {e}")
        raise

    # Agrupar por familia de dirección (IPv4 vs IPv6)
    # Usamos un dict para evitar duplicados por familia
    addr_by_family = {}
    for family, socktype, proto, canonname, sockaddr in addrinfos:
        if family not in addr_by_family:
            addr_by_family[family] = (family, socktype, proto, sockaddr)

    servers = []

    # Crear un socket para cada familia de dirección
    for family, (fam, socktype, proto, sockaddr) in addr_by_family.items():
        try:
            # Crear socket manualmente
            sock = socket.socket(fam, socktype, proto)

            # Configurar socket para reusar dirección
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Para IPv6, asegurarse de que SOLO escuche IPv6 (no dual-stack)
            # Esto permite que el socket IPv4 y el IPv6 coexistan en el mismo puerto
            if fam == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

            # Bind al puerto
            sock.bind(sockaddr)
            sock.listen()
            sock.setblocking(False)

            # Crear servidor asyncio usando el socket pre-configurado
            server = await asyncio.start_server(
                handle_client,
                sock=sock
            )

            servers.append(server)

            family_name = 'IPv6' if fam == socket.AF_INET6 else 'IPv4'
            print(f"Servidor {family_name} escuchando en: {sockaddr}")

        except OSError as e:
            family_name = 'IPv6' if fam == socket.AF_INET6 else 'IPv4'
            print(f"Advertencia: No se pudo crear servidor {family_name}: {e}")
            continue

    if not servers:
        raise RuntimeError("No se pudo crear ningún servidor")

    print(f"Servidor dual-stack listo con {len(servers)} socket(s)")

    # Ejecutar todos los servidores concurrentemente
    try:
        async with asyncio.TaskGroup() as tg:
            for server in servers:
                tg.create_task(server.serve_forever())
    except* Exception as eg:
        # Manejar excepciones del TaskGroup
        print(f"Error en servidor: {eg}")


def main():
    """Punto de entrada del servidor."""
    parser = argparse.ArgumentParser(description='Servidor de procesamiento de video')
    parser.add_argument('--bind', default='::', help='Dirección de bind (default: ::)')
    parser.add_argument('--port', type=int, default=9090, help='Puerto TCP (default: 9090)')
    parser.add_argument('--preview-port', type=int, default=8080, help='Puerto HTTP preview (default: 8080)')
    parser.add_argument('--codec', default='mp4v', help='Codec de salida (default: mp4v)')

    args = parser.parse_args()

    print(f"Iniciando servidor de procesamiento de video...")
    print(f"Bind: {args.bind}:{args.port}")
    print(f"Codec: {args.codec}")

    try:
        asyncio.run(start_server(args.bind, args.port))
    except KeyboardInterrupt:
        print("\nServidor detenido por usuario")


if __name__ == '__main__':
    main()
