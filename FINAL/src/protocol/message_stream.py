"""
Stream de mensajes usando generators (yield).

Implementa diferentes formas de iterar sobre mensajes recibidos por socket,
evitando while True loops y haciendo el código más Pythonic.
"""

import socket
from typing import Iterator, Dict, Any, Optional
from . import messages


# ============================================================================
# OPCIÓN 1: Generator Function (yield)
# ============================================================================

def message_stream(sock: socket.socket) -> Iterator[Dict[str, Any]]:
    """
    Generator que yields mensajes recibidos del socket.

    Usage:
        for msg in message_stream(sock):
            if msg['type'] == 'result':
                break
            process(msg)

    Args:
        sock: Socket de red

    Yields:
        Diccionarios con mensajes recibidos
    """
    while True:
        msg = messages.recv_message(sock)
        if not msg:
            return  # StopIteration
        yield msg


def message_stream_typed(sock: socket.socket) -> Iterator[Dict[str, Any]]:
    """
    Generator que yields mensajes, filtrando tipos específicos.

    Usage:
        for msg in message_stream_typed(sock):
            match msg['type']:
                case 'progress':
                    show_progress(msg)
                case 'result':
                    return process_result(msg)
                case 'error':
                    handle_error(msg)

    Args:
        sock: Socket de red

    Yields:
        Mensajes recibidos (nunca None)
    """
    while True:
        msg = messages.recv_message(sock)
        if not msg:
            break
        yield msg


def message_stream_until(
    sock: socket.socket,
    stop_type: str = "result"
) -> Iterator[Dict[str, Any]]:
    """
    Generator que yields mensajes hasta recibir tipo específico.

    El mensaje de stop también se yields (para procesarlo).

    Usage:
        for msg in message_stream_until(sock, stop_type='result'):
            if msg['type'] == 'progress':
                show_progress(msg)
            elif msg['type'] == 'result':
                # Último mensaje
                return process_result(msg)

    Args:
        sock: Socket de red
        stop_type: Tipo de mensaje que detiene el stream

    Yields:
        Mensajes hasta (e incluyendo) el de tipo stop_type
    """
    while True:
        msg = messages.recv_message(sock)
        if not msg:
            break

        yield msg

        if msg.get("type") == stop_type:
            break


# ============================================================================
# OPCIÓN 2: Iterator Class (Protocol __iter__ y __next__)
# ============================================================================

class MessageIterator:
    """
    Iterator que implementa protocol __iter__ y __next__.

    Usage:
        for msg in MessageIterator(sock):
            process(msg)

        # O explícitamente:
        it = MessageIterator(sock)
        msg1 = next(it)
        msg2 = next(it)
    """

    def __init__(self, sock: socket.socket, stop_on: Optional[str] = None):
        """
        Inicializa el iterator.

        Args:
            sock: Socket de red
            stop_on: Tipo de mensaje que detiene iteración (opcional)
        """
        self.sock = sock
        self.stop_on = stop_on
        self.stopped = False

    def __iter__(self):
        """Retorna self (protocol de iterator)."""
        return self

    def __next__(self) -> Dict[str, Any]:
        """
        Retorna siguiente mensaje.

        Raises:
            StopIteration: Cuando conexión se cierra o se alcanza stop_on
        """
        if self.stopped:
            raise StopIteration

        msg = messages.recv_message(self.sock)

        if not msg:
            self.stopped = True
            raise StopIteration

        if self.stop_on and msg.get("type") == self.stop_on:
            self.stopped = True

        return msg


# ============================================================================
# OPCIÓN 3: Context Manager + Generator
# ============================================================================

class MessageStream:
    """
    Context manager + iterator para stream de mensajes.

    Usage:
        with MessageStream(sock) as stream:
            for msg in stream:
                if msg['type'] == 'result':
                    return msg

        # O con filter:
        with MessageStream(sock, filter_types=['progress', 'result']) as stream:
            for msg in stream:
                ...
    """

    def __init__(
        self,
        sock: socket.socket,
        filter_types: Optional[list] = None,
        stop_on: Optional[str] = None
    ):
        """
        Inicializa el stream.

        Args:
            sock: Socket de red
            filter_types: Lista de tipos de mensajes a incluir (None = todos)
            stop_on: Tipo de mensaje que detiene el stream
        """
        self.sock = sock
        self.filter_types = set(filter_types) if filter_types else None
        self.stop_on = stop_on

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Podría hacer cleanup aquí si fuera necesario
        pass

    def __iter__(self):
        """Itera sobre mensajes."""
        while True:
            msg = messages.recv_message(self.sock)

            if not msg:
                break

            # Filtrar por tipo si se especificó
            if self.filter_types:
                msg_type = msg.get("type")
                if msg_type not in self.filter_types:
                    continue  # Skip this message

            yield msg

            # Stop si se alcanzó el tipo especificado
            if self.stop_on and msg.get("type") == self.stop_on:
                break


