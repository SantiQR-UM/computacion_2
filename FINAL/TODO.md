# Lista de Mejoras y Características Futuras

## MVP Actual ✓

- [x] Cliente CLI con argparse
- [x] Protocolo de mensajes JSON
- [x] Procesamiento distribuido con Celery + Redis
- [x] Filtros OpenCV: blur, edges, faces, motion
- [x] Escritura de video con ThreadPoolExecutor
- [x] Métricas (FPS, latencias, reintentos)
- [x] Docker + docker-compose
- [x] Documentación completa
- [x] Dual-stack TCP (IPv4/IPv6) asíncrono
- [x] HTTP de Preview
- [x] Progress Tracking con FrameCollector (concurrent.futures)

## Mejoras Posibles

### 1. ✅ Usar FrameCollector para Recolección de Frames con Progress Tracking (IMPLEMENTADO)
**Prioridad**: Alta (para examen / demo avanzada)
**Esfuerzo**: Bajo (código ya implementado en `frame_collector.py`)
**Estado**: ✅ **COMPLETADO**

#### Problema Actual
La implementación actual en `server.py` usa `asyncio.gather()` para esperar todos los frames, sin feedback intermedio:

```python
# Implementación actual (líneas 138-183 de server.py)
async def get_celery_results(self, tasks: list):
    async def wait_for_frame(frame_number):
        # ... polling con asyncio.sleep(0.1)
        pass

    # ❌ Espera TODOS los frames sin feedback hasta el final
    awaiting_coroutines = [wait_for_frame(frame_num) for frame_num, _ in tasks]
    all_results = await asyncio.gather(*awaiting_coroutines, return_exceptions=True)
    return all_results
```

**Limitaciones:**
- ❌ Sin progress tracking en tiempo real
- ❌ No permite procesamiento por batches (streaming)
- ❌ Difícil cancelar frames individuales
- ❌ Usuario no ve progreso hasta que termina todo

#### Solución: FrameCollector (ya implementado)

El archivo `src/frame_collector.py` (actualmente no usado) implementa recolección avanzada con:
- ✅ **ThreadPoolExecutor** para polling paralelo
- ✅ **Callbacks** para progress tracking en tiempo real
- ✅ **Batch processing** (recolectar primeros 50 frames, procesar, mientras recolecta siguientes)
- ✅ **Futures explícitos** para cancelación y monitoreo granular
- ✅ **Versión async** compatible con el event loop de asyncio

#### Mejoras Concretas

**1. Progress Tracking en Tiempo Real:**
```python
def on_frame_ready(result):
    print(f"✓ Frame {result.frame_number} listo ({completed}/{total})")
    # Actualizar preview server
    redis_client.set(f'session:{session_id}:progress', progress)

results = collector.collect_frames_parallel(range(300), callback=on_frame_ready)
```

**2. Batch Processing / Streaming:**
```python
# ⚡ Empieza a escribir video mientras otros frames se procesan
for result in collector.collect_frames_streaming(total_frames=300, batch_size=50):
    frame = result.load_frame()
    writer.write(frame)  # Latencia inicial reducida
```

**3. Cancelación de Frames:**
```python
collector = FrameCollectorWithFutures()
futures = collector.submit_all_frames(300)

# Usuario cancela procesamiento
futures[150].cancel()  # Cancelar frame específico
collector.cancel_all()  # Cancelar todos los pendientes
```

#### Cambios Necesarios en `server.py`

**Paso 1: Importar FrameCollector** (al inicio del archivo, línea ~30)
```python
from frame_collector import FrameCollector, FrameResult
```

**Paso 2: Reemplazar método `get_celery_results`** (líneas 138-183)

**ANTES:**
```python
async def get_celery_results(self, tasks: list, executor=None) -> list:
    frames_dir = f'/app/data/frames/{self.session_id}'

    async def wait_for_frame(frame_number):
        frame_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.png')
        stats_path = os.path.join(frames_dir, f'frame_{frame_number:06d}.json')
        max_wait = 300
        check_interval = 0.1
        waited = 0

        while waited < max_wait:
            if os.path.exists(frame_path) and os.path.exists(stats_path):
                import json
                try:
                    with open(stats_path, 'r') as f:
                        stats = json.load(f)
                except Exception:
                    stats = {...}

                return {'frame_path': frame_path, 'frame_number': frame_number, 'stats': stats}

            await asyncio.sleep(check_interval)
            waited += check_interval

        raise TimeoutError(f"Frame {frame_number} no apareció en {max_wait}s")

    print("Esperando que todos los frames se procesen en disco...")
    awaiting_coroutines = [wait_for_frame(frame_num) for frame_num, _ in tasks]
    all_results = await asyncio.gather(*awaiting_coroutines, return_exceptions=True)
    print("Todos los frames procesados.")
    return all_results
```

