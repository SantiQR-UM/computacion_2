# TP2 - Sistema de Scraping y Análisis Web Distribuido

## Descripción del Proyecto

Sistema distribuido de scraping y análisis web implementado en Python que utiliza dos servidores trabajando de forma coordinada:

- **Servidor A (asyncio)**: Servidor HTTP asíncrono que maneja scraping web de forma no bloqueante
- **Servidor B (multiprocessing)**: Servidor de procesamiento que ejecuta tareas CPU-bound en paralelo

El sistema extrae información completa de páginas web incluyendo contenido HTML, metadatos, screenshots, análisis de rendimiento y procesamiento de imágenes, todo de forma distribuida y transparente para el cliente.

## Características Implementadas

### Parte A: Servidor de Scraping Asíncrono ✓

- Servidor HTTP asíncrono con `aiohttp`
- Scraping no bloqueante con `asyncio`
- Extracción de:
  - Título de la página
  - Enlaces (links)
  - Meta tags (description, keywords, Open Graph, Twitter Cards)
  - Estructura de headers (H1-H6)
  - Conteo y URLs de imágenes
- Comunicación asíncrona con servidor de procesamiento
- Respuestas JSON consolidadas
- Soporte IPv4 e IPv6

### Parte B: Servidor de Procesamiento con Multiprocessing ✓

- Servidor TCP con `socketserver.ThreadingMixIn`
- Pool de procesos con `multiprocessing.Pool`
- Operaciones CPU-bound:
  - **Screenshots**: Captura de pantalla de páginas web con Selenium/Playwright
  - **Análisis de rendimiento**: Tiempo de carga, tamaño de recursos, número de requests
  - **Procesamiento de imágenes**: Descarga y generación de thumbnails optimizados
- Protocolo binario eficiente con serialización JSON
- Procesamiento paralelo de múltiples operaciones

### Parte C: Transparencia para el Cliente ✓

- El cliente solo interactúa con el Servidor A
- Coordinación automática entre servidores
- Respuesta única consolidada
- Manejo transparente de errores

## Estructura del Proyecto

```
TP2/
├── server_scraping.py           # Servidor asyncio (Parte A)
├── server_processing.py         # Servidor multiprocessing (Parte B)
├── client.py                    # Cliente de prueba
├── scraper/
│   ├── __init__.py
│   ├── async_http.py            # Cliente HTTP asíncrono
│   ├── html_parser.py           # Parser de HTML con BeautifulSoup
│   └── metadata_extractor.py    # Extractor de metadatos
├── processor/
│   ├── __init__.py
│   ├── screenshot.py            # Generación de screenshots
│   ├── performance.py           # Análisis de rendimiento
│   └── image_processor.py       # Procesamiento de imágenes
├── common/
│   ├── __init__.py
│   ├── protocol.py              # Protocolo de comunicación TCP
│   └── serialization.py         # Serialización JSON/Pickle
├── tests/
│   ├── __init__.py
│   ├── test_serialization.py   # Tests de serialización
│   ├── test_protocol.py         # Tests de protocolo
│   ├── test_html_parser.py      # Tests de parsing HTML
│   └── test_integration.py      # Tests de integración
├── requirements.txt             # Dependencias
├── README.md                    # Especificación del TP
└── README_TP2.md               # Este archivo
```

## Instalación

### 1. Clonar el repositorio

```bash
cd TP2
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar ChromeDriver para screenshots

**Opción 1: ChromeDriver (Selenium)**

- Descargar ChromeDriver desde: https://chromedriver.chromium.org/
- Agregar ChromeDriver al PATH del sistema
- Verificar: `chromedriver --version`

**Opción 2: Playwright (Alternativa)**

```bash
pip install playwright
playwright install chromium
```

## Uso

### Iniciar los Servidores

#### 1. Servidor de Procesamiento (Parte B)

```bash
python server_processing.py -i 127.0.0.1 -p 8001 -n 4
```

Opciones:
- `-i, --ip`: Dirección de escucha (IPv4 o IPv6)
- `-p, --port`: Puerto de escucha
- `-n, --processes`: Número de procesos en el pool (default: CPU count)
- `--debug`: Modo debug con logging verbose

Ejemplos:
```bash
# IPv4
python server_processing.py -i 127.0.0.1 -p 8001

