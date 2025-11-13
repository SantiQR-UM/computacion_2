#!/usr/bin/env python3
"""
Servidor de Scraping Asíncrono (Parte A).

Este servidor HTTP asíncrono maneja requests de scraping web:
- Recibe URLs via HTTP
- Realiza scraping asíncrono sin bloquear
- Se comunica con el servidor de procesamiento para tareas CPU-bound
- Devuelve respuestas JSON consolidadas

Arquitectura:
    - aiohttp para servidor HTTP asíncrono
    - asyncio para operaciones I/O no bloqueantes
    - Cliente de protocolo para comunicación con servidor de procesamiento

Uso:
    python server_scraping.py -i 127.0.0.1 -p 8000 -w 4
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from aiohttp import web
import aiohttp

from scraper.async_http import AsyncHTTPClient
from scraper.html_parser import HTMLParser
from scraper.metadata_extractor import extract_relevant_metadata
from common.protocol import ProtocolClient, ProtocolError
from common.serialization import (
    serialize_json, deserialize_json,
    create_request, validate_response
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Variables globales para configuración
processing_server_host: Optional[str] = None
processing_server_port: Optional[int] = None


async def handle_scrape(request: web.Request) -> web.Response:
    """
    Handler para endpoint /scrape.

    Query params:
        url: URL a scrapear (requerido)

    Returns:
        JSON con datos de scraping y procesamiento
    """
    try:
        # Obtener URL de query params
        url = request.query.get('url')

        if not url:
            return web.json_response(
                {'status': 'error', 'error': 'Parámetro "url" requerido'},
                status=400
            )

        # Validar URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("URL inválida")
        except Exception:
            return web.json_response(
                {'status': 'error', 'error': 'URL inválida'},
                status=400
            )

        logger.info(f"Scraping request: {url}")

        # Realizar scraping
        scraping_data = await scrape_url(url)

        # Obtener datos de procesamiento
        processing_data = await get_processing_data(url, scraping_data)

        # Construir respuesta consolidada
        response_data = {
            'url': url,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'scraping_data': scraping_data,
            'processing_data': processing_data,
            'status': 'success'
        }

        logger.info(f"Scraping completado exitosamente: {url}")
        return web.json_response(response_data)

    except asyncio.TimeoutError:
        logger.error(f"Timeout al procesar {url}")
        return web.json_response(
            {'status': 'error', 'error': 'Timeout al procesar la solicitud'},
            status=504
        )

    except Exception as e:
        logger.error(f"Error al procesar scraping: {e}", exc_info=True)
        return web.json_response(
            {'status': 'error', 'error': str(e)},
            status=500
        )


async def scrape_url(url: str) -> dict:
    """
    Realiza el scraping de una URL.

    Args:
        url: URL a scrapear

    Returns:
        Diccionario con datos extraídos
    """
    async with AsyncHTTPClient(timeout=30.0) as client:
        # Descargar HTML
        html, status, headers = await client.get(url)

        if status != 200:
            raise Exception(f"HTTP {status} al solicitar {url}")

        # Parsear HTML
        parser = HTMLParser(html, base_url=url)

        # Extraer información
        title = parser.get_title()
        links = parser.get_links()
        images = parser.get_images()
        meta_tags = extract_relevant_metadata(html)
        structure = parser.get_headers_structure()

        return {
            'title': title,
            'links': links[:50],  # Limitar a 50 links
            'meta_tags': meta_tags,
            'structure': structure,
            'images_count': len(images),
            'images_urls': [img['src'] for img in images[:10]]  # Primeras 10 imágenes
        }


async def get_processing_data(url: str, scraping_data: dict) -> dict:
    """
    Obtiene datos de procesamiento del servidor de procesamiento.

    Args:
        url: URL procesada
        scraping_data: Datos de scraping ya obtenidos

    Returns:
        Diccionario con datos de procesamiento
    """
    if not processing_server_host or not processing_server_port:
        logger.warning("Servidor de procesamiento no configurado, omitiendo procesamiento")
        return {
            'screenshot': None,
            'performance': None,
            'thumbnails': []
        }

    try:
        # Conectar al servidor de procesamiento
        async with ProtocolClient(processing_server_host, processing_server_port) as client:

            # Crear request para procesamiento completo
            image_urls = scraping_data.get('images_urls', [])

            request_data = create_request('all', {
                'url': url,
                'html': None,  # No enviamos HTML para que el servidor lo descargue
                'image_urls': image_urls
            })

            # Enviar request y recibir response
            request_bytes = serialize_json(request_data)
            response_bytes = await client.send_and_receive(request_bytes, timeout=90.0)

            # Deserializar response
            response = deserialize_json(response_bytes)
            validate_response(response)

            if not response['success']:
                raise Exception(f"Error del servidor de procesamiento: {response.get('error')}")

            data = response['data']

            # Extraer resultados
            screenshot_data = data.get('screenshot', {})
            performance_data = data.get('performance', {})
            images_data = data.get('images', {})

            return {
                'screenshot': screenshot_data.get('screenshot') if screenshot_data.get('success') else None,
                'performance': {
                    'load_time_ms': performance_data.get('load_time_ms'),
                    'total_size_kb': performance_data.get('total_size_kb') or performance_data.get('estimated_total_size_kb'),
                    'num_requests': performance_data.get('num_requests') or performance_data.get('estimated_num_requests')
                } if performance_data.get('success') else {},
                'thumbnails': [
                    t.get('thumbnail')
                    for t in images_data.get('thumbnails', [])
                    if 'thumbnail' in t
                ]
            }

    except ProtocolError as e:
        logger.error(f"Error de comunicación con servidor de procesamiento: {e}")
        return {
            'screenshot': None,
            'performance': None,
            'thumbnails': [],
            'error': f"Processing server error: {e}"
        }

    except Exception as e:
        logger.error(f"Error al obtener datos de procesamiento: {e}", exc_info=True)
        return {
            'screenshot': None,
            'performance': None,
            'thumbnails': [],
            'error': str(e)
        }


async def handle_health(request: web.Request) -> web.Response:
    """Handler para endpoint /health."""
    return web.json_response({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })


async def handle_index(request: web.Request) -> web.Response:
    """Handler para endpoint raíz."""
    return web.Response(
        text="""
<!DOCTYPE html>
<html>
<head>
    <title>Servidor de Scraping Web</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Servidor de Scraping Web Distribuido</h1>
    <p>Servidor HTTP asíncrono para scraping y análisis de páginas web.</p>

    <h2>Endpoints Disponibles</h2>

    <div class="endpoint">
        <strong>GET /scrape</strong>
        <p>Realiza scraping de una URL.</p>
        <p>Query params: <code>url</code> (requerido)</p>
        <p>Ejemplo: <code>/scrape?url=https://example.com</code></p>
    </div>

    <div class="endpoint">
        <strong>GET /health</strong>
        <p>Verifica el estado del servidor.</p>
    </div>

    <h2>Ejemplo de Uso</h2>
    <pre><code>curl "http://localhost:8000/scrape?url=https://example.com"</code></pre>
</body>
</html>
        """,
        content_type='text/html'
    )


def create_app() -> web.Application:
    """
    Crea la aplicación aiohttp.

    Returns:
        Aplicación web configurada
    """
    app = web.Application()

    # Rutas
    app.router.add_get('/', handle_index)
    app.router.add_get('/scrape', handle_scrape)
    app.router.add_get('/health', handle_health)

    return app


def parse_arguments():
    """
    Parsea argumentos de línea de comandos.

    Returns:
        Namespace con los argumentos
    """
    parser = argparse.ArgumentParser(
        description='Servidor de Scraping Web Asíncrono',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s -i 127.0.0.1 -p 8000
  %(prog)s -i :: -p 8000 --processing-host 127.0.0.1 --processing-port 8001
  %(prog)s -i 0.0.0.0 -p 8000 -w 8 --debug
        """
    )

    parser.add_argument(
        '-i', '--ip',
        required=True,
        help='Dirección de escucha (soporta IPv4/IPv6)'
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        required=True,
        help='Puerto de escucha'
    )

    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=4,
        help='Número de workers (default: 4)'
    )

    parser.add_argument(
        '--processing-host',
        default='127.0.0.1',
        help='Host del servidor de procesamiento (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--processing-port',
        type=int,
        default=8001,
        help='Puerto del servidor de procesamiento (default: 8001)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Activar modo debug'
    )

    return parser.parse_args()


def signal_handler(signum):
    """Handler para señales de terminación."""
    logger.info(f"Señal {signum} recibida, cerrando servidor...")
    sys.exit(0)


def main():
    """Función principal."""
    global processing_server_host, processing_server_port

    args = parse_arguments()

    # Configurar logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Configurar servidor de procesamiento
    processing_server_host = args.processing_host
    processing_server_port = args.processing_port

    logger.info(f"Servidor de procesamiento: {processing_server_host}:{processing_server_port}")

    # Crear aplicación
    app = create_app()

    # Registrar signal handlers (compatible con Windows)
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s))

    # Ejecutar servidor
    try:
        logger.info(f"Iniciando servidor de scraping en {args.ip}:{args.port}")
        logger.info(f"Workers: {args.workers}")

        web.run_app(
            app,
            host=args.ip,
            port=args.port,
            access_log=logger if args.debug else None
        )

    except KeyboardInterrupt:
        logger.info("Servidor interrumpido por el usuario")

    except Exception as e:
        logger.error(f"Error al iniciar servidor: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