**DESPUÉS:**
```python
async def get_celery_results(self, tasks: list, executor=None) -> list:
    """Espera frames usando FrameCollector con progress tracking."""
    frames_dir = f'/app/data/frames/{self.session_id}'
    frame_numbers = [frame_num for frame_num, _ in tasks]
    total_frames = len(frame_numbers)

    # Crear collector con configuración optimizada
    collector = FrameCollector(
        frames_dir=frames_dir,
        max_workers=8,      # 8 threads en paralelo para polling I/O-bound
        poll_interval=0.1,  # Check cada 100ms
        timeout=300.0       # 5 minutos timeout por frame
    )

    # Callback para progress tracking en tiempo real
    completed_count = [0]  # Usar lista para modificar en closure

    def on_frame_ready(result: FrameResult):
        completed_count[0] += 1
        progress = (completed_count[0] / total_frames) * 100

        print(f"✓ Frame {result.frame_number} listo ({completed_count[0]}/{total_frames}) - {progress:.1f}%")

        # Actualizar Redis para el preview server
        if redis_client:
            try:
                redis_client.set(f'session:{self.session_id}:progress', f'{progress:.2f}')
                redis_client.set(f'session:{self.session_id}:frames_processed', completed_count[0])

                # Calcular FPS y ETA
                elapsed = time.time() - self.metrics.start_time if hasattr(self.metrics, 'start_time') else 1
                current_fps = completed_count[0] / elapsed if elapsed > 0 else 0
                frames_remaining = total_frames - completed_count[0]
                eta_seconds = frames_remaining / current_fps if current_fps > 0 else 0

                redis_client.set(f'session:{self.session_id}:current_fps', f'{current_fps:.2f}')
                redis_client.set(f'session:{self.session_id}:eta_seconds', f'{eta_seconds:.1f}')
            except Exception as e:
                pass  # Ignore Redis errors

    # Usar versión async (no bloquea el event loop de asyncio)
    print(f"Esperando que {total_frames} frames se procesen en disco (con progress tracking)...")
    results = await collector.collect_frames_async(frame_numbers, callback=on_frame_ready)
    print("Todos los frames procesados.")

    # Convertir de FrameResult a formato esperado por _process_results_sync
    all_results = []
    for r in results:
        if r.frame_path:
            all_results.append({
                'frame_path': r.frame_path,
                'frame_number': r.frame_number,
                'stats': r.stats
            })
        else:
            # Frame con error
            all_results.append({
                'error': r.stats.get('error', 'Unknown error'),
                'frame_number': r.frame_number
            })

    return all_results
```

**Paso 3: (Opcional) Inicializar start_time en metrics**

En el método `dispatch_tasks` o al inicio del procesamiento, agregar:
```python
self.metrics.start_time = time.time()
```

#### Alternativa: Batch Processing / Streaming

Si prefieres reducir latencia inicial (empezar a escribir video antes de que terminen todos los frames):

**Reemplazar método `process_video`** para procesar en streaming:

