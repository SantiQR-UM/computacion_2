"""
Módulo de protocolo para comunicación cliente-servidor.

Implementa envío y recepción de mensajes JSON con prefijo de longitud (4 bytes big-endian).
"""

import json
import struct
import socket
from typing import Dict, Any, Optional


class ProtocolError(Exception):
    """Excepción para errores de protocolo."""
    pass


def send_message(sock: socket.socket, message: Dict[str, Any]) -> None:
    """
    Envía un mensaje JSON con prefijo de longitud.

    Args:
        sock: Socket de red
        message: Diccionario con el mensaje a enviar

    Raises:
        ProtocolError: Si hay error al enviar
    """
    try:
        payload = json.dumps(message).encode('utf-8')
        length = struct.pack('!I', len(payload))  # 4 bytes big-endian
        sock.sendall(length + payload)
    except (socket.error, OSError) as e:
        raise ProtocolError(f"Error enviando mensaje: {e}")


def recv_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """
    Recibe un mensaje JSON con prefijo de longitud.

    Args:
        sock: Socket de red

    Returns:
        Diccionario con el mensaje recibido, o None si la conexión se cerró

    Raises:
        ProtocolError: Si hay error al recibir o el mensaje es inválido
    """
    try:
        # Leer longitud (4 bytes)
        length_bytes = _recv_exact(sock, 4)
        if not length_bytes:
            return None

        length = struct.unpack('!I', length_bytes)[0]

        # Validar longitud razonable (max 100MB)
        if length > 100 * 1024 * 1024:
            raise ProtocolError(f"Mensaje demasiado grande: {length} bytes")

        # Leer payload
        payload = _recv_exact(sock, length)
        if len(payload) != length:
            raise ProtocolError(f"Payload incompleto: esperado {length}, recibido {len(payload)}")

        return json.loads(payload.decode('utf-8'))

    except json.JSONDecodeError as e:
        raise ProtocolError(f"Error decodificando JSON: {e}")
    except (socket.error, OSError) as e:
        raise ProtocolError(f"Error recibiendo mensaje: {e}")


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """
    Recibe exactamente n bytes del socket.

    Args:
        sock: Socket de red
        n: Cantidad de bytes a recibir

    Returns:
        Bytes recibidos (puede ser menos de n si se cierra la conexión)
    """
    data = b''
    chunk_size = 256 * 1024  # 256KB chunks para mejor rendimiento
    while len(data) < n:
        chunk = sock.recv(min(chunk_size, n - len(data)))
        if not chunk:
            # Conexión cerrada
            return data
        data += chunk
    return data


def send_bytes(sock: socket.socket, data: bytes) -> None:
    """
    Envía datos binarios raw.

    Args:
        sock: Socket de red
        data: Bytes a enviar

    Raises:
        ProtocolError: Si hay error al enviar
    """
    try:
        sock.sendall(data)
    except (socket.error, OSError) as e:
        raise ProtocolError(f"Error enviando bytes: {e}")


def recv_bytes(sock: socket.socket, size: int) -> bytes:
    """
    Recibe exactamente size bytes.

    Args:
        sock: Socket de red
        size: Cantidad de bytes a recibir

    Returns:
        Bytes recibidos

    Raises:
        ProtocolError: Si no se pueden recibir todos los bytes
    """
    data = _recv_exact(sock, size)
    if len(data) != size:
        raise ProtocolError(f"No se recibieron todos los bytes: esperado {size}, recibido {len(data)}")
    return data


# Funciones de construcción de mensajes

def make_handshake(
    mode: str,
    codec: str,
    processing: str,
    video_info: Dict[str, Any],
    filters: Optional[list] = None,
    version: int = 1
) -> Dict[str, Any]:
    """Construye mensaje de handshake."""
    return {
        "type": "handshake",
        "version": version,
        "mode": mode,
        "codec": codec,
        "processing": processing,
        "filters": filters or [],
        "video_info": video_info
    }


def make_handshake_ack(
    accepted: bool,
    session_id: str,
    preview_url: Optional[str] = None
) -> Dict[str, Any]:
    """Construye mensaje de handshake ACK."""
    return {
        "type": "handshake_ack",
        "accepted": accepted,
        "session_id": session_id,
        "preview_url": preview_url
    }


def make_frame_metadata(seq: int, pts: int, size_bytes: int) -> Dict[str, Any]:
    """Construye mensaje de metadatos de frame."""
    return {
        "type": "frame",
        "seq": seq,
        "pts": pts,
        "size_bytes": size_bytes
    }


def make_eof(total_frames: int) -> Dict[str, Any]:
    """Construye mensaje de EOF."""
    return {
        "type": "eof",
        "total_frames": total_frames
    }


def make_progress(
    frames_processed: int,
    frames_total: int,
    fps: float,
    eta_seconds: float
) -> Dict[str, Any]:
    """Construye mensaje de progreso."""
    return {
        "type": "progress",
        "frames_processed": frames_processed,
        "frames_total": frames_total,
        "fps": fps,
        "eta_seconds": eta_seconds
    }


def make_result(
    ok: bool,
    output_path: str,
    size_bytes: int,
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Construye mensaje de resultado."""
    return {
        "type": "result",
        "ok": ok,
        "output_path": output_path,
        "size_bytes": size_bytes,
        "metrics": metrics
    }


def make_error(code: str, message: str, recoverable: bool = False) -> Dict[str, Any]:
    """Construye mensaje de error."""
    return {
        "type": "error",
        "code": code,
        "message": message,
        "recoverable": recoverable
    }
