# Decisiones de Diseño y Justificaciones

## Resumen

Este documento explica las principales decisiones de diseño del sistema y sus justificaciones técnicas.

## 1. Arquitectura Cliente-Servidor con Procesamiento Distribuido

### Decisión
Implementar una arquitectura cliente-servidor donde el servidor actúa como orquestador y delega el procesamiento a workers distribuidos.

### Justificación
- **Escalabilidad**: Permite añadir workers según la carga de procesamiento
- **Separación de responsabilidades**: El servidor maneja red/orquestación, los workers hacen procesamiento CPU-bound
- **Tolerancia a fallos**: Si un worker falla, Celery reintenta en otro
- **Aprovechamiento de recursos**: Múltiples máquinas pueden colaborar en el procesamiento

## 2. Unidad de Trabajo: Frame Completo

### Decisión
Procesar frames completos en lugar de dividirlos en tiles/regiones.

### Justificación
- **Simplicidad**: Evita complejidad de reconstrucción de tiles
- **Coherencia en filtros**: Algunos filtros (ej: detección de rostros) pueden ser cortados por bordes artificiales de tiles
- **Paralelización suficiente**: Con videos de 30+ FPS, hay suficiente paralelismo entre frames
- **Balance**: Si un filtro específico requiere más paralelismo, puede subdividir internamente el frame con `multiprocessing`, pero la interfaz se mantiene simple

## 3. Asyncio en el Servidor

### Decisión
Usar `asyncio` para el servidor TCP en lugar de threading o multiprocessing.

### Justificación
- **Concurrencia I/O-bound**: El servidor hace principalmente I/O de red (recibir/enviar datos)
- **Escalabilidad**: Puede manejar muchos clientes simultáneos con bajo overhead
- **Event loop**: Permite coordinar múltiples operaciones asíncronas (recepción, dispatch a Celery, escritura)
- **Moderno**: `asyncio` es el estándar actual en Python para I/O concurrente

## 4. Celery + Redis para Distribución de Tareas

### Decisión
Usar Celery con Redis solo como broker (NO se usa result backend).

**NOTA IMPORTANTE**: Se usa Redis únicamente como broker. Los resultados se intercambian vía filesystem compartido (ver sección 16 más abajo).

### Justificación
- **Solución probada**: Celery es estándar de industria para tareas distribuidas
- **Características built-in**: Reintentos, timeouts, rate limiting, monitoring
- **Escalabilidad**: Redis es rápido y confiable como broker
- **Simplicidad**: Evita reinventar la rueda con una cola custom
- **Requisito del curso**: "Uso de cola de tareas distribuidas" → Celery cumple perfectamente

## 5. concurrent.futures (ThreadPoolExecutor) para Operaciones I/O-Bound

### Decisión
Usar `ThreadPoolExecutor` en DOS contextos I/O-bound:
1. **Escritura de video** (VideoWriter)
2. **Polling paralelo de frames** (FrameCollector) ⭐ **NUEVO**

### Justificación

#### General
- **I/O-bound**: Operaciones de disco (escritura/lectura) son I/O-bound, no CPU-bound
- **GIL no es problema**: I/O libera el GIL en Python
- **Simplicidad**: Interfaz más simple que multiprocessing
- **Preferencia del enunciado**: "si hay dos similares como multiprocessing y futures, utilizar el que más conveniente, como futures"
- **Menor overhead**: Threads son más livianos que procesos para I/O

#### Caso 1: Escritura de Video (VideoWriter)
- Escribir frames a disco no debe bloquear el event loop de asyncio
- ThreadPoolExecutor con 1 worker para escritura secuencial
- Futures para sincronización asíncrona

#### Caso 2: Polling Paralelo de Frames (FrameCollector) ⭐
- **Problema**: Esperar que 300 frames aparezcan en disco secuencialmente es lento
- **Solución**: ThreadPoolExecutor con 8 workers haciendo polling en paralelo
- **Ventajas**:
  - Polling de múltiples frames simultáneamente
  - Callbacks para progress tracking en tiempo real
  - `as_completed()` procesa frames a medida que llegan (no espera a todos)
  - Compatible con asyncio via `loop.run_in_executor()`
  - Actualización de métricas (FPS, ETA) en tiempo real a Redis
- **Implementación**: `src/frame_collector.py` usado por `server.py`

## 6. OpenCV para Todo el Pipeline de Video

### Decisión
Usar OpenCV tanto para lectura, procesamiento y escritura de video.

### Justificación
- **Una sola librería**: Evita dependencias múltiples (ffmpeg-python, PIL, etc.)
- **Performance**: OpenCV está implementado en C++, muy rápido
- **Completo**: Incluye VideoCapture, VideoWriter y todos los filtros necesarios
- **Integración**: Trabajo directo con numpy arrays (eficiente)
- **Haar cascades incluidos**: Para detección de rostros, OpenCV incluye los XMLs