# IPv6
python server_processing.py -i :: -p 8001

# Con 8 procesos
python server_processing.py -i 0.0.0.0 -p 8001 -n 8
```

#### 2. Servidor de Scraping (Parte A)

```bash
python server_scraping.py -i 127.0.0.1 -p 8000 --processing-host 127.0.0.1 --processing-port 8001
```

Opciones:
- `-i, --ip`: Dirección de escucha (soporta IPv4/IPv6)
- `-p, --port`: Puerto de escucha
- `-w, --workers`: Número de workers (default: 4)
- `--processing-host`: Host del servidor de procesamiento
- `--processing-port`: Puerto del servidor de procesamiento
- `--debug`: Modo debug

Ejemplos:
```bash
# Configuración básica
python server_scraping.py -i 127.0.0.1 -p 8000

# IPv6 con servidor de procesamiento remoto
python server_scraping.py -i :: -p 8000 --processing-host 192.168.1.100 --processing-port 8001

# Con debug
python server_scraping.py -i 0.0.0.0 -p 8000 --debug
```

### Usar el Cliente

```bash
python client.py http://localhost:8000 https://example.com
```

Opciones:
- `--save FILE`: Guardar respuesta en archivo JSON
- `--timeout SECONDS`: Timeout en segundos (default: 120)
- `--health`: Solo verificar estado del servidor
- `--json`: Mostrar respuesta en formato JSON crudo

Ejemplos:
```bash
# Scraping básico
python client.py http://localhost:8000 https://www.python.org

# Guardar resultado
python client.py http://localhost:8000 https://github.com --save output.json

# Health check
python client.py http://localhost:8000 --health

# Con timeout personalizado
python client.py http://localhost:8000 https://example.com --timeout 180
```

### Usar con curl

```bash
# Scraping
curl "http://localhost:8000/scrape?url=https://example.com"

# Health check
curl "http://localhost:8000/health"
```

## Formato de Respuesta

El servidor devuelve un JSON con la siguiente estructura:

```json
{
  "url": "https://example.com",
  "timestamp": "2024-11-10T15:30:00Z",
  "scraping_data": {
    "title": "Example Domain",
    "links": ["https://www.iana.org/domains/example"],
    "meta_tags": {
      "description": "Example description",
      "og:title": "Example"
    },
    "structure": {
      "h1": 1,
      "h2": 0,
      "h3": 0
    },
    "images_count": 0,
    "images_urls": []
  },
  "processing_data": {
    "screenshot": "iVBORw0KGgoAAAANSUhEUg...",
    "performance": {
      "load_time_ms": 450,
      "total_size_kb": 1.2,
      "num_requests": 3
    },
    "thumbnails": ["base64_thumb1", "base64_thumb2"]
  },
  "status": "success"
}
```

## Testing

### Ejecutar Tests Unitarios

```bash
# Todos los tests
python -m pytest tests/ -v

