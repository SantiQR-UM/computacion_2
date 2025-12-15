# Arquitectura del Sistema

## Nodos y Conectividad

### Componentes principales

```
┌─────────────┐     TCP (IPv4/IPv6)       ┌──────────────────┐
│   Cliente   │ ─────────────────────────>│   Servidor       │
│     CLI     │                           │   Asíncrono      │
│  (argparse) │ <─────────────────────────│   (asyncio)      │
└─────────────┘                           └──────────────────┘
                                                   │
                                                   │ Celery tasks
                                                   │ (Redis broker)
                                                   ▼
                                          ┌─────────────────┐
                                          │  Workers Pool   │
                                          │   (Celery)      │
                                          │                 │
                                          │ Worker 1 │ ...  │
                                          │ Worker 2 │      │
                                          │ Worker N │      │
                                          └─────────────────┘
                                                   │
                                                   │ Escriben frames
                                                   ▼
                                          ┌─────────────────┐
                                          │ Volumen Docker  │
                                          │  Compartido     │
                                          │ /app/data/      │
                                          │   frames/       │
                                          └─────────────────┘
                                                   ▲
                                                   │ Polling asíncrono
                                                   │
                                          ┌────────┴─────────┐
                                          │                  │
                                     Servidor           Preview HTTP
                                     (lee frames)       (sirve frames)
```

### Conexiones

- **Cliente CLI** → **Servidor Asíncrono**: **TCP dual-stack** (`AF_INET6` con `IPV6_V6ONLY=0`), puerto configurable (default: 9090)
- **Servidor** → **Workers**: **Celery** con **Redis** como broker (solo tareas, NO result backend)
- **Workers** → **Filesystem Compartido**: Escriben frames procesados a `/app/data/frames/{session_id}/`
- **Servidor** ← **Filesystem Compartido**: Polling paralelo con `ThreadPoolExecutor` (8 workers) esperando frames
- **Preview HTTP** ← **Filesystem Compartido**: Lee frames para servir vía HTTP
- **Servidor (local)**: `concurrent.futures.ThreadPoolExecutor` para:
  1. Polling paralelo de frames procesados (FrameCollector, 8 workers)
  2. Escritura I/O-bound del video (VideoWriter, 1 worker)
- **Servidor (preview)**: Contenedor separado con Flask + SSE en puerto 8080

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

### 2. Procesamiento distribuido (filesystem compartido)

```
Servidor                Redis (broker)          Workers              Filesystem Compartido
   │                         │                      │                        │
   │─ dispatch task 0 ──────>│                      │                        │
   │─ dispatch task 1 ──────>│                      │                        │
   │─ dispatch task 2 ──────>│                      │                        │
   │                         │                      │                        │
   │                         │<──── consume task ───│ Worker 1               │
   │                         │<──── consume task ───│ Worker 2               │
   │                         │<──── consume task ───│ Worker 3               │
   │                         │                      │                        │
   │                         │                      │ process_frame(0)       │
   │                         │                      │ process_frame(1)       │
   │                         │                      │ process_frame(2)       │
   │                         │                      │                        │
   │                         │                      │─ write frame_000000.png ──>│
   │                         │                      │─ write frame_000000.json ──>│
   │                         │                      │─ write frame_000001.png ──>│
   │                         │                      │─ write frame_000001.json ──>│
   │                         │                      │─ write frame_000002.png ──>│
   │                         │                      │─ write frame_000002.json ──>│
   │                         │                      │                        │
   │<─ polling: wait_for_frame(0) ────────────────────────────────────────────│
   │<─ polling: wait_for_frame(1) ────────────────────────────────────────────│
   │<─ polling: wait_for_frame(2) ────────────────────────────────────────────│
   │  (asyncio.sleep cada 100ms)                                              │
```

**NOTA IMPORTANTE**: Los workers NO devuelven resultados vía Celery result backend. En su lugar, escriben los frames procesados directamente al filesystem compartido (`/app/data/frames/{session_id}/`) y el servidor hace polling asíncrono esperando que aparezcan los archivos.

### 3. Reconstrucción y envío

