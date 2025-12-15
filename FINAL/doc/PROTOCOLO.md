# Protocolo de Comunicación Cliente-Servidor

## Formato de Mensajes

Todos los mensajes se envían en formato **JSON** con un prefijo de longitud de **4 bytes** (big-endian) seguido del payload JSON.

```
┌─────────────┬──────────────────┐
│  4 bytes    │   N bytes        │
│  (length)   │   (JSON)         │
└─────────────┴──────────────────┘
```

## Tipos de Mensajes

### 1. Handshake (Cliente → Servidor)

**Propósito**: Negociar parámetros de procesamiento al inicio de la conexión.

```json
{
  "type": "handshake",
  "version": 1,
  "mode": "stream",
  "codec": "h264",
  "processing": "blur",
  "filters": [
    ["blur", {"kernel": 5}],
    ["denoise", {}]
  ],
  "video_info": {
    "filename": "input.mp4",
    "size_bytes": 10485760
  }
}
```

**Campos**:
- `type`: siempre `"handshake"`
- `version`: versión del protocolo (actualmente `1`)
- `mode`: modo de envío (`"stream"` o `"file"`)
- `codec`: codec de salida deseado (`"h264"`, `"vp9"`, etc.)
- `processing`: tipo de procesamiento principal (`"blur"`, `"faces"`, `"edges"`, `"motion"`, `"custom"`)
- `filters` (opcional): lista de filtros adicionales con parámetros
- `video_info`: información del video

### 2. Handshake ACK (Servidor → Cliente)

**Propósito**: Confirmar aceptación de parámetros.

```json
{
  "type": "handshake_ack",
  "accepted": true,
  "session_id": "abc123def456",
  "preview_url": "http://[::1]:8080"
}
```

**Campos**:
- `type`: siempre `"handshake_ack"`
- `accepted`: booleano indicando si se aceptó la conexión
- `session_id`: identificador único de la sesión
- `preview_url`: URL del preview HTTP (si está habilitado)

### 3. Frame Data (Cliente → Servidor)

**Propósito**: Enviar un frame del video.

Para frames individuales, se envía primero el mensaje de metadatos y luego los bytes del frame:

```json
{
  "type": "frame",
  "seq": 42,
  "pts": 1400000,
  "size_bytes": 921600
}
```

Seguido de `size_bytes` bytes del frame codificado (PNG o JPG).

**Campos**:
- `type`: siempre `"frame"`
- `seq`: número de secuencia del frame (0-indexed)
- `pts`: presentation timestamp
- `size_bytes`: tamaño del frame en bytes

### 4. EOF (Cliente → Servidor)

**Propósito**: Indicar fin del stream de video.

```json
{
  "type": "eof",
  "total_frames": 1440
}
```

**Campos**:
- `type`: siempre `"eof"`
- `total_frames`: cantidad total de frames enviados

### 5. Progress (Servidor → Cliente)

**Propósito**: Actualización de progreso durante el procesamiento.

```json
{
  "type": "progress",
  "frames_processed": 120,
  "frames_total": 1440,
  "fps": 24.5,
  "eta_seconds": 53.9
}
```

**Campos**:
- `type`: siempre `"progress"`
- `frames_processed`: frames procesados hasta el momento
- `frames_total`: total de frames a procesar
- `fps`: frames por segundo de procesamiento
- `eta_seconds`: tiempo estimado restante

### 6. Result (Servidor → Cliente)

**Propósito**: Enviar resultado final con métricas.

```json
{
  "type": "result",
  "ok": true,
  "output_path": "output.mp4",
  "size_bytes": 8388608,
  "metrics": {
    "total_frames": 1440,
    "fps_input": 30.0,
    "fps_output": 29.97,
    "fps_processing": 24.3,
    "processing_time_seconds": 59.2,
    "retries": 5,
    "latency_p50_ms": 41.2,
    "latency_p95_ms": 87.5,
    "latency_p99_ms": 124.8,
    "frames_failed": 0
  }
}
```

Seguido de `size_bytes` bytes del video procesado.

**Campos**:
- `type`: siempre `"result"`
- `ok`: booleano indicando éxito
- `output_path`: nombre del archivo de salida
- `size_bytes`: tamaño del video procesado
- `metrics`: diccionario con métricas detalladas

### 7. Error (Servidor → Cliente)

**Propósito**: Notificar error durante el procesamiento.

```json
{
  "type": "error",
  "code": "PROCESSING_FAILED",
  "message": "Worker timeout on frame 234",
  "recoverable": false
}
```

**Campos**:
- `type`: siempre `"error"`
- `code`: código de error (`"INVALID_FORMAT"`, `"PROCESSING_FAILED"`, etc.)
- `message`: descripción del error
- `recoverable`: indica si el cliente puede reintentar

## Flujo de Comunicación

### Flujo exitoso completo

```
Cliente                                    Servidor
  │                                           │
  │────── handshake ──────────────────────────>│
  │                                           │
  │<────── handshake_ack ─────────────────────│
  │                                           │
  │────── frame (seq=0) ──────────────────────>│
  │────── frame (seq=1) ──────────────────────>│
  │────── frame (seq=2) ──────────────────────>│
  │       ...                                 │
  │                                           │
  │<────── progress ──────────────────────────│ (periódico)
  │                                           │
  │────── frame (seq=N-1) ────────────────────>│
  │────── eof ────────────────────────────────>│
  │                                           │
  │                [procesamiento]            │
  │                                           │
  │<────── result ────────────────────────────│
  │<────── [video bytes] ─────────────────────│
  │                                           │
```

### Flujo con error

```
Cliente                                    Servidor
  │                                           │
  │────── handshake ──────────────────────────>│
  │                                           │
  │<────── error ─────────────────────────────│
  │         (INVALID_CODEC)                   │
  │                                           │
  [conexión cerrada]
```

## Implementación

### En Python

#### Envío de mensaje

```python
import json
import struct

def send_message(sock, message_dict):
    """Envía un mensaje JSON con prefijo de longitud."""
    payload = json.dumps(message_dict).encode('utf-8')
    length = struct.pack('!I', len(payload))  # 4 bytes big-endian
    sock.sendall(length + payload)
```

#### Recepción de mensaje

```python
def recv_message(sock):
    """Recibe un mensaje JSON con prefijo de longitud."""
    length_bytes = sock.recv(4)
    if not length_bytes:
        return None
    length = struct.unpack('!I', length_bytes)[0]
    payload = b''
    while len(payload) < length:
        chunk = sock.recv(min(4096, length - len(payload)))
        if not chunk:
            raise ConnectionError("Conexión cerrada prematuramente")
        payload += chunk
    return json.loads(payload.decode('utf-8'))
```

## Consideraciones de Diseño

### Longitud prefijada
El uso de longitud prefijada permite:
- Saber exactamente cuántos bytes leer
- Evitar delimitadores especiales en el payload
- Facilitar el parsing de mensajes grandes

### JSON como formato
- Legible y debuggable
- Fácil extensibilidad
- Amplio soporte en Python
- Overhead aceptable para mensajes de control

### Separación de metadatos y datos binarios
Los frames se envían como:
1. Mensaje JSON con metadatos (`seq`, `pts`, `size`)
2. Bytes raw del frame

Esto permite:
- Procesar metadatos sin cargar todo el frame
- Validar integridad antes de recibir datos
- Optimizar buffers de recepción
