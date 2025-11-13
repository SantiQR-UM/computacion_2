"""
Protocolo de comunicación entre servidores.

Este módulo implementa el protocolo de comunicación basado en sockets TCP
entre el servidor de scraping (asyncio) y el servidor de procesamiento (multiprocessing).

Protocolo:
    [4 bytes: longitud del mensaje][N bytes: mensaje serializado]

El protocolo es binario y utiliza network byte order (big-endian) para
la longitud del mensaje.
"""

import struct
import socket
import asyncio
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Constantes del protocolo
HEADER_SIZE = 4  # 4 bytes para la longitud del mensaje
HEADER_FORMAT = '!I'  # unsigned int, network byte order
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10 MB máximo por mensaje


class ProtocolError(Exception):
    """Excepción para errores del protocolo de comunicación."""
    pass


def encode_message(data: bytes) -> bytes:
    """
    Codifica un mensaje con el formato del protocolo.

    Args:
        data: Datos binarios a enviar

    Returns:
        Mensaje codificado con header de longitud

    Raises:
        ProtocolError: Si el mensaje es demasiado grande
    """
    length = len(data)
    if length > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"Mensaje demasiado grande: {length} bytes (máximo: {MAX_MESSAGE_SIZE})")

    header = struct.pack(HEADER_FORMAT, length)
    return header + data


def decode_header(header: bytes) -> int:
    """
    Decodifica el header para obtener la longitud del mensaje.

    Args:
        header: Header de 4 bytes

    Returns:
        Longitud del mensaje

    Raises:
        ProtocolError: Si el header es inválido o la longitud es inválida
    """
    if len(header) != HEADER_SIZE:
        raise ProtocolError(f"Header inválido: esperado {HEADER_SIZE} bytes, recibido {len(header)}")

    length = struct.unpack(HEADER_FORMAT, header)[0]

    if length > MAX_MESSAGE_SIZE:
        raise ProtocolError(f"Longitud de mensaje inválida: {length} bytes")

    return length


def send_message(sock: socket.socket, data: bytes) -> None:
    """
    Envía un mensaje completo a través de un socket (versión síncrona).

    Args:
        sock: Socket conectado
        data: Datos a enviar

    Raises:
        ProtocolError: Si hay un error al enviar
    """
    try:
        message = encode_message(data)
        sock.sendall(message)
        logger.debug(f"Mensaje enviado: {len(data)} bytes")
    except socket.error as e:
        raise ProtocolError(f"Error al enviar mensaje: {e}")


def receive_message(sock: socket.socket, timeout: Optional[float] = None) -> bytes:
    """
    Recibe un mensaje completo de un socket (versión síncrona).

    Args:
        sock: Socket conectado
        timeout: Timeout en segundos (None para sin timeout)

    Returns:
        Datos recibidos

    Raises:
        ProtocolError: Si hay un error al recibir
    """
    try:
        old_timeout = sock.gettimeout()
        if timeout is not None:
            sock.settimeout(timeout)

        # Recibir header
        header = _receive_exact(sock, HEADER_SIZE)
        if not header:
            raise ProtocolError("Conexión cerrada por el peer")

        # Decodificar longitud
        length = decode_header(header)

        # Recibir mensaje completo
        data = _receive_exact(sock, length)
        if len(data) != length:
            raise ProtocolError(f"Mensaje incompleto: esperado {length} bytes, recibido {len(data)}")

        logger.debug(f"Mensaje recibido: {len(data)} bytes")
        return data

    except socket.timeout:
        raise ProtocolError("Timeout al recibir mensaje")
    except socket.error as e:
        raise ProtocolError(f"Error al recibir mensaje: {e}")
    finally:
        if timeout is not None:
            sock.settimeout(old_timeout)


def _receive_exact(sock: socket.socket, size: int) -> bytes:
    """
    Recibe exactamente 'size' bytes de un socket.

    Args:
        sock: Socket conectado
        size: Número de bytes a recibir

    Returns:
        Datos recibidos
    """
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


