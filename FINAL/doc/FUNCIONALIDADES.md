# Funcionalidades de Cada Entidad

## Cliente (`client.py`)

### Funcionalidad principal
Enviar un video al servidor para su procesamiento y recibir el resultado procesado.

### Argumentos (argparse)
- `--host HOST`: Dirección del servidor (default: `::1` para IPv6 loopback)
- `--port PORT`: Puerto del servidor (default: `9090`)
- `--ipv6`: Forzar IPv6
- `--ipv4`: Forzar IPv4
- `--video PATH`: Ruta al archivo de video a procesar (requerido)
- `--processing TYPE`: Tipo de procesamiento (`blur`, `faces`, `edges`, `motion`, `custom`)
- `--out PATH`: Ruta del archivo de salida (default: `output.mp4`)
- `--preview`: Mostrar URL del preview HTTP mientras procesa
- `--protocol MODE`: Modo de envío (`file` para copiar, `stream` para streaming)

### Flujo
1. Parsear argumentos
2. Conectar al servidor vía TCP
3. Enviar handshake con parámetros de procesamiento
4. Enviar video (chunked) con checksum
5. Mostrar barra de progreso
6. Recibir video procesado y JSON con métricas
7. Guardar resultado

### Salida
- Archivo de video procesado
- JSON con métricas en consola

---

## Servidor (`server.py`)

### Funcionalidad principal
Recibir videos de clientes, extraer frames, distribuirlos a workers, reensamblar y devolver resultado.

### Componentes

#### 1. TCP Server Asíncrono (asyncio)
- Escucha en `::` (dual-stack IPv4/IPv6)
- Acepta múltiples clientes concurrentes
- Maneja handshake y recepción de video

#### 2. Dispatcher
- Extrae frames con OpenCV (`cv2.VideoCapture`)
- Envía frames completos a Celery con tipo de procesamiento
- Asigna `task_id` a cada frame

#### 3. Aggregator
- Espera resultados de Celery (futures)
- Reconstruye frames procesados en orden
- Envía frames al muxer

#### 4. Muxer
- Escribe MP4 con `cv2.VideoWriter` o `ffmpeg-python`
- Genera thumbnails y preview GIF
- Usa `ThreadPoolExecutor` para escritura I/O-bound

#### 5. Preview HTTP
- Servidor HTTP (`http.server`) en puerto separado (default: 8080)
- Endpoints:
  - `/metrics`: JSON con métricas en tiempo real
  - `/frame/<n>`: Frame específico (JPG)
  - `/preview.gif`: GIF animado del progreso

### Argumentos
- `--bind ADDR`: Dirección de escucha (default: `::`)
- `--port PORT`: Puerto TCP (default: `9090`)
- `--preview-port PORT`: Puerto HTTP (default: `8080`)
- `--codec CODEC`: Codec de salida (default: `h264`)
- `--default-processing TYPE`: Procesamiento por defecto si cliente no especifica

### Métricas recolectadas
- FPS entrada/salida
- Frames por segundo procesados
- Reintentos por frame
- Latencia p50, p95, p99
- Uso de CPU por proceso
- Frames en cola

---

## Worker (`worker.py`)

### Funcionalidad principal
Procesar frames individuales aplicando filtros de OpenCV según el tipo solicitado.

### Tarea Celery: `process_frame`

**Entrada:**
- `frame_data`: bytes del frame (PNG/JPG codificado)
- `frame_number`: número de secuencia
- `processing_type`: tipo de procesamiento (`blur`, `faces`, `edges`, `motion`)
- `metadata`: diccionario con parámetros adicionales

**Procesamiento:**
1. Decodificar frame (OpenCV `cv2.imdecode`)
2. Aplicar pipeline de filtros según `processing_type`:
   - `blur`: Gaussian blur
   - `faces`: Detección de rostros con Haar cascades
   - `edges`: Canny edge detection
   - `motion`: Diferencia con frame anterior
   - `custom`: Pipeline personalizado
3. Codificar frame procesado

**Salida:**
- `frame_data`: bytes del frame procesado
- `stats`: diccionario con métricas (tiempo_ms, memoria_mb, filtro_aplicado)

### Configuración Celery
- Cola: `frames`
- Reintentos: 3 (exponential backoff)
- Timeout: 30s por frame
- Rate limiting: 64 frames/s

---

## Componentes de Soporte

### `filters/` (módulo de filtros)

Filtros implementados sobre OpenCV:

- `blur.py`: Gaussian blur, median blur, bilateral filter
- `edges.py`: Canny, Sobel, Laplacian
- `faces.py`: Detección de rostros con Haar cascades
- `motion.py`: Diferencia entre frames, optical flow

### `protocol/` (protocolo de mensajes)

Mensajes JSON con longitud prefijada:

- `messages.py`: Serialización/deserialización de mensajes
- Tipos: `handshake`, `frame`, `eof`, `result`, `error`

### `storage/` (escritor de video)

- `writer.py`: Wrapper sobre `cv2.VideoWriter`
- Soporte para múltiples codecs (H.264, VP9)
- Escritura thread-safe

### `metrics/` (métricas)

- `stats.py`: Recolección de estadísticas
- Cálculo de percentiles (p50, p95, p99)
- Contador de reintentos
- Registro de latencias