## 7. TCP Dual-Stack (IPv4/IPv6)

### Decisión
Implementar servidor dual-stack que acepta conexiones IPv4 e IPv6 simultáneamente.

### Justificación
- **Requisito del curso**: "Uso de Sockets con conexión de clientes múltiples... dual-stack (IPv4/IPv6)"
- **Flexibilidad**: Clientes pueden conectar con cualquier protocolo
- **Configuración simple**: `IPV6_V6ONLY=0` en socket IPv6 permite ambos
- **Futuro-proof**: IPv6 es el futuro de Internet

## 8. Protocolo JSON con Longitud Prefijada

### Decisión
Mensajes JSON con prefijo de 4 bytes indicando longitud del payload.

### Justificación
- **Legibilidad**: JSON es human-readable, facilita debugging
- **Extensibilidad**: Fácil añadir campos sin romper compatibilidad
- **Delimitación clara**: Longitud prefijada evita necesidad de delimitadores especiales
- **Balance**: Overhead aceptable para mensajes de control (no para frames grandes)
- **Soporte nativo**: Python tiene `json` y `struct` en stdlib

## 9. Separación de Metadatos y Datos Binarios

### Decisión
Enviar metadatos de frame (seq, pts, size) en JSON separado de los bytes del frame.

### Justificación
- **Eficiencia**: Evita codificar binario en base64 (overhead 33%)
- **Procesamiento selectivo**: Servidor puede validar metadatos antes de recibir bytes
- **Simplicidad**: Protocolo claro: JSON → bytes → JSON → bytes...
- **Buffer optimization**: Permite preparar buffer del tamaño exacto antes de recibir

## 10. Métricas con Percentiles

### Decisión
Reportar latencias como percentiles (p50, p95, p99) además de promedio.

### Justificación
- **Realista**: Promedio oculta outliers, percentiles muestran distribución real
- **Estándar**: p95/p99 son métricas estándar en sistemas distribuidos
- **Debugging**: p99 alta indica problemas en casos extremos
- **Performance**: Implementación eficiente con sorting

## 11. VideoFrameBuffer para Escritura Ordenada

### Decisión
Implementar buffer que acumula frames desordenados y escribe en orden secuencial.

### Justificación
- **Procesamiento asíncrono**: Workers pueden terminar en cualquier orden
- **Correctitud**: Video final debe tener frames en orden correcto
- **Simplicidad**: VideoWriter de OpenCV requiere frames en secuencia
- **Robustez**: Si falta un frame, puede rellenar con negro o frame anterior

## 12. Docker con docker-compose

### Decisión
Proveer despliegue completo con docker-compose orquestando todos los servicios.

### Justificación
- **Requisito**: "Despliegue en contenedores Docker"
- **Reproducibilidad**: Mismo entorno en desarrollo y producción
- **Facilidad**: Un comando (`docker-compose up`) lanza todo
- **Aislamiento**: Cada servicio en su contenedor
- **Escalabilidad**: Fácil escalar workers con `--scale`

## 13. Dimensionamiento de Workers

### Decisión
Configurar hasta 8 workers en máquina de 12 hilos lógicos, dejando 2 hilos libres.

### Justificación
- **No saturar CPU**: Dejar recursos para SO, Redis, tareas interactivas
- **CPU-bound**: Procesamiento de frames es CPU-bound, más workers que cores satura
- **Balance**: 8 workers + 1 servidor + 1 cliente + 2 libres = 12 hilos
- **Flexibilidad**: Configurable según hardware disponible

## 14. Reintentos con Exponential Backoff

### Decisión
Configurar Celery con 3 reintentos y delay de 5s entre reintentos.

### Justificación
- **Tolerancia a fallos**: Errores temporales (memoria, worker sobrecargado) se recuperan
- **Evita cascadas**: Exponential backoff previene saturación por reintentos
- **Límite razonable**: 3 reintentos balancean recuperación vs. tiempo total
- **Celery built-in**: Configuración estándar de Celery

## 15. argparse para CLI

### Decisión
Usar `argparse` para parseo de argumentos en cliente y servidor.

### Justificación
- **Requisito**: "Parseo de argumentos por línea de comandos"
- **Estándar**: Librería estándar de Python, robusta y completa
- **Help automático**: Genera `--help` automáticamente
- **Validaciones**: Permite especificar tipos, choices, defaults
- **Profesional**: Interfaz CLI clara y consistente

## Decisiones que NO se Tomaron

### ¿Por qué NO multiprocessing en el servidor?
- El servidor es I/O-bound, `asyncio` es más apropiado
- `multiprocessing` añadiría complejidad sin beneficio

