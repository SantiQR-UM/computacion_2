"""
Serialización y deserialización de datos.

Este módulo proporciona funciones para serializar y deserializar datos
que se intercambian entre los servidores. Soporta JSON y pickle.

JSON se usa para datos simples y compatibilidad.
Pickle se usa para objetos Python complejos (con precaución).
"""

import json
import pickle
import base64
from typing import Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Formatos de serialización disponibles."""
    JSON = 'json'
    PICKLE = 'pickle'


class SerializationError(Exception):
    """Excepción para errores de serialización."""
    pass


def serialize_json(data: Any) -> bytes:
    """
    Serializa datos a JSON.

    Args:
        data: Datos a serializar (deben ser serializables a JSON)

    Returns:
        Bytes codificados en UTF-8 del JSON

    Raises:
        SerializationError: Si los datos no son serializables a JSON
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        return json_str.encode('utf-8')
    except (TypeError, ValueError) as e:
        raise SerializationError(f"Error al serializar a JSON: {e}")


def deserialize_json(data: bytes) -> Any:
    """
    Deserializa datos desde JSON.

    Args:
        data: Bytes del JSON

    Returns:
        Datos deserializados

    Raises:
        SerializationError: Si los datos no son JSON válido
    """
    try:
        json_str = data.decode('utf-8')
        return json.loads(json_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise SerializationError(f"Error al deserializar JSON: {e}")


def serialize_pickle(data: Any) -> bytes:
    """
    Serializa datos usando pickle.

    Args:
        data: Datos a serializar

    Returns:
        Bytes del pickle

    Raises:
        SerializationError: Si los datos no son serializables con pickle
    """
    try:
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    except pickle.PicklingError as e:
        raise SerializationError(f"Error al serializar con pickle: {e}")


def deserialize_pickle(data: bytes) -> Any:
    """
    Deserializa datos desde pickle.

    Args:
        data: Bytes del pickle

    Returns:
        Datos deserializados

    Raises:
        SerializationError: Si los datos no son pickle válido
    """
    try:
        return pickle.loads(data)
    except pickle.UnpicklingError as e:
        raise SerializationError(f"Error al deserializar pickle: {e}")


def serialize(data: Any, format: SerializationFormat = SerializationFormat.JSON) -> bytes:
    """
    Serializa datos usando el formato especificado.

    Args:
        data: Datos a serializar
        format: Formato de serialización

    Returns:
        Datos serializados

    Raises:
        SerializationError: Si hay un error al serializar
    """
    if format == SerializationFormat.JSON:
        return serialize_json(data)
    elif format == SerializationFormat.PICKLE:
        return serialize_pickle(data)
    else:
        raise SerializationError(f"Formato de serialización no soportado: {format}")


def deserialize(data: bytes, format: SerializationFormat = SerializationFormat.JSON) -> Any:
    """
    Deserializa datos usando el formato especificado.

    Args:
        data: Datos a deserializar
        format: Formato de serialización

    Returns:
        Datos deserializados

    Raises:
        SerializationError: Si hay un error al deserializar
    """
    if format == SerializationFormat.JSON:
        return deserialize_json(data)
    elif format == SerializationFormat.PICKLE:
        return deserialize_pickle(data)
    else:
        raise SerializationError(f"Formato de serialización no soportado: {format}")


def encode_binary_to_base64(data: bytes) -> str:
    """
    Codifica datos binarios a base64 para incluir en JSON.

    Args:
        data: Datos binarios

    Returns:
        String base64
    """
    return base64.b64encode(data).decode('ascii')


def decode_base64_to_binary(data: str) -> bytes:
    """
    Decodifica string base64 a datos binarios.

    Args:
        data: String base64

    Returns:
        Datos binarios

    Raises:
        SerializationError: Si el base64 es inválido
    """
    try:
        return base64.b64decode(data)
    except Exception as e:
        raise SerializationError(f"Error al decodificar base64: {e}")


def create_request(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un mensaje de request estándar.

    Args:
        operation: Nombre de la operación
        params: Parámetros de la operación

    Returns:
        Diccionario con el request
    """
    return {
        'type': 'request',
        'operation': operation,
        'params': params
    }


def create_response(success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
    """
    Crea un mensaje de response estándar.

    Args:
        success: Si la operación fue exitosa
        data: Datos de la respuesta (si success=True)
        error: Mensaje de error (si success=False)

    Returns:
        Diccionario con la response
    """
    response = {
        'type': 'response',
        'success': success
    }

    if success:
        response['data'] = data
    else:
        response['error'] = error

    return response


def validate_request(request: Dict[str, Any]) -> bool:
    """
    Valida que un request tenga el formato correcto.

    Args:
        request: Diccionario del request

    Returns:
        True si es válido

    Raises:
        SerializationError: Si el request es inválido
    """
    if not isinstance(request, dict):
        raise SerializationError("Request debe ser un diccionario")

    if request.get('type') != 'request':
        raise SerializationError("Request debe tener type='request'")

    if 'operation' not in request:
        raise SerializationError("Request debe tener campo 'operation'")

    if 'params' not in request:
        raise SerializationError("Request debe tener campo 'params'")

    if not isinstance(request['params'], dict):
        raise SerializationError("Params debe ser un diccionario")

    return True


def validate_response(response: Dict[str, Any]) -> bool:
    """
    Valida que una response tenga el formato correcto.

    Args:
        response: Diccionario de la response

    Returns:
        True si es válido

    Raises:
        SerializationError: Si la response es inválida
    """
    if not isinstance(response, dict):
        raise SerializationError("Response debe ser un diccionario")

    if response.get('type') != 'response':
        raise SerializationError("Response debe tener type='response'")

    if 'success' not in response:
        raise SerializationError("Response debe tener campo 'success'")

    if not isinstance(response['success'], bool):
        raise SerializationError("Campo 'success' debe ser booleano")

    if response['success']:
        if 'data' not in response:
            raise SerializationError("Response exitosa debe tener campo 'data'")
    else:
        if 'error' not in response:
            raise SerializationError("Response con error debe tener campo 'error'")

    return True
