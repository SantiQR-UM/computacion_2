"""
Procesamiento de imágenes.

Este módulo descarga y procesa imágenes de páginas web,
generando thumbnails optimizados.
"""

import logging
import base64
from typing import List, Dict, Optional
from io import BytesIO
import requests

logger = logging.getLogger(__name__)


class ImageProcessorError(Exception):
    """Excepción para errores de procesamiento de imágenes."""
    pass


def download_image(url: str, timeout: int = 10) -> bytes:
    """
    Descarga una imagen desde una URL.

    Args:
        url: URL de la imagen
        timeout: Timeout en segundos

    Returns:
        Bytes de la imagen

    Raises:
        ImageProcessorError: Si hay un error al descargar
    """
    try:
        response = requests.get(url, timeout=timeout, stream=True)

        if response.status_code != 200:
            raise ImageProcessorError(f"HTTP {response.status_code}")

        # Verificar que sea una imagen
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            raise ImageProcessorError(f"Content-Type no es imagen: {content_type}")

        # Limitar tamaño máximo
        max_size = 10 * 1024 * 1024  # 10 MB
        content = response.content

        if len(content) > max_size:
            raise ImageProcessorError(f"Imagen demasiado grande: {len(content)} bytes")

        logger.debug(f"Imagen descargada: {len(content)} bytes")
        return content

    except requests.Timeout:
        raise ImageProcessorError(f"Timeout al descargar imagen: {url}")
    except requests.RequestException as e:
        raise ImageProcessorError(f"Error al descargar imagen: {e}")


def create_thumbnail(image_bytes: bytes, max_size: tuple = (200, 200)) -> bytes:
    """
    Crea un thumbnail de una imagen.

    Args:
        image_bytes: Bytes de la imagen original
        max_size: Tamaño máximo (ancho, alto)

    Returns:
        Bytes del thumbnail en formato PNG

    Raises:
        ImageProcessorError: Si hay un error al procesar
    """
    try:
        from PIL import Image

        # Cargar imagen
        img = Image.open(BytesIO(image_bytes))

        # Convertir a RGB si es necesario (para PNG con transparencia, etc.)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Crear thumbnail
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Guardar como PNG optimizado
        output = BytesIO()
        img.save(output, format='PNG', optimize=True)
        thumbnail_bytes = output.getvalue()

        logger.debug(f"Thumbnail creado: {len(image_bytes)} -> {len(thumbnail_bytes)} bytes")
        return thumbnail_bytes

    except ImportError:
        raise ImageProcessorError("Pillow no está instalado")
    except Exception as e:
        raise ImageProcessorError(f"Error al crear thumbnail: {e}")


def image_to_base64(image_bytes: bytes) -> str:
    """
    Convierte bytes de imagen a string base64.

    Args:
        image_bytes: Bytes de la imagen

    Returns:
        String base64
    """
    return base64.b64encode(image_bytes).decode('ascii')


def get_image_info(image_bytes: bytes) -> Dict:
    """
    Obtiene información sobre una imagen.

    Args:
        image_bytes: Bytes de la imagen

    Returns:
        Diccionario con información de la imagen
    """
    try:
        from PIL import Image

        img = Image.open(BytesIO(image_bytes))

        return {
            'format': img.format,
            'mode': img.mode,
            'width': img.width,
            'height': img.height,
            'size_bytes': len(image_bytes)
        }

    except Exception as e:
        logger.warning(f"No se pudo obtener info de imagen: {e}")
        return {
            'size_bytes': len(image_bytes)
        }


def process_images(image_urls: List[str], max_images: int = 5) -> List[Dict]:
    """
    Procesa múltiples imágenes: descarga y genera thumbnails.

    Args:
        image_urls: Lista de URLs de imágenes
        max_images: Número máximo de imágenes a procesar

    Returns:
        Lista de diccionarios con thumbnails y metadata
    """
    results = []

    for i, url in enumerate(image_urls[:max_images]):
        try:
            logger.debug(f"Procesando imagen {i+1}/{min(len(image_urls), max_images)}: {url}")

            # Descargar imagen
            image_bytes = download_image(url, timeout=10)

            # Obtener info
            info = get_image_info(image_bytes)

            # Crear thumbnail
            thumbnail_bytes = create_thumbnail(image_bytes, max_size=(200, 200))

            # Convertir a base64
            thumbnail_b64 = image_to_base64(thumbnail_bytes)

            results.append({
                'url': url,
                'thumbnail': thumbnail_b64,
                'original_size_bytes': info.get('size_bytes', 0),
                'thumbnail_size_bytes': len(thumbnail_bytes),
                'width': info.get('width'),
                'height': info.get('height'),
                'format': info.get('format')
            })

            logger.info(f"Imagen procesada: {url}")

        except Exception as e:
            logger.warning(f"Error al procesar imagen {url}: {e}")
            results.append({
                'url': url,
                'error': str(e)
            })

    return results


# Función principal que se ejecutará en un proceso separado
def process_images_task(image_urls: List[str], max_images: int = 5) -> Dict:
    """
    Función principal para procesamiento de imágenes.

    Esta función está diseñada para ejecutarse en un proceso separado
    del pool de multiprocessing.

    Args:
        image_urls: Lista de URLs de imágenes
        max_images: Número máximo de imágenes a procesar

    Returns:
        Diccionario con resultados del procesamiento
    """
    try:
        if not image_urls:
            return {
                'success': True,
                'thumbnails': [],
                'processed_count': 0
            }

        thumbnails = process_images(image_urls, max_images)

        # Contar cuántas se procesaron exitosamente
        successful = sum(1 for t in thumbnails if 'thumbnail' in t)

        return {
            'success': True,
            'thumbnails': thumbnails,
            'processed_count': successful,
            'total_images': len(image_urls)
        }

    except Exception as e:
        logger.error(f"Error al procesar imágenes: {e}")
        return {
            'success': False,
            'error': str(e)
        }