```
Servidor                Cliente
   │                       │
   │─ read frames from     │
   │   shared volume       │
   │─ mux frames ─────────>│
   │─ write MP4 in         │
   │   ThreadPoolExecutor  │
   │                       │
   │──── result JSON ─────>│
   │──── output.mp4 ──────>│
```

## Mecanismos de IPC

### Entre procesos locales
- `concurrent.futures.ThreadPoolExecutor` para tareas I/O-bound:
  - **Polling paralelo de frames** (`FrameCollector`, 8 workers): Espera que múltiples frames aparezcan en disco simultáneamente
  - **Escritura de video** (`VideoWriter`, 1 worker): Escribe frames a disco sin bloquear event loop
- `Lock` para secciones críticas (buffer de salida)

### Entre nodos distribuidos
- **Redis** (Celery) como cola distribuida de tareas (SOLO broker, NO result backend)
- **TCP sockets** para comunicación cliente-servidor
- **Filesystem compartido** (volumen Docker `video_data`) para intercambio de frames procesados:
  - Workers escriben frames a `/app/data/frames/{session_id}/frame_XXXXXX.png`
  - Workers escriben estadísticas a `/app/data/frames/{session_id}/frame_XXXXXX.json`
  - Servidor hace polling paralelo con `FrameCollector` (ThreadPoolExecutor con 8 workers, check cada 100ms, timeout 5min)
  - Callbacks en tiempo real actualizan Redis con progreso, FPS y ETA
  - Preview HTTP lee frames del mismo volumen

## Sincronización

- **Semáforos**: limitar frames concurrentes en procesamiento
- **Rate limiting** Celery: evitar saturación de workers (ej: 64 frames/s)
- **Locks**: proteger escritura concurrente al archivo de salida

## Tolerancia a Fallos

- **Reintentos Celery**: exponential backoff si falla procesamiento de frame
- **Fallback**: si un frame no se procesa, usar frame original y marcar en métricas
- **Timeouts**: límites de tiempo para procesamiento de cada frame (5 minutos por frame en el polling)
- **Timeouts en polling**: `wait_for_frame()` espera hasta 5 minutos antes de declarar un frame como perdido

## Decisión Arquitectónica Clave: Filesystem Compartido vs Redis Result Backend

### Problema Original
La arquitectura inicial contemplaba usar Redis como result backend de Celery para devolver frames procesados. Sin embargo, al escalar a videos de 300+ frames, se detectaron errores críticos:
- `InvalidResponse: Protocol Error` en Redis
- Corrupción/truncamiento de mensajes JSON
- Problemas persistentes incluso aumentando memoria Redis a 8GB y cambiando serialización

### Solución Implementada
Se reemplazó el Redis result backend por un **sistema basado en filesystem compartido**:

**Funcionamiento:**
1. Workers procesan frames y escriben resultados a disco (`/app/data/frames/{session_id}/`)
2. Cada frame genera dos archivos:
   - `frame_XXXXXX.png`: Frame procesado
   - `frame_XXXXXX.json`: Estadísticas (tiempo, memoria, filtro, worker)
3. Servidor hace polling asíncrono con `wait_for_frame()`:
   - Verifica existencia de archivos cada 100ms usando `asyncio.sleep()`
   - Timeout de 5 minutos por frame
   - Lee frame y estadísticas cuando ambos archivos existen

**Ventajas:**
- ✅ Resuelve problemas de escala (maneja 300+ frames sin corrupciones)
- ✅ Simplicidad en configuración (Redis solo como broker)
- ✅ Debugging facilitado (frames visibles en filesystem)
- ✅ Sin límites de memoria Redis
- ✅ Persistencia automática de resultados

**Desventajas:**
- ❌ Requiere volumen compartido Docker
- ❌ Polling menos eficiente que notificaciones push
- ❌ Requiere limpieza manual de frames antiguos

**Docker Compose:**
```yaml
volumes:
  video_data:  # Volumen compartido entre server, workers y preview

services:
  server:
    volumes:
      - video_data:/app/data
  worker:
    volumes:
      - video_data:/app/data
  preview:
    volumes:
      - video_data:/app/data
```

Esta decisión prioriza **funcionalidad y confiabilidad** sobre elegancia arquitectónica. Ver `INFO.md` sección 16 para detalles completos.
