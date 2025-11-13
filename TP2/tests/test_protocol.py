"""
Tests para el módulo de protocolo.

Prueba las funcionalidades de codificación/decodificación de mensajes
y manejo del protocolo binario.
"""

import unittest
from common.protocol import (
    encode_message, decode_header,
    HEADER_SIZE, MAX_MESSAGE_SIZE,
    ProtocolError
)


class TestProtocol(unittest.TestCase):
    """Tests para funciones del protocolo."""

    def test_encode_decode_message(self):
        """Test de codificación de mensajes."""
        data = b'Hello, World!'

        # Codificar
        encoded = encode_message(data)

        # Verificar formato
        self.assertEqual(len(encoded), HEADER_SIZE + len(data))

        # Decodificar header
        header = encoded[:HEADER_SIZE]
        length = decode_header(header)

        self.assertEqual(length, len(data))

        # Verificar payload
        payload = encoded[HEADER_SIZE:]
        self.assertEqual(payload, data)

    def test_encode_empty_message(self):
        """Test de codificación de mensaje vacío."""
        data = b''

        encoded = encode_message(data)
        self.assertEqual(len(encoded), HEADER_SIZE)

        header = encoded[:HEADER_SIZE]
        length = decode_header(header)
        self.assertEqual(length, 0)

    def test_encode_large_message(self):
        """Test de codificación de mensaje grande."""
        data = b'X' * 1000000  # 1 MB

        encoded = encode_message(data)
        self.assertEqual(len(encoded), HEADER_SIZE + len(data))

        header = encoded[:HEADER_SIZE]
        length = decode_header(header)
        self.assertEqual(length, len(data))

    def test_encode_message_too_large(self):
        """Test de mensaje demasiado grande."""
        data = b'X' * (MAX_MESSAGE_SIZE + 1)

        with self.assertRaises(ProtocolError):
            encode_message(data)

    def test_decode_invalid_header_size(self):
        """Test de header con tamaño inválido."""
        invalid_header = b'ABC'  # Menos de 4 bytes

        with self.assertRaises(ProtocolError):
            decode_header(invalid_header)

    def test_decode_invalid_length(self):
        """Test de longitud inválida en header."""
        # Crear header con longitud > MAX_MESSAGE_SIZE
        import struct
        invalid_header = struct.pack('!I', MAX_MESSAGE_SIZE + 1)

        with self.assertRaises(ProtocolError):
            decode_header(invalid_header)


if __name__ == '__main__':
    unittest.main()