### ¿Por qué NO threading para procesamiento de frames?
- Procesamiento de imagen es CPU-bound
- GIL de Python limita paralelismo real con threads
- Celery workers usan procesos, evitando el GIL

### ¿Por qué NO base de datos?
- No es requisito obligatorio
- Para MVP, almacenamiento en disco es suficiente
- Puede añadirse después (ver TODO.md)

### ¿Por qué NO AF_UNIX o FIFOs en el core?
- Son opcionales en el diseño
- TCP es más importante (requisito principal)
- Pueden demostrarse como bonus (ver TODO.md)

## Mapeo a Temas de la Materia

| Tema | Aplicación en el Proyecto |
|------|---------------------------|
| Git | Repositorio con commits incrementales |
| E/S Unix | Lectura/escritura de archivos de video |
| Argumentos | argparse en client.py y server.py |
| Procesos | Workers de Celery como procesos separados |
| Threading | ThreadPoolExecutor para escritura de video y polling de frames |
| Docker | Dockerfiles + docker-compose.yml |
| Redes | TCP dual-stack, protocolos |
| Sockets | Comunicación cliente-servidor |
| HTTP | Servidor de preview con Flask y SSE |
| IPv6 | Dual-stack con IPV6_V6ONLY=0 |
| Asyncio | Servidor asíncrono, event loop |
| concurrent.futures | ThreadPoolExecutor para I/O (escritura + polling paralelo) |
| Celery | Cola de tareas distribuidas, workers |

## 16. Eliminación de Redis Result Backend (Cambio Arquitectónico)

### Decisión
Eliminar completamente el Redis result backend de Celery y reemplazarlo con un sistema basado en filesystem compartido.

### Contexto del Problema
Durante el desarrollo, al procesar videos largos (300+ frames), se descubrió un problema crítico con el Redis result backend:
- Celery reportaba errores de protocolo: `InvalidResponse: Protocol Error`
- Los mensajes JSON se corrompían/truncaban al almacenarse en Redis
- El problema persistía incluso después de:
  - Aumentar memoria de Redis de 512MB a 8GB
  - Cambiar serialización de JSON a pickle
  - Ajustar timeouts y configuración de transporte

### Solución Implementada
**Sistema basado en archivos**:
- Workers escriben frames procesados directamente a disco compartido (`/app/data/frames/`)
- Cada frame genera dos archivos:
  - `frame_XXXXXX.png` - Frame procesado
  - `frame_XXXXXX.json` - Estadísticas del procesamiento
- Servidor hace polling asíncrono esperando que aparezcan los archivos
- `wait_for_frame()` verifica existencia con `asyncio.sleep()` entre checks

### Justificación
**Ventajas**:
- ✅ **Resuelve el problema de escala**: Maneja 300+ frames sin corrupciones
- ✅ **Simplicidad**: Menos configuración de Redis (solo broker, no backend)
- ✅ **Debugging más fácil**: Frames visibles en filesystem para inspección
- ✅ **Sin límites de memoria Redis**: Filesystem puede crecer según disponibilidad
- ✅ **Persistencia natural**: Resultados persisten en disco automáticamente

**Desventajas**:
- ❌ **Requiere volumen compartido**: Docker necesita volumen montado en todos los contenedores
- ❌ **Polling menos eficiente**: Polling activo vs. notificaciones de Celery
- ❌ **No demuestra result backend**: Pierde oportunidad de mostrar feature completa de Celery
- ❌ **Limpieza manual**: Necesita borrar frames de sesiones anteriores

### Trade-off Aceptado
El cambio prioriza **funcionalidad sobre elegancia**. Es preferible un sistema que funciona correctamente a uno que usa todas las features de Celery pero falla en escala.

### Alternativas Consideradas

1. **RabbitMQ como result backend**: No resolvería el problema de serialización de objetos grandes
2. **Dividir resultados en chunks**: Complejidad excesiva, no garantiza solución
3. **PostgreSQL como result backend**: Overhead de BD para datos temporales
4. **Mantener Redis con límite de frames**: Limitaría videos a ~90 frames (~3 segundos)

La solución de filesystem fue la más pragmática dado el tiempo y requisitos del proyecto.

---

## Conclusión

Las decisiones de diseño priorizan:
1. **Cumplimiento de requisitos** del examen final
2. **Funcionalidad sobre elegancia** (ej: filesystem vs Redis backend)
3. **Simplicidad** sobre optimización prematura
4. **Tecnologías estándar** probadas en industria
5. **Escalabilidad** horizontal (añadir workers)
6. **Mantenibilidad** del código

**Lección aprendida**: Sistemas distribuidos en escala revelan problemas que no aparecen en pruebas pequeñas. La capacidad de adaptar la arquitectura ante problemas reales es más valiosa que seguir rígidamente el plan original.
