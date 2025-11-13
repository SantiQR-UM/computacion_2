# Sistema Distribuido de Procesamiento de Video por Frames

## 1) Descripción verbal (para `doc/DESCRIPCION.md`)

**Idea:**
Una app **cliente-servidor** donde el cliente envía un **video** (o la ruta al archivo) al servidor por **TCP dual-stack (IPv4/IPv6)**.
El servidor (asíncrono con `asyncio`) **demuxea** el video en **frames**, los **divide en tiles** y **distribuye** tareas de procesamiento a **workers** (locales y/o remotos) vía **Celery + Redis**.
Cada worker (CPU por defecto; opcional GPU) aplica un **pipeline de filtros** (p. ej. *canny edge, blur, detección de rostros, resaltado de movimiento*) usando `multiprocessing` internamente para paralelizar por **sub-tiles**.
Los resultados por frame se **reconstruyen** y se **re-ensambla** el video procesado (MP4) que el servidor retorna al cliente junto con un **JSON** con métricas (tiempo por frame, FPS efectivo, colas, porcentaje de tiles reintentados, etc).
Para debugging, el servidor expone un **HTTP simple** (`http.server`) con un **preview** (GIF o JPGs) y **métricas en tiempo real**.

**Problema que resuelve:**
Acelerar procesamientos pesados de video (filtrado, detección) distribuyendo trabajo entre procesos y nodos, mostrando dominio de concurrencia + asincronismo + IPC.

---

## 2) Arquitectura (para `doc/ARQUITECTURA.md`)

**Nodos y conectividad**

* **Cliente CLI** → **Servidor Asíncrono**: **TCP** (`AF_INET` dual-stack, `::`), puerto configurable.
* **Servidor** → **Workers**: **Celery** con **Redis** como *broker* y *backend* (opcional RabbitMQ).
* **Servidor (local)** → **Pool local**: `multiprocessing.Pool` + **Queues/Pipes** (IPC) para subtareas por tile.
* **Servidor (preview)**: `http.server`/`socketserver.ThreadingHTTPServer` para ver métricas/frames.
* **Opcional**: **AF_UNIX** para IPC en el mismo host y **FIFOs** nombradas para un pipeline offline (ej: `ffmpeg` → FIFO → `frame_ingestor.py`).

**Flujo de datos**

1. Cliente negocia parámetros y **sube el video** (stream) o envía sólo la **ruta** si comparte volumen.
2. Servidor lee asíncronamente (`asyncio.StreamReader`), **extrae frames** (OpenCV o `ffmpeg-python`) y los **divide en tiles** (NxM).
3. Por frame:

   * Encola **Ntiles** como **tareas Celery** (una por tile) con `task_id` y metadatos.
   * Cada worker procesa su tile (pipeline de filtros). Para filtros pesados, usa **`multiprocessing.Pool`** interno (sub-tiles).
   * Devuelve `ndarray`/bytes + métricas.
4. Servidor **reconstruye** el frame, lo **encola** para muxer (writer).
5. `muxer` (thread o proceso) escribe **MP4** (H.264) y genera **thumbnails** para preview.
6. Cliente recibe **archivo procesado** + **JSON** final con estadísticas agregadas.

**Mecanismos de IPC**

* **Entre procesos locales**: `multiprocessing.Queue`, `Pipe`, `Lock` para secciones críticas (buffer de salida).
* **Entre nodos**: **Redis** (Celery) como cola distribuida y *result backend*.
* **Opcional**: **FIFOs** (`mkfifo`) para integrar `ffmpeg` por shell (tema de *FIFOs en Unix*).

**Sincronización**

* **Semáforos** para limitar tiles concurrentes por frame.
* **Rate limiting** de tareas Celery (p. ej. 64 tiles/s) para no saturar workers.

**Tolerancia a fallos**

* **Reintentos** Celery con *exponential backoff* si un tile falla.
* Si un tile no llega, el servidor rellena con el **tile original** y marca en métricas (¡muestra robustez!).

---

## 3) Entidades y funcionalidades (para `doc/FUNCIONALIDADES.md`)

### Cliente (`client.py`)

* Parseo de args (`argparse`):
  `--host`, `--port`, `--ipv6/--ipv4`, `--video PATH`, `--codec h264`, `--tiles 2x2`, `--filters canny,blur:5`, `--out output.mp4`, `--preview`, `--protocol file|stream`.
* Envío del archivo o *stream* por **TCP** (chunked) con **checksum**.
* Barra de progreso y recepción de **JSON de resultados** + archivo final.

### Servidor (`server.py`)

* **`asyncio`** TCP server dual-stack (`socket.AF_INET6`, `IPV6_V6ONLY=0`): acepta múltiples clientes.
* **Dispatcher**: extracción de frames, **split en tiles**, envío a **Celery**.
* **Aggregator**: espera *futures* de Celery, **reconstruye** frame y lo envía al **muxer**.
* **Muxer**: escribe **MP4**; guarda **thumbnails** y **preview GIF** si se solicita.
* **HTTP Preview** (`http.server`): endpoint `/metrics`, `/frame/<n>`, `/gif`.
* Métricas: FPS entrada/salida, tiles/seg, reintentos, uso CPU por proceso, latencias.

### Worker (`worker.py`)

* Inicializa **Celery** (`celery[redis]`).
* **Tarea `process_tile`**: aplica pipeline configurable (canny, sobel, gaussian blur, umbral adaptativo, motion diff entre frames, etc.).
  *Dentro* usa `multiprocessing.Pool` para sub-tiles si el filtro es CPU-bound.
* Devuelve **bytes** del tile + **stats** (ms, RAM, filtro aplicado).

### Componentes de soporte

