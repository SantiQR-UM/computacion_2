#!/usr/bin/env python3
"""
Servidor de Procesamiento con Multiprocessing (Parte B).

Este servidor maneja tareas computacionalmente intensivas usando multiprocessing:
- Generación de screenshots
- Análisis de rendimiento
- Procesamiento de imágenes

Arquitectura:
    - SocketServer para manejar conexiones TCP
    - Pool de procesos para procesamiento paralelo
    - Protocolo binario para comunicación con servidor de scraping

Uso:
    python server_processing.py -i 127.0.0.1 -p 8001 -n 4
"""

import argparse
import logging
import socketserver
import signal
import sys
from multiprocessing import Pool, cpu_count
from typing import Optional

from common.protocol import receive_message, send_message, ProtocolError
from common.serialization import (
    deserialize_json, serialize_json,
    validate_request, create_response
)
from processor.screenshot import process_screenshot
from processor.performance import process_performance
from processor.image_processor import process_images_task

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Pool global de procesos
process_pool: Optional[Pool] = None


class ProcessingRequestHandler(socketserver.BaseRequestHandler):
    """
    Handler para procesar requests del servidor de scraping.

    Recibe requests via socket, las ejecuta en el pool de procesos,
    y devuelve las respuestas.
    """

    def handle(self):
        """Maneja una conexión entrante."""
        client_address = self.client_address
        logger.info(f"Nueva conexión desde {client_address}")

        try:
            # Recibir request
            request_data = receive_message(self.request, timeout=60.0)
            request = deserialize_json(request_data)

            logger.debug(f"Request recibido: {request.get('operation', 'unknown')}")

            # Validar request
            validate_request(request)

            # Procesar request
            response = self.process_request(request)

            # Enviar response
            response_data = serialize_json(response)
            send_message(self.request, response_data)

            logger.info(f"Response enviado a {client_address}")

        except ProtocolError as e:
            logger.error(f"Error de protocolo: {e}")
            self._send_error(f"Protocol error: {e}")

        except Exception as e:
            logger.error(f"Error al procesar request: {e}", exc_info=True)
            self._send_error(f"Internal error: {e}")

        finally:
            logger.info(f"Conexión cerrada con {client_address}")

    def process_request(self, request: dict) -> dict:
        """
        Procesa un request ejecutando la operación correspondiente.

        Args:
            request: Diccionario con el request

        Returns:
            Diccionario con la response
        """
        operation = request['operation']
        params = request['params']

        try:
            if operation == 'screenshot':
                result = self._process_screenshot(params)
            elif operation == 'performance':
                result = self._process_performance(params)
            elif operation == 'images':
                result = self._process_images(params)
            elif operation == 'all':
                result = self._process_all(params)
            else:
                return create_response(False, error=f"Operación desconocida: {operation}")

            if result.get('success'):
                return create_response(True, data=result)
            else:
                return create_response(False, error=result.get('error', 'Unknown error'))

        except Exception as e:
            logger.error(f"Error al ejecutar {operation}: {e}", exc_info=True)
            return create_response(False, error=str(e))

    def _process_screenshot(self, params: dict) -> dict:
        """Procesa una request de screenshot."""
        url = params.get('url')
        if not url:
            return {'success': False, 'error': 'URL requerida'}

        max_width = params.get('max_width', 1280)
        max_height = params.get('max_height', 720)

        logger.info(f"Procesando screenshot: {url}")

        # Ejecutar en el pool de procesos
        result = process_pool.apply_async(
            process_screenshot,
            args=(url, max_width, max_height)
        )

        # Esperar resultado (con timeout)
        try:
            return result.get(timeout=60)
        except Exception as e:
            logger.error(f"Error al obtener resultado de screenshot: {e}")
            return {'success': False, 'error': str(e)}

    def _process_performance(self, params: dict) -> dict:
        """Procesa una request de análisis de rendimiento."""
        url = params.get('url')
        html = params.get('html')

        if not url:
            return {'success': False, 'error': 'URL requerida'}

        logger.info(f"Procesando rendimiento: {url}")

        # Ejecutar en el pool de procesos
        result = process_pool.apply_async(
            process_performance,
            args=(url, html)
        )

        # Esperar resultado
        try:
            return result.get(timeout=60)
        except Exception as e:
            logger.error(f"Error al obtener resultado de performance: {e}")
            return {'success': False, 'error': str(e)}

    def _process_images(self, params: dict) -> dict:
        """Procesa una request de procesamiento de imágenes."""
        image_urls = params.get('image_urls', [])
        max_images = params.get('max_images', 5)

        if not image_urls:
            return {'success': True, 'thumbnails': [], 'processed_count': 0}

        logger.info(f"Procesando {len(image_urls)} imágenes (max {max_images})")

        # Ejecutar en el pool de procesos
        result = process_pool.apply_async(
            process_images_task,
            args=(image_urls, max_images)
        )

        # Esperar resultado
        try:
            return result.get(timeout=60)
        except Exception as e:
            logger.error(f"Error al obtener resultado de images: {e}")
            return {'success': False, 'error': str(e)}

    def _process_all(self, params: dict) -> dict:
        """
        Procesa múltiples operaciones en paralelo.

        Args:
            params: Diccionario con parámetros

        Returns:
            Diccionario con todos los resultados
        """
        url = params.get('url')
        html = params.get('html')
        image_urls = params.get('image_urls', [])

        if not url:
            return {'success': False, 'error': 'URL requerida'}

        logger.info(f"Procesando todas las operaciones para {url}")

        # Ejecutar todas las operaciones en paralelo
        screenshot_result = process_pool.apply_async(
            process_screenshot,
            args=(url, 1280, 720)
        )

        performance_result = process_pool.apply_async(
            process_performance,
            args=(url, html)
        )

        images_result = process_pool.apply_async(
            process_images_task,
            args=(image_urls, 5)
        )

        # Esperar todos los resultados
        try:
            screenshot_data = screenshot_result.get(timeout=60)
            performance_data = performance_result.get(timeout=60)
            images_data = images_result.get(timeout=60)

            return {
                'success': True,
                'screenshot': screenshot_data,
                'performance': performance_data,
                'images': images_data
            }

        except Exception as e:
            logger.error(f"Error al obtener resultados: {e}")
            return {'success': False, 'error': str(e)}

    def _send_error(self, error_message: str):
        """Envía un mensaje de error al cliente."""
        try:
            response = create_response(False, error=error_message)
            response_data = serialize_json(response)
            send_message(self.request, response_data)
        except Exception as e:
            logger.error(f"Error al enviar mensaje de error: {e}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Servidor TCP que maneja cada conexión en un thread separado.

    ThreadingMixIn permite manejar múltiples clientes concurrentemente.
    """
    allow_reuse_address = True
    daemon_threads = True


def init_process_pool(num_processes: int) -> None:
    """
    Inicializa el pool de procesos.

    Args:
        num_processes: Número de procesos en el pool
    """
    global process_pool

    if process_pool is not None:
        logger.warning("Pool de procesos ya inicializado")
        return

    logger.info(f"Inicializando pool de procesos con {num_processes} workers")
    process_pool = Pool(processes=num_processes)


def cleanup_process_pool() -> None:
    """Cierra el pool de procesos."""
    global process_pool

    if process_pool:
        logger.info("Cerrando pool de procesos")
        process_pool.close()
        process_pool.join()
        process_pool = None


def signal_handler(signum, frame):
    """Handler para señales de terminación."""
    logger.info(f"Señal {signum} recibida, cerrando servidor...")
    cleanup_process_pool()
    sys.exit(0)


def parse_arguments():
    """
    Parsea argumentos de línea de comandos.

    Returns:
        Namespace con los argumentos
    """
    parser = argparse.ArgumentParser(
        description='Servidor de Procesamiento Distribuido',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s -i 127.0.0.1 -p 8001
  %(prog)s -i :: -p 8001 -n 8
  %(prog)s -i 0.0.0.0 -p 8001 -n 4 --debug
        """
    )

    parser.add_argument(
        '-i', '--ip',
        required=True,
        help='Dirección de escucha (IPv4 o IPv6)'
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        required=True,
        help='Puerto de escucha'
    )

    parser.add_argument(
        '-n', '--processes',
        type=int,
        default=cpu_count(),
        help=f'Número de procesos en el pool (default: {cpu_count()})'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Activar modo debug'
    )

    return parser.parse_args()


def main():
    """Función principal."""
    args = parse_arguments()

    # Configurar logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Registrar signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Inicializar pool de procesos
    init_process_pool(args.processes)

    # Crear servidor
    try:
        logger.info(f"Iniciando servidor de procesamiento en {args.ip}:{args.port}")
        logger.info(f"Pool de procesos: {args.processes} workers")

        server = ThreadedTCPServer((args.ip, args.port), ProcessingRequestHandler)

        logger.info("Servidor listo para recibir conexiones")

        # Ejecutar servidor
        server.serve_forever()

    except KeyboardInterrupt:
        logger.info("Servidor interrumpido por el usuario")

    except Exception as e:
        logger.error(f"Error al iniciar servidor: {e}", exc_info=True)
        return 1

    finally:
        cleanup_process_pool()

    return 0


if __name__ == '__main__':
    sys.exit(main())