```python
async def process_video_streaming(self, video_path: str, output_path: str, codec: str = 'mp4v'):
    """Procesa video en streaming: escribe frames a medida que se procesan."""

    # 1. Dispatch frames a Celery
    tasks, original_frames, video_props = await self.dispatch_tasks(video_path)
    total_frames = video_props['total_frames']

    # 2. Crear VideoWriter
    writer = VideoWriter(output_path, codec, video_props['fps'],
                        (video_props['width'], video_props['height']))
    frame_buffer = VideoFrameBuffer(writer)

    # 3. Recolectar y escribir en batches (streaming)
    frames_dir = f'/app/data/frames/{self.session_id}'
    collector = FrameCollector(frames_dir=frames_dir, max_workers=8)

    batch_size = 50  # Procesar de a 50 frames
    for result in collector.collect_frames_streaming(total_frames, batch_size=batch_size):
        # Leer frame procesado
        if result.frame_path and os.path.exists(result.frame_path):
            processed_frame = cv2.imread(result.frame_path)
        else:
            # Fallback a frame original
            processed_frame = original_frames.get(result.frame_number)

        # Escribir inmediatamente (pipeline)
        if processed_frame is not None:
            frame_buffer.add_frame(result.frame_number, processed_frame)

        # Actualizar métricas
        self.metrics.record_frame(
            result.frame_number,
            result.stats.get("processing_time_ms", 0),
            result.stats.get("hostname"),
            result.stats.get("filter_applied"),
            result.stats.get("memory_mb", 0),
            failed=result.frame_path is None
        )

        print(f"✓ Frame {result.frame_number} escrito al video")

    # 4. Cerrar writer y retornar métricas
    frame_buffer.close()
    return self.metrics.get_summary()
```

#### Beneficios para el Examen

1. **Demuestra dominio de `concurrent.futures`**: ThreadPoolExecutor, Futures, as_completed
2. **Progress tracking profesional**: Actualización en tiempo real a Redis
3. **Arquitectura de pipeline**: Procesamiento continuo vs batch
4. **Callbacks y event-driven design**: Más avanzado que solo asyncio.gather
5. **Código ya implementado**: Solo copiar/adaptar, no escribir desde cero

#### Desventajas

- Mayor complejidad (de ~30 líneas a ~60 líneas)
- Overhead de threads (ThreadPoolExecutor vs coroutines puras)
- Requiere entender bien concurrent.futures

#### Recomendación

**USAR** si:
- Quieres destacar en el examen con progress tracking avanzado
- Necesitas procesar videos largos (300+ frames)
- Quieres demostrar dominio de concurrent.futures

**NO USAR** si:
- Prefieres simplicidad
- Videos cortos (< 100 frames)
- Ya funciona bien y no quieres riesgo

#### ✅ Estado de Implementación

**IMPLEMENTADO** - Los siguientes cambios fueron realizados en `server.py`:

1. ✅ **Import agregado** (línea 28):
   ```python
   from frame_collector import FrameCollector, FrameResult
   ```

2. ✅ **Método `get_celery_results` reemplazado** (líneas 142-205):
   - Usa `FrameCollector` con ThreadPoolExecutor (8 workers)
   - Callback `on_frame_ready()` actualiza progreso en tiempo real
   - Actualiza Redis con: `progress`, `frames_processed`, `current_fps`, `eta_seconds`
   - Conversión automática de `FrameResult` a formato esperado

3. ✅ **Inicialización de `start_time`** (línea 132 en `dispatch_tasks`):
   ```python
   self.start_time = time.time()
   ```

4. ✅ **Integración con Preview Server**:
   - `preview_server.py` ya lee `current_fps` y `eta_seconds` de Redis
   - Dashboard web muestra FPS y ETA en tiempo real
   - Updates vía Server-Sent Events (SSE)

**Resultado:**
- ✅ Progress tracking en consola: `✓ Frame 42 listo (42/300) - 14.0%`
- ✅ Updates en tiempo real a Redis cada frame procesado
- ✅ Dashboard web muestra progreso, FPS y ETA actualizados
- ✅ Cálculos precisos basados en tiempo real (no estimaciones)

---

### 2. Soporte para AF_UNIX (Unix Domain Sockets)
**Prioridad**: Media
**Esfuerzo**: Bajo

Permitir que cliente y servidor se comuniquen vía Unix sockets cuando están en el mismo host.

**Implementación**:
- Añadir `--unix-socket PATH` a cliente y servidor
- Usar `socket.AF_UNIX` en lugar de `AF_INET/AF_INET6`
- Comparar performance con TCP loopback

**Beneficios**:
- Cumple tema "AF_UNIX (Unix Domain Sockets)"
- Mejor performance para comunicación local
- Evita stack de red

---

### 3. Integración con FIFOs para Pipeline Offline
**Prioridad**: Media
**Esfuerzo**: Medio

Crear script que use FIFOs nombradas para integrar `ffmpeg`:

```bash
mkfifo frame_input.fifo
ffmpeg -i input.mp4 -f image2pipe - > frame_input.fifo &
python frame_processor.py < frame_input.fifo
```

