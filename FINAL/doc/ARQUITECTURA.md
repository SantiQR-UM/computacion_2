# Arquitectura del Sistema

## Nodos y Conectividad

### Componentes principales

```
┌─────────────┐     TCP (IPv4/IPv6)      ┌──────────────────┐
│   Cliente   │ ─────────────────────────>│   Servidor       │
│     CLI     │                           │   Asíncrono      │
│  (argparse) │ <─────────────────────────│   (asyncio)      │
└─────────────┘                           └──────────────────┘
                                                   │
                                                   │ Celery
                                                   │ (Redis)
                                                   ▼
                                          ┌─────────────────┐
                                          │  Workers Pool   │
                                          │   (Celery)      │
                                          │                 │
                                          │ Worker 1 │ ... │
                                          │ Worker 2 │     │
                                          │ Worker N │     │
                                          └─────────────────┘
```

### Conexiones

- **Cliente CLI** → **Servidor Asíncrono**: **TCP dual-stack** (`AF_INET6` con `IPV6_V6ONLY=0`), puerto configurable (default: 9090)
- **Servidor** → **Workers**: **Celery** con **Redis** como broker y backend
- **Servidor (local)**: `concurrent.futures.ThreadPoolExecutor` para escritura I/O-bound del video
- **Servidor (preview)**: `http.server` para exponer métricas y frames
- **Opcional**: **AF_UNIX** para IPC en el mismo host y **FIFOs** nombradas para pipeline offline

## Dimensionamiento (máquina con 12 hilos lógicos)

- **1 hilo**: Cliente CLI
- **1 hilo**: Servidor asíncrono (event loop + orquestación)
- **8 hilos**: Workers Celery CPU-bound (procesamiento de frames)
- **2 hilos**: Libres para SO, Redis y tareas interactivas

## Flujo de Datos

### 1. Negociación y envío

```
Cliente                     Servidor
   │                           │
   │──── handshake ────────────>│
   │<─── ack ──────────────────│
   │                           │
   │──── stream video ─────────>│
   │     (chunks TCP)           │
```

### 2. Procesamiento distribuido

```
Servidor                Workers
   │                       │
   │─ extract frame 0 ────>│ Worker 1: process_frame(0, "blur")
   │─ extract frame 1 ────>│ Worker 2: process_frame(1, "blur")
   │─ extract frame 2 ────>│ Worker 3: process_frame(2, "blur")
   │                       │
   │<── frame 0 processed ─│
   │<── frame 1 processed ─│
   │<── frame 2 processed ─│
```

### 3. Reconstrucción y envío

```
Servidor                Cliente
   │                       │
   │─ mux frames ─────────>│
   │─ write MP4            │
   │                       │
   │──── result JSON ─────>│
   │──── output.mp4 ──────>│
```

## Mecanismos de IPC

### Entre procesos locales
- `concurrent.futures` para tareas I/O-bound (escritura de video)
- `multiprocessing.Queue` / `Pipe` (opcional, para subdivisión interna de frames)
- `Lock` para secciones críticas (buffer de salida)

### Entre nodos
- **Redis** (Celery) como cola distribuida y result backend
- **TCP sockets** para comunicación cliente-servidor

### Opcional
- **FIFOs** (`mkfifo`) para integrar `ffmpeg` por shell

## Sincronización

- **Semáforos**: limitar frames concurrentes en procesamiento
- **Rate limiting** Celery: evitar saturación de workers (ej: 64 frames/s)
- **Locks**: proteger escritura concurrente al archivo de salida

## Tolerancia a Fallos

- **Reintentos Celery**: exponential backoff si falla procesamiento de frame
- **Fallback**: si un frame no se procesa, usar frame original y marcar en métricas
- **Timeouts**: límites de tiempo para procesamiento de cada frame
