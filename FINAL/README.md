# Sistema Distribuido de Procesamiento de Video por Frames

Sistema cliente-servidor que procesa videos aplicando filtros de OpenCV de manera distribuida usando Celery, Redis y asyncio.

## Descripción

Este proyecto implementa un sistema de procesamiento de video que:

- Recibe videos de clientes vía TCP (IPv4/IPv6 dual-stack)
- Extrae frames usando OpenCV
- Distribuye el procesamiento a múltiples workers usando Celery
- Aplica filtros de procesamiento de imagen (blur, detección de rostros, bordes, movimiento)
- Reensambla el video procesado y lo devuelve al cliente
- Reporta métricas detalladas de performance

## Características

- **TCP Dual-Stack**: Soporta IPv4 e IPv6 simultáneamente
- **Procesamiento Distribuido**: Workers escalables con Celery + Redis
- **Asincronismo**: Servidor asíncrono con asyncio
- **Múltiples Filtros**: Blur, detección de rostros, bordes, movimiento
- **Métricas en Tiempo Real**: FPS, latencias (p50, p95, p99), reintentos
- **Tolerancia a Fallos**: Reintentos automáticos, fallback a frame original
- **Despliegue Docker**: Orquestación completa con docker-compose

## Requisitos

- Python 3.11+
- Docker y Docker Compose (para despliegue en contenedores)
- Redis 7+
- OpenCV 4.8+

## Instalación Rápida

```bash
# Clonar repositorio
git clone <url>
cd FINAL

# Lanzar con Docker
cd docker
docker-compose up --build

# En otra terminal, ejecutar cliente
pip install -r requirements.txt
python src/client.py --host localhost --video input.mp4 --processing blur --out output.mp4
```

Ver [INSTALL.md](INSTALL.md) para instrucciones detalladas.

## Uso

### Servidor

```bash
python src/server.py [opciones]

Opciones:
  --bind ADDR        Dirección de bind (default: ::)
  --port PORT        Puerto TCP (default: 9090)
  --preview-port     Puerto HTTP preview (default: 8080)
  --codec CODEC      Codec de salida (default: mp4v)
```

### Workers

```bash
celery -A src.worker.app worker --loglevel=INFO -Q frames -n worker1@%h
```

### Cliente

```bash
python src/client.py [opciones]

Opciones requeridas:
  --video PATH       Video de entrada

Opciones de conexión:
  --host HOST        Dirección del servidor (default: ::1)
  --port PORT        Puerto (default: 9090)
  --ipv6             Forzar IPv6
  --ipv4             Forzar IPv4

Opciones de procesamiento:
  --processing TYPE  Tipo: blur, faces, edges, motion (default: blur)
  --codec CODEC      Codec de salida (default: mp4v)
  --out PATH         Video de salida (default: output.mp4)
```

## Ejemplos

### Blur (Gaussian)

```bash
python src/client.py --host ::1 --ipv6 --video input.mp4 --processing blur --out blurred.mp4
```

### Detección de Rostros

```bash
python src/client.py --host 127.0.0.1 --ipv4 --video input.mp4 --processing faces --out faces.mp4
```

### Detección de Bordes (Canny)

```bash
python src/client.py --video input.mp4 --processing edges --out edges.mp4
```

### Detección de Movimiento

```bash
python src/client.py --video input.mp4 --processing motion --out motion.mp4
```

## Arquitectura

```
Cliente (TCP) → Servidor (asyncio) → Redis (Celery) → Workers (OpenCV)
                     ↓
                 Muxer (ThreadPoolExecutor)
                     ↓
                 Video procesado → Cliente
```

Ver [doc/ARQUITECTURA.md](doc/ARQUITECTURA.md) para detalles.

## Tecnologías Utilizadas

- **Python 3.11**: Lenguaje principal
- **asyncio**: Servidor asíncrono
- **Celery**: Cola de tareas distribuidas
- **Redis**: Broker y backend para Celery
- **OpenCV**: Procesamiento de video y filtros
- **Docker**: Contenerización y orquestación
- **argparse**: Parseo de argumentos CLI
- **concurrent.futures**: ThreadPoolExecutor para I/O-bound
- **psutil**: Métricas de sistema

## Temas de la Materia Aplicados

- Git: Control de versiones
- E/S Unix: Descriptores, redirecciones
- Argumentos: argparse con validaciones
- Procesos: Celery workers como procesos separados
- Pipes/FIFOs: Comunicación interproceso (opcional)
- Concurrencia: asyncio para I/O concurrente
- Paralelismo: Celery workers para procesamiento CPU-bound
- Threading: ThreadPoolExecutor para escritura de video
- Docker: Despliegue en contenedores
- Redes: TCP dual-stack (IPv4/IPv6)
- Sockets: Comunicación cliente-servidor
- HTTP: Servidor de preview (futuro)
- IPv6: Dual-stack con IPV6_V6ONLY=0
- Asyncio: Event loop, async/await
- concurrent.futures: Abstracciones de paralelismo
- Celery: Tareas distribuidas, reintentos, rate limiting

## Métricas Reportadas

- Frames procesados / total
- FPS de procesamiento
- Latencias (p50, p95, p99)
- Tiempo total de procesamiento
- Reintentos
- Cantidad de workers activos
- Filtros aplicados

## Estructura del Proyecto

```
FINAL/
├── doc/                    # Documentación de diseño
│   ├── DESCRIPCION.md
│   ├── ARQUITECTURA.md
│   ├── FUNCIONALIDADES.md
│   └── PROTOCOLO.md
├── src/                    # Código fuente
│   ├── client.py          # Cliente CLI
│   ├── server.py          # Servidor asíncrono
│   ├── worker.py          # Worker de Celery
│   ├── filters/           # Filtros de OpenCV
│   │   ├── blur.py
│   │   ├── edges.py
│   │   ├── faces.py
│   │   └── motion.py
│   ├── protocol/          # Protocolo de mensajes
│   │   └── messages.py
│   ├── storage/           # Escritor de video
│   │   └── writer.py
│   └── metrics/           # Recolección de métricas
│       └── stats.py
├── docker/                 # Archivos Docker
│   ├── Dockerfile.server
│   ├── Dockerfile.worker
│   └── docker-compose.yml
├── README.md              # Este archivo
├── INSTALL.md             # Instrucciones de instalación
├── INFO.md                # Decisiones de diseño
├── TODO.md                # Mejoras futuras
└── requirements.txt       # Dependencias Python
```

## Autor

Proyecto desarrollado para el examen final de Computación II.

## Licencia

MIT