**Beneficios**:
- Cumple tema "FIFOs en Sistemas Unix/Linux"
- Demuestra pipeline con herramientas externas
- Procesamiento sin almacenar frames intermedios

### 4. Base de Datos para Historial de Trabajos
**Prioridad**: Media
**Esfuerzo**: Alto

Almacenar información de cada procesamiento en SQLite o PostgreSQL:
- ID de sesión
- Parámetros de procesamiento
- Métricas finales
- Timestamps de inicio/fin
- Ruta a videos entrada/salida

**Beneficios**:
- Historial de trabajos
- Análisis de performance a lo largo del tiempo
- Posibilidad de re-procesar con mismos parámetros

### 5. Streaming de Video en Tiempo Real
**Prioridad**: Baja
**Esfuerzo**: Alto

Procesar frames a medida que se reciben sin esperar al video completo.

**Implementación**:
- Cliente envía frames uno a uno
- Servidor procesa y envía de vuelta inmediatamente
- Cliente puede ver preview en tiempo real

**Beneficios**:
- Menor latencia inicial
- Procesamiento de streams infinitos (ej: webcam)
- Uso eficiente de memoria

## Mejoras de Performance

### 6. Subdivisión de Frames con multiprocessing
**Prioridad**: Baja
**Esfuerzo**: Medio

Para filtros muy CPU-bound, dividir frame en tiles y procesar con `multiprocessing.Pool`.

**Casos de uso**:
- Videos 4K+ donde un frame es muy grande
- Filtros costosos (ej: optical flow de alta resolución)

**Implementación**:
- Añadir `--tile-size` en worker
- Dividir frame en grid NxM
- Procesar cada tile en proceso separado con `Pool`
- Reconstruir frame

### 7. GPU Acceleration con CUDA
**Prioridad**: Baja
**Esfuerzo**: Alto

Usar OpenCV compilado con CUDA para procesamiento en GPU.

**Requisitos**:
- NVIDIA GPU
- CUDA toolkit
- OpenCV con soporte CUDA

**Beneficios**:
- Aceleración 10-50x en filtros soportados
- Procesar videos 4K en tiempo real

### 8. Compresión de Frames en Tránsito
**Prioridad**: Baja
**Esfuerzo**: Bajo

Comprimir frames antes de enviar a workers y descomprimir al recibir.

**Implementación**:
- Usar `zlib` o `lz4` para comprimir PNG
- Añadir campo `compressed: true` en metadatos
- Medir tradeoff CPU vs. ancho de banda

## Mejoras de Robustez

### 9. Checkpointing y Recuperación
**Prioridad**: Media
**Esfuerzo**: Alto

Guardar progreso periódicamente para recuperar si se interrumpe.

**Implementación**:
- Guardar frames procesados en disco temporal
- Metadata de qué frames están completos
- Al reiniciar, saltar frames ya procesados

**Beneficios**:
- Recuperación ante crashes
- Poder pausar/resumir procesamiento

### 10. Rate Limiting Inteligente
**Prioridad**: Baja
**Esfuerzo**: Medio

Ajustar dinámicamente rate limit de Celery según carga de workers.

**Implementación**:
- Monitorear longitud de cola y uso de CPU
- Reducir rate si cola crece mucho
- Aumentar si workers están ociosos

## Mejoras de Usabilidad

### 11. Interfaz Web
**Prioridad**: Baja
**Esfuerzo**: Alto

Frontend web para subir videos, ver progreso y descargar resultados.

**Stack sugerido**:
- Backend: Flask o FastAPI
- Frontend: HTML + JavaScript (htmx o Alpine.js)
- WebSockets para progreso en tiempo real

### 12. Presets de Procesamiento
**Prioridad**: Baja
**Esfuerzo**: Bajo

Configuraciones predefinidas:

```bash
python client.py --preset cinematic --video input.mp4
# Aplica: denoise → color grading → sharpen
```

**Implementación**:
- Archivo de configuración YAML/JSON
- Parsear en cliente y enviar lista de filtros

### 13. Batch Processing
**Prioridad**: Media
**Esfuerzo**: Medio

Procesar múltiples videos en un solo comando:

```bash
python client.py --batch videos/*.mp4 --processing blur
```

