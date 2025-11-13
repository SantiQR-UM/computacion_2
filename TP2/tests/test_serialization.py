"""
Tests para el módulo de serialización.

Prueba las funcionalidades de serialización JSON y pickle,
y la creación de mensajes de request/response.
"""

import unittest
from common.serialization import (
    serialize_json, deserialize_json,
    serialize_pickle, deserialize_pickle,
    encode_binary_to_base64, decode_base64_to_binary,
    create_request, create_response,
    validate_request, validate_response,
    SerializationError
)


class TestSerialization(unittest.TestCase):
    """Tests para funciones de serialización."""

    def test_serialize_deserialize_json(self):
        """Test de serialización y deserialización JSON."""
        data = {
            'nombre': 'Test',
            'número': 42,
            'lista': [1, 2, 3],
            'nested': {'key': 'value'}
        }

        # Serializar
        serialized = serialize_json(data)
        self.assertIsInstance(serialized, bytes)

        # Deserializar
        deserialized = deserialize_json(serialized)
        self.assertEqual(deserialized, data)

    def test_serialize_deserialize_pickle(self):
        """Test de serialización y deserialización con pickle."""
        data = {
            'complex': complex(1, 2),
            'set': {1, 2, 3},
            'tuple': (1, 2, 3)
        }

        # Serializar
        serialized = serialize_pickle(data)
        self.assertIsInstance(serialized, bytes)

        # Deserializar
        deserialized = deserialize_pickle(serialized)
        self.assertEqual(deserialized['complex'], data['complex'])
        self.assertEqual(deserialized['set'], data['set'])

    def test_base64_encoding(self):
        """Test de codificación/decodificación base64."""
        data = b'Hello, World!'

        # Codificar
        encoded = encode_binary_to_base64(data)
        self.assertIsInstance(encoded, str)

        # Decodificar
        decoded = decode_base64_to_binary(encoded)
        self.assertEqual(decoded, data)

    def test_create_request(self):
        """Test de creación de requests."""
        request = create_request('test_operation', {'param1': 'value1'})

        self.assertEqual(request['type'], 'request')
        self.assertEqual(request['operation'], 'test_operation')
        self.assertEqual(request['params']['param1'], 'value1')

    def test_create_response_success(self):
        """Test de creación de response exitosa."""
        response = create_response(True, data={'result': 'ok'})

        self.assertEqual(response['type'], 'response')
        self.assertTrue(response['success'])
        self.assertEqual(response['data']['result'], 'ok')

    def test_create_response_error(self):
        """Test de creación de response con error."""
        response = create_response(False, error='Error message')

        self.assertEqual(response['type'], 'response')
        self.assertFalse(response['success'])
        self.assertEqual(response['error'], 'Error message')

    def test_validate_request_valid(self):
        """Test de validación de request válido."""
        request = create_request('operation', {'key': 'value'})
        self.assertTrue(validate_request(request))

    def test_validate_request_invalid(self):
        """Test de validación de request inválido."""
        invalid_request = {'type': 'request'}  # Falta operation y params

        with self.assertRaises(SerializationError):
            validate_request(invalid_request)

    def test_validate_response_valid(self):
        """Test de validación de response válida."""
        response = create_response(True, data={'result': 'ok'})
        self.assertTrue(validate_response(response))

    def test_validate_response_invalid(self):
        """Test de validación de response inválida."""
        invalid_response = {'type': 'response'}  # Falta success

        with self.assertRaises(SerializationError):
            validate_response(invalid_response)


if __name__ == '__main__':
    unittest.main()
