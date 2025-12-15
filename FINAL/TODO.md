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

## Mejoras Posibles


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
- Servidor HTTP de Preview (#1)

### Fase 2: Robustez y Usabilidad
)
2. Tests Unitarios (#16)
3. Checkpointing (#9)
4. Batch Processing (#13)

### Fase 3: Performance
1. Subdivisión de Frames (#6)
2. Compresión (#8)
3. Tests de Performance (#18)

### Fase 4: Producción
1. Base de Datos (#4)
2. Autenticación (#19)
3. Monitoring con Prometheus (#14)
4. Logging Estructurado (#15)

### Fase 5: Características Avanzadas
1. Interfaz Web (#11)
2. GPU Acceleration (#7)
3. Procesamiento con ML (#21)

## Contribuciones

Si quieres contribuir con alguna de estas features:
1. Abrir issue discutiendo el diseño
2. Fork del repo
3. Implementar feature con tests
4. Abrir PR con descripción detallada

---

**Nota**: Este documento es un living document. Se actualizará a medida que se implementen features y surjan nuevas ideas.
