#!/usr/bin/env python3
"""
Cliente de prueba para el sistema de scraping distribuido.

Este cliente permite probar el servidor de scraping enviando requests
y mostrando las respuestas de forma legible.

Uso:
    python client.py http://localhost:8000 https://example.com
    python client.py http://localhost:8000 https://www.python.org --save output.json
"""

import argparse
import sys
import json
import requests
from datetime import datetime
from typing import Optional


class ScrapingClient:
    """Cliente para el servidor de scraping."""

    def __init__(self, server_url: str, timeout: int = 120):
        """
        Inicializa el cliente.

        Args:
            server_url: URL base del servidor (ej: http://localhost:8000)
            timeout: Timeout en segundos
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout

    def scrape(self, url: str) -> dict:
        """
        Realiza una request de scraping.

        Args:
            url: URL a scrapear

        Returns:
            Diccionario con la respuesta

        Raises:
            Exception: Si hay un error en la request
        """
        endpoint = f"{self.server_url}/scrape"
        params = {'url': url}

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Solicitando scraping de: {url}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Timeout: {self.timeout}s")
        print()

        try:
            start_time = datetime.now()

            response = requests.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )

            elapsed = (datetime.now() - start_time).total_seconds()

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Respuesta recibida en {elapsed:.2f}s")
            print(f"  Status Code: {response.status_code}")
            print()

            if response.status_code != 200:
                print(f"ERROR: HTTP {response.status_code}")
                print(response.text)
                raise Exception(f"HTTP {response.status_code}")

            return response.json()

        except requests.Timeout:
            raise Exception(f"Timeout después de {self.timeout}s")
        except requests.RequestException as e:
            raise Exception(f"Error de request: {e}")

    def health_check(self) -> dict:
        """
        Verifica el estado del servidor.

        Returns:
            Diccionario con el estado
        """
        endpoint = f"{self.server_url}/health"

        try:
            response = requests.get(endpoint, timeout=5)

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP {response.status_code}")

        except Exception as e:
            raise Exception(f"Health check falló: {e}")


def print_response(data: dict) -> None:
    """
    Imprime la respuesta de forma legible.

    Args:
        data: Diccionario con la respuesta
    """
    print("=" * 80)
    print("RESULTADO DEL SCRAPING")
    print("=" * 80)
    print()

    # Información básica
    print(f"URL:       {data.get('url', 'N/A')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print(f"Status:    {data.get('status', 'N/A')}")
    print()

    # Datos de scraping
    if 'scraping_data' in data:
        scraping = data['scraping_data']

        print("-" * 80)
        print("SCRAPING DATA")
        print("-" * 80)
        print()

        print(f"Título: {scraping.get('title', 'N/A')}")
        print()

        # Estructura
        if 'structure' in scraping:
            print("Estructura de Headers:")
            for tag, count in scraping['structure'].items():
                if count > 0:
                    print(f"  {tag.upper()}: {count}")
            print()

        # Meta tags
        if 'meta_tags' in scraping and scraping['meta_tags']:
            print("Meta Tags:")
            for key, value in scraping['meta_tags'].items():
                # Truncar valores largos
                value_str = value[:100] + '...' if len(value) > 100 else value
                print(f"  {key}: {value_str}")
            print()

        # Links
        if 'links' in scraping:
            num_links = len(scraping['links'])
            print(f"Enlaces encontrados: {num_links}")
            if num_links > 0:
                print("  Primeros 5 enlaces:")
                for link in scraping['links'][:5]:
                    print(f"    - {link}")
            print()

        # Imágenes
        images_count = scraping.get('images_count', 0)
        print(f"Imágenes encontradas: {images_count}")
        print()

    # Datos de procesamiento
    if 'processing_data' in data:
        processing = data['processing_data']

        print("-" * 80)
        print("PROCESSING DATA")
        print("-" * 80)
        print()

        # Screenshot
        if processing.get('screenshot'):
            screenshot_size = len(processing['screenshot'])
            print(f"Screenshot: ✓ ({screenshot_size} caracteres base64)")
        else:
            print("Screenshot: ✗")
        print()

        # Performance
        if 'performance' in processing and processing['performance']:
            perf = processing['performance']
            print("Performance:")
            if perf.get('load_time_ms'):
                print(f"  Tiempo de carga: {perf['load_time_ms']} ms")
            if perf.get('total_size_kb'):
                print(f"  Tamaño total: {perf['total_size_kb']:.2f} KB")
            if perf.get('num_requests'):
                print(f"  Número de requests: {perf['num_requests']}")
            print()

        # Thumbnails
        if 'thumbnails' in processing:
            num_thumbnails = len(processing['thumbnails'])
            print(f"Thumbnails generados: {num_thumbnails}")
            print()

        # Error
        if 'error' in processing:
            print(f"Error en procesamiento: {processing['error']}")
            print()

    print("=" * 80)


def save_response(data: dict, filename: str) -> None:
    """
    Guarda la respuesta en un archivo JSON.

    Args:
        data: Diccionario con la respuesta
        filename: Nombre del archivo
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Respuesta guardada en: {filename}")


def parse_arguments():
    """
    Parsea argumentos de línea de comandos.

    Returns:
        Namespace con los argumentos
    """
    parser = argparse.ArgumentParser(
        description='Cliente de prueba para el servidor de scraping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s http://localhost:8000 https://example.com
  %(prog)s http://localhost:8000 https://www.python.org --save output.json
  %(prog)s http://localhost:8000 https://github.com --timeout 180
  %(prog)s http://localhost:8000 --health
        """
    )

    parser.add_argument(
        'server',
        help='URL del servidor de scraping (ej: http://localhost:8000)'
    )

    parser.add_argument(
        'url',
        nargs='?',
        help='URL a scrapear'
    )

    parser.add_argument(
        '--save',
        metavar='FILE',
        help='Guardar respuesta en archivo JSON'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Timeout en segundos (default: 120)'
    )

    parser.add_argument(
        '--health',
        action='store_true',
        help='Solo verificar el estado del servidor'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Mostrar respuesta en formato JSON crudo'
    )

    return parser.parse_args()


def main():
    """Función principal."""
    args = parse_arguments()

    # Crear cliente
    client = ScrapingClient(args.server, timeout=args.timeout)

    try:
        # Health check
        if args.health:
            print(f"Verificando estado del servidor: {args.server}")
            health = client.health_check()
            print(f"Estado: {health.get('status')}")
            print(f"Timestamp: {health.get('timestamp')}")
            return 0

        # Validar que se proporcionó URL
        if not args.url:
            print("ERROR: Debe proporcionar una URL a scrapear")
            print("Use --help para ver opciones")
            return 1

        # Realizar scraping
        result = client.scrape(args.url)

        # Mostrar resultado
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print_response(result)

        # Guardar si se solicitó
        if args.save:
            save_response(result, args.save)

        return 0

    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario")
        return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