# Test específico
python -m unittest tests.test_serialization
python -m unittest tests.test_protocol
python -m unittest tests.test_html_parser
```

### Ejecutar Tests de Integración

**Importante**: Los tests de integración requieren que ambos servidores estén ejecutándose.

Terminal 1:
```bash
python server_processing.py -i 127.0.0.1 -p 8001
```

Terminal 2:
```bash
python server_scraping.py -i 127.0.0.1 -p 8000
```

Terminal 3:
```bash
python -m unittest tests.test_integration
```

## Arquitectura Técnica

### Comunicación entre Servidores

**Protocolo Binario:**
```
[4 bytes: longitud del mensaje][N bytes: payload JSON]
```

- Header: 4 bytes en big-endian (network byte order)
- Payload: JSON serializado en UTF-8
- Máximo por mensaje: 10 MB

**Formato de Mensajes:**

Request:
```json
{
  "type": "request",
  "operation": "screenshot|performance|images|all",
  "params": {
    "url": "https://example.com",
    "html": "...",
    "image_urls": [...]
  }
}
```

Response:
```json
{
  "type": "response",
  "success": true,
  "data": {...}
}
```

### Concurrencia y Paralelismo

**Servidor A (asyncio):**
- Event loop no bloqueante
- `aiohttp.ClientSession` para requests HTTP asíncronos
- `asyncio.open_connection` para comunicación con Servidor B
- Manejo asíncrono de múltiples clientes simultáneos

**Servidor B (multiprocessing):**
- `socketserver.ThreadingMixIn` para manejar múltiples conexiones
- `multiprocessing.Pool` para procesamiento paralelo
- Cada operación CPU-bound se ejecuta en un proceso separado
- Pool con tamaño configurable (default: número de CPUs)

### Manejo de Errores

El sistema implementa manejo robusto de errores:

- **URLs inválidas o inaccesibles**: Validación y respuesta HTTP 400
- **Timeouts**: 30s para scraping, 60s para procesamiento
- **Errores de comunicación**: Reintentos y mensajes de error descriptivos
- **Recursos no disponibles**: Manejo graceful con logging
- **Excepciones del servidor**: Captura y respuesta JSON con error

## Logging

Ambos servidores implementan logging detallado:

```
[2024-11-10 15:30:00] [INFO] [server_scraping] Iniciando servidor en 127.0.0.1:8000
[2024-11-10 15:30:15] [INFO] [scraper.async_http] GET https://example.com - Status: 200 - Time: 0.45s
[2024-11-10 15:30:16] [DEBUG] [common.protocol] Mensaje enviado: 1234 bytes
```

Niveles:
- **INFO**: Operaciones principales
- **DEBUG**: Detalles de comunicación (activar con `--debug`)
- **ERROR**: Errores y excepciones
- **WARNING**: Advertencias

## Buenas Prácticas Implementadas

### Código

- ✓ Documentación completa con docstrings
- ✓ Type hints en funciones principales
- ✓ Separación de concerns (módulos especializados)
- ✓ Manejo de excepciones específicas
- ✓ Logging estructurado
- ✓ Validación de inputs
- ✓ Context managers para recursos

### Seguridad

- ✓ Validación de URLs
- ✓ Timeouts en todas las operaciones
- ✓ Límites de tamaño de mensajes
- ✓ Sanitización de inputs
- ✓ Modo headless para browsers

### Performance

- ✓ I/O no bloqueante con asyncio
- ✓ Procesamiento paralelo con multiprocessing
- ✓ Connection pooling en cliente HTTP
- ✓ Compresión de imágenes (thumbnails)
- ✓ Límites de recursos procesados

### Testing

- ✓ Tests unitarios para módulos críticos
- ✓ Tests de integración end-to-end
- ✓ Cobertura de casos edge
- ✓ Validación de errores

## Limitaciones y Consideraciones

1. **Screenshots**: Requiere ChromeDriver o Playwright instalado
2. **Memoria**: Páginas muy grandes (>10 MB) pueden causar errores
3. **Timeout**: Páginas lentas pueden exceder el timeout de 30s
4. **Recursos**: El procesamiento de imágenes está limitado a 5 imágenes por request
5. **Concurrencia**: El número de workers debe ajustarse según recursos disponibles

## Troubleshooting

### Error: "ChromeDriver not found"

```bash
# Verificar instalación
chromedriver --version

# O usar Playwright
pip install playwright
playwright install chromium
```

### Error: "Connection refused"

- Verificar que el servidor de procesamiento esté ejecutándose
- Verificar que el puerto no esté en uso: `netstat -an | grep 8001`

### Error: "Timeout al procesar"

- Aumentar timeout en cliente: `--timeout 300`
- Verificar conectividad de red
- Probar con una URL más simple

### Alto uso de memoria

- Reducir número de procesos: `-n 2`
- Reducir número de workers: `-w 2`
- Limitar número de imágenes procesadas