# ============================================================================
# OPCIÓN 4: Async Generator (asyncio)
# ============================================================================

async def message_stream_async(reader) -> Iterator[Dict[str, Any]]:
    """
    Async generator para cliente asyncio.

    Usage:
        async for msg in message_stream_async(reader):
            if msg['type'] == 'result':
                break

    Args:
        reader: asyncio.StreamReader

    Yields:
        Mensajes recibidos
    """
    while True:
        # Nota: necesitarías una versión async de recv_message
        msg = await recv_message_async(reader)
        if not msg:
            break
        yield msg


async def recv_message_async(reader) -> Optional[Dict[str, Any]]:
    """
    Versión async de recv_message para asyncio.

    Args:
        reader: asyncio.StreamReader

    Returns:
        Mensaje o None si conexión cerrada
    """
    import struct
    import json

    # Leer longitud
    length_bytes = await reader.readexactly(4)
    if not length_bytes:
        return None

    length = struct.unpack('!I', length_bytes)[0]

    # Leer payload
    payload = await reader.readexactly(length)
    return json.loads(payload.decode('utf-8'))


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

def example_usage_generator(sock):
    """Ejemplo con generator function."""
    print("=== Opción 1: Generator Function ===\n")

    for msg in message_stream_until(sock, stop_type='result'):
        msg_type = msg.get("type")

        if msg_type == "progress":
            frames = msg.get("frames_processed", 0)
            total = msg.get("frames_total", 0)
            print(f"Progreso: {frames}/{total}")

        elif msg_type == "result":
            print("Resultado recibido!")
            return msg

        elif msg_type == "error":
            print(f"Error: {msg.get('message')}")
            break


def example_usage_iterator(sock):
    """Ejemplo con iterator class."""
    print("=== Opción 2: Iterator Class ===\n")

    for msg in MessageIterator(sock, stop_on='result'):
        msg_type = msg.get("type")

        match msg_type:
            case "progress":
                print(f"Progreso: {msg.get('frames_processed')}")
            case "result":
                print("Resultado recibido!")
                return msg
            case "error":
                print(f"Error: {msg.get('message')}")
                break


def example_usage_context_manager(sock):
    """Ejemplo con context manager."""
    print("=== Opción 3: Context Manager + Generator ===\n")

    with MessageStream(sock, filter_types=['progress', 'result']) as stream:
        for msg in stream:
            if msg['type'] == 'progress':
                print(f"Progreso: {msg.get('frames_processed')}")
            elif msg['type'] == 'result':
                print("Resultado recibido!")
                return msg


async def example_usage_async(reader):
    """Ejemplo con async generator."""
    print("=== Opción 4: Async Generator ===\n")

    async for msg in message_stream_async(reader):
        msg_type = msg.get("type")

        if msg_type == "progress":
            print(f"Progreso: {msg.get('frames_processed')}")
        elif msg_type == "result":
            print("Resultado recibido!")
            return msg


# ============================================================================
# COMPARACIÓN
# ============================================================================

"""
COMPARACIÓN DE OPCIONES:

┌────────────────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Aspecto                │ while True  │ Generator   │ Iterator    │ Async Gen   │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Legibilidad            │ ⚠️ Meh      │ ✅ Buena    │ ✅ Buena    │ ✅ Excelente│
│ Pythonic               │ ❌ No       │ ✅ Sí       │ ✅ Sí       │ ✅ Sí       │
│ Control de flujo       │ ⚠️ Manual   │ ✅ Auto     │ ✅ Auto     │ ✅ Auto     │
│ Composabilidad         │ ❌ Difícil  │ ✅ Fácil    │ ✅ Fácil    │ ✅ Fácil    │
│ Async compatible       │ ❌ No       │ ❌ No       │ ❌ No       │ ✅ Sí       │
│ Overhead               │ ✅ Cero     │ ⚠️ Mínimo   │ ⚠️ Mínimo   │ ⚠️ Mínimo   │
│ Cancelación            │ ⚠️ Manual   │ ⚠️ break    │ ⚠️ break    │ ✅ cancel() │
└────────────────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

RECOMENDACIÓN:
- Cliente sync simple: Generator Function (Opción 1)
- Cliente con state:    Iterator Class (Opción 2)
- Cliente con filters:  Context Manager (Opción 3)
- Cliente async:        Async Generator (Opción 4)
"""