* **`filters/`**: módulo con filtros puros (facilita tests).
* **`protocol/`**: mensajes JSON (`handshake`, `job_descriptor`, `frame_n`, `end`).
* **`storage/`**: escritor de video (OpenCV `VideoWriter` o `ffmpeg-python`).
* **`metrics/`**: prom, p95 de latencias, contador de reintentos.

---

## 4) Argumentos y ejemplos de uso (para `README.md`)

### Servidor

```bash
# Redis
docker run -p 6379:6379 --name redis -d redis:7-alpine

# Workers (1 por contenedor, escalables)
celery -A worker.app worker --loglevel=INFO -Q tiles -n worker1@%h
celery -A worker.app worker --loglevel=INFO -Q tiles -n worker2@%h

# Servidor dual-stack + preview HTTP
python server.py --bind :: --port 9090 --preview-port 8080 --tiles 3x3 --filters canny,blur:3 --codec h264
```

### Cliente

```bash
python client.py --host ::1 --port 9090 --ipv6 \
  --video ./input.mp4 --tiles 3x3 --filters canny,blur:3 \
  --out ./output.mp4 --preview
```

---

## 5) Protocolo de mensajes (para `doc/PROTOCOLO.md`)

Mensajes en **JSON** con longitud prefijada (4 bytes big-endian) + payload:

* `handshake`: `{ "version":1, "mode":"stream|file", "codec":"h264", "tiles":[3,3], "filters":[["canny",{}],["blur",{"k":3}]] }`
* `frame`: `{ "seq":42, "pts":123456, "bytes":<bin> }`  *(el frame se manda binario en chunk aparte)*
* `eof`: `{ "total_frames": 1834 }`
* `result`: `{ "ok":true, "fps_out":23.4, "retries":12, "p95_ms":47, "output_path":"..." }`

---

## 6) Mapeo a los **temas** de la cursada (para `doc/INFO.md`)

* **Git**: repo con ramas `server/`, `client/`, `workers/`, PRs, tags.
* **E/S Unix**: descriptores, redirecciones (`ffmpeg` → FIFO), `os.read/os.write`.
* **Argumentos**: `argparse` completo con validaciones.
* **Procesos**: `fork/exec` explicado (en Linux), zombies/huérfanos en pruebas del muxer.
* **Pipes/FIFOs**: `multiprocessing.Pipe/Queue`; demo con `mkfifo` + `ffmpeg`.
* **Multiprocessing**: `Pool`, `Lock`, `Semaphore`.
* **Threading**: opcional `Thread` para muxer/preview I/O-bound.
* **Docker**: `Dockerfile` + `docker-compose.yml` (redis, workers, server).
* **Redes**: puertos, netcat/telnet para probar handshake.
* **Sockets**: TCP dual-stack, `AF_UNIX` opcional.
* **HTTP**: `http.server` para preview/metrics.
* **IPv6**: bind `::`, `IPV6_V6ONLY=0` para dual-stack.
* **Asyncio**: servidor y pipeline de ingestión/dispatch.
* **concurrent.futures**: `ThreadPoolExecutor` para escritura de video (I/O).
* **Celery**: `@app.task` con Redis broker/backend, `groups` por frame, reintentos, rate limiting.

---

## 7) Roadmap incremental (para `doc/TODO.md`)

1. **MVP local**: cliente↔servidor, extraer frames, **canny** en un solo proceso, escribir MP4.
2. **Tiles + multiprocessing** local (sin Celery).
3. **Celery + Redis**: distribuir tiles a 2 workers.
4. **Preview HTTP** + métricas básicas.
5. **IPv6 dual-stack** + pruebas con `nc -6`.
6. **FIFOs/AF_UNIX** demo (bonus IPC).
7. **Docker Compose** (redis, server, N workers).
8. **Filtros extra** (sobel, blur, motion, detección de rostros Haar).
9. **Refactor filtros** + tests.
10. **Pulido**: INSTALL.md, README con ejemplos, INFO.md con justificaciones.

---

## 8) Estructura de archivos sugerida

```
final/
  doc/
    DESCRIPCION.md
    ARQUITECTURA.md
    FUNCIONALIDADES.md
    PROTOCOLO.md
    INFO.md
    TODO.md
  src/
    client.py
    server.py
    worker.py
    filters/
      __init__.py
      canny.py
      blur.py
      sobel.py
      motion.py
    protocol/
      messages.py
    storage/
      writer.py
    metrics/
      stats.py
  docker/
    Dockerfile.server
    Dockerfile.worker
    docker-compose.yml
  README.md
  INSTALL.md
```

---

## 9) Justificaciones de diseño (resumen para `INFO.md`)

* **TCP dual-stack**: confiable + cumple IPv4/IPv6 (requisito).
* **`asyncio`** en el servidor: muchos clientes concurrentes y E/S de red + disco.
* **Celery+Redis**: cola distribuida estándar, reintentos, *rate limiting*, escalable a múltiples hosts.
* **`multiprocessing`** en workers: filtros CPU-bound → evita GIL.
* **IPC** con `Queue/Pipe` y *FIFOs opcionales*: cubre tema de comunicación interproceso.
* **Preview HTTP**: demuestra `http.server` y threading.
* **Docker**: despliegue reproducible y orquestación de workers.

---

## 10) Criterios de evaluación prácticos

* **Demostración en vivo**: lanzar `docker compose up`, iniciar server, 2 workers, correr cliente con un MP4 chico; ver preview en `:8080`, recibir `output.mp4`.
* **Preguntas teóricas**: por qué `multiprocessing` y no `threading` para CPU-bound; cómo garantizar dual-stack; cómo manejar backpressure; diferencia **pipe vs FIFO**; qué pasa si muere un worker (reintentos Celery).

---