# Descripción del Proyecto

## Sistema Distribuido de Procesamiento de Video por Frames

### Problema que resuelve

Acelerar procesamientos pesados de video (filtrado, detección de objetos) distribuyendo el trabajo entre múltiples procesos y nodos, demostrando dominio de concurrencia, asincronismo e IPC (Inter-Process Communication).

### Descripción de la aplicación

Una aplicación **cliente-servidor** donde:

1. **El cliente** envía un **video** (o la ruta al archivo) al servidor por **TCP dual-stack (IPv4/IPv6)**.

2. **El servidor** (asíncrono con `asyncio`) **demuxea** el video en **frames** usando **OpenCV** (`cv2.VideoCapture`) y distribuye **cada frame completo** como tarea de procesamiento a **workers** (locales y/o remotos) vía **Celery + Redis**.

3. **Cada worker** (CPU por defecto; opcional GPU) aplica un **pipeline de filtros sobre el frame completo** en función de un **tipo de procesamiento** pedido por el cliente (blur, detección de caras, edges, motion, etc.).

4. Los **resultados por frame** se **reconstruyen** en el servidor y se **re-ensambla** el video procesado (MP4) que el servidor retorna al cliente junto con un **JSON** con métricas (tiempo por frame, FPS efectivo, colas, porcentaje de frames reintentados, etc.).

5. Para debugging, el servidor expone un **HTTP simple** (`http.server`) con un **preview** (GIF o JPGs) y **métricas en tiempo real**.

### Concurrencia y Paralelismo

- **Concurrencia**: El servidor usa `asyncio` para manejar múltiples clientes simultáneamente de manera asíncrona.
- **Paralelismo**: Los workers de Celery procesan frames en paralelo, aprovechando múltiples núcleos CPU.
- **Comunicación asíncrona**: Las entidades se comunican de manera asíncrona usando:
  - **TCP** para cliente-servidor
  - **Redis** como broker para Celery (cola de tareas distribuidas)
  - **Queues/Pipes** de `multiprocessing` para comunicación interna entre procesos locales

### Tecnologías principales

- **Python 3.11+**
- **OpenCV** (cv2): procesamiento de video y frames
- **asyncio**: servidor asíncrono
- **Celery**: cola de tareas distribuidas
- **Redis**: broker y backend para Celery
- **Docker**: despliegue en contenedores
- **argparse**: parseo de argumentos CLI