async def send_message_async(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, data: bytes) -> None:
    """
    Envía un mensaje completo a través de streams asyncio.

    Args:
        reader: StreamReader (no usado pero mantiene consistencia de API)
        writer: StreamWriter
        data: Datos a enviar

    Raises:
        ProtocolError: Si hay un error al enviar
    """
    try:
        message = encode_message(data)
        writer.write(message)
        await writer.drain()
        logger.debug(f"Mensaje enviado (async): {len(data)} bytes")
    except Exception as e:
        raise ProtocolError(f"Error al enviar mensaje (async): {e}")


async def receive_message_async(reader: asyncio.StreamReader, timeout: Optional[float] = None) -> bytes:
    """
    Recibe un mensaje completo de un StreamReader asyncio.

    Args:
        reader: StreamReader
        timeout: Timeout en segundos (None para sin timeout)

    Returns:
        Datos recibidos

    Raises:
        ProtocolError: Si hay un error al recibir
    """
    try:
        # Recibir header con timeout
        if timeout:
            header = await asyncio.wait_for(reader.readexactly(HEADER_SIZE), timeout=timeout)
        else:
            header = await reader.readexactly(HEADER_SIZE)

        if not header:
            raise ProtocolError("Conexión cerrada por el peer")

        # Decodificar longitud
        length = decode_header(header)

        # Recibir mensaje completo con timeout
        if timeout:
            data = await asyncio.wait_for(reader.readexactly(length), timeout=timeout)
        else:
            data = await reader.readexactly(length)

        logger.debug(f"Mensaje recibido (async): {len(data)} bytes")
        return data

    except asyncio.TimeoutError:
        raise ProtocolError("Timeout al recibir mensaje (async)")
    except asyncio.IncompleteReadError as e:
        raise ProtocolError(f"Mensaje incompleto: esperado {e.expected} bytes, recibido {len(e.partial)}")
    except Exception as e:
        raise ProtocolError(f"Error al recibir mensaje (async): {e}")


class ProtocolClient:
    """Cliente del protocolo para comunicación con el servidor de procesamiento."""

    def __init__(self, host: str, port: int):
        """
        Inicializa el cliente del protocolo.

        Args:
            host: Dirección del servidor
            port: Puerto del servidor
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self, timeout: float = 5.0) -> None:
        """
        Conecta al servidor de procesamiento.

        Args:
            timeout: Timeout de conexión en segundos

        Raises:
            ProtocolError: Si no puede conectar
        """
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout
            )
            logger.info(f"Conectado a {self.host}:{self.port}")
        except asyncio.TimeoutError:
            raise ProtocolError(f"Timeout al conectar a {self.host}:{self.port}")
        except Exception as e:
            raise ProtocolError(f"Error al conectar a {self.host}:{self.port}: {e}")

    async def send(self, data: bytes, timeout: Optional[float] = None) -> None:
        """
        Envía datos al servidor.

        Args:
            data: Datos a enviar
            timeout: Timeout en segundos
        """
        if not self.writer:
            raise ProtocolError("Cliente no conectado")
        await send_message_async(self.reader, self.writer, data)

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Recibe datos del servidor.

        Args:
            timeout: Timeout en segundos

        Returns:
            Datos recibidos
        """
        if not self.reader:
            raise ProtocolError("Cliente no conectado")
        return await receive_message_async(self.reader, timeout)

    async def send_and_receive(self, data: bytes, timeout: Optional[float] = 30.0) -> bytes:
        """
        Envía datos y espera respuesta.

        Args:
            data: Datos a enviar
            timeout: Timeout total en segundos

        Returns:
            Respuesta del servidor
        """
        await self.send(data, timeout=timeout)
        return await self.receive(timeout=timeout)

    async def close(self) -> None:
        """Cierra la conexión."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Conexión cerrada")
        self.reader = None
        self.writer = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