**Implementación**:
- Expandir glob pattern
- Procesar videos secuencialmente o en paralelo
- Reporte consolidado de métricas

## Mejoras de Monitoreo

### 14. Integración con Prometheus + Grafana
**Prioridad**: Baja
**Esfuerzo**: Alto

Exportar métricas en formato Prometheus para visualización en Grafana.

**Métricas**:
- Latencias de procesamiento (histograma)
- Throughput (frames/s)
- Uso de CPU/memoria por worker
- Longitud de cola de Celery

### 15. Logging Estructurado
**Prioridad**: Media
**Esfuerzo**: Bajo

Usar `structlog` para logs en formato JSON.

**Beneficios**:
- Logs parseables automáticamente
- Integración con ELK stack (Elasticsearch + Kibana)
- Mejor debugging en producción

## Mejoras de Testing

### 16. Tests Unitarios
**Prioridad**: Alta
**Esfuerzo**: Alto

Crear suite de tests con `pytest`:
- Tests de filtros (entrada/salida conocida)
- Tests de protocolo (serialización/deserialización)
- Tests de VideoWriter
- Mocks para Celery

### 17. Tests de Integración
**Prioridad**: Media
**Esfuerzo**: Alto

Tests end-to-end:
- Levantar servidor + workers en containers de test
- Enviar video de prueba
- Verificar salida

### 18. Tests de Performance
**Prioridad**: Baja
**Esfuerzo**: Medio

Benchmarks automatizados:
- Medir throughput con 1, 2, 4, 8 workers
- Comparar performance de filtros
- Detectar regresiones de performance

## Mejoras de Seguridad

### 19. Autenticación de Clientes
**Prioridad**: Media
**Esfuerzo**: Medio

Añadir autenticación básica:
- Token en handshake
- Validar token contra base de datos o JWT
- Rate limiting por cliente

### 20. Sandboxing de Filtros
**Prioridad**: Baja
**Esfuerzo**: Alto

Ejecutar filtros custom en sandbox (Docker, seccomp, etc.).

**Beneficios**:
- Permitir filtros custom sin riesgo
- Protección contra código malicioso

## Características Experimentales

### 21. Procesamiento con ML (YOLO, etc.)
**Prioridad**: Baja
**Esfuerzo**: Alto

Integrar modelos de machine learning:
- Detección de objetos (YOLO)
- Segmentación semántica
- Super-resolution
- Style transfer

### 22. Pipeline Configurable con DAG
**Prioridad**: Baja
**Esfuerzo**: Alto

Permitir pipelines complejos descritos como DAG:

```yaml
pipeline:
  - id: denoise
    type: blur
    params: {kernel: 3}
  - id: detect
    type: faces
    depends_on: [denoise]
  - id: blur_faces
    type: custom
    depends_on: [detect]
```

### 23. Soporte para Múltiples Codecs
**Prioridad**: Media
**Esfuerzo**: Medio

Permitir más codecs de salida:
- H.264 (vía OpenCV con compilación especial)
- H.265 / HEVC
- VP9 / AV1
- Delegar a `ffmpeg` si OpenCV no soporta

## Roadmap Sugerido

### Fase 1: Completar MVP (Actual) ✓
- Funcionalidad básica completa
- Documentación
- Servidor HTTP de Preview ✓

### Fase 2: Robustez y Usabilidad
1. Progress Tracking con FrameCollector (#1) ⭐
2. Tests Unitarios (#17)
3. Checkpointing (#10)
4. Batch Processing (#14)

### Fase 3: Performance
1. Subdivisión de Frames (#7)
2. Compresión (#9)
3. Tests de Performance (#19)

### Fase 4: Producción
1. Base de Datos (#5)
2. Autenticación (#20)
3. Monitoring con Prometheus (#15)
4. Logging Estructurado (#16)

### Fase 5: Características Avanzadas
1. Interfaz Web (#12)
2. GPU Acceleration (#8)
3. Procesamiento con ML (#22)

## Contribuciones

Si quieres contribuir con alguna de estas features:
1. Abrir issue discutiendo el diseño
2. Fork del repo
3. Implementar feature con tests
4. Abrir PR con descripción detallada

---

**Nota**: Este documento es un living document. Se actualizará a medida que se implementen features y surjan nuevas ideas.
