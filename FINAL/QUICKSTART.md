# Guía de Inicio Rápido

Guía para usar el sistema cuando ya está instalado. Si es tu primera vez, consulta [INSTALL.md](INSTALL.md).

---

## Iniciar el Sistema

### 1. Activar Entorno Virtual

#### Linux/macOS
```bash
cd FINAL
source .venv/bin/activate
```

#### Windows (PowerShell)
```bash
cd FINAL
.venv\Scripts\Activate.ps1
```

#### Windows (CMD)
```bash
cd FINAL
.venv\Scripts\activate.bat
```

### 2. Levantar Docker

```bash
cd docker
docker compose up
```

Si es la primera vez después de cambios en el código:
```bash
docker compose up --build
```

**Configurar número de workers** (por defecto: 4):
```bash
# 2 workers (para máquinas con pocos recursos)
docker compose up --scale worker=2

# 8 workers (para procesamiento rápido)
docker compose up --scale worker=8

# 16 workers (para videos largos o alta carga)
docker compose up --scale worker=16
```

**Espera a que veas:**
```
video_server   | Servidor IPv6 escuchando en: ('::', 9090, 0, 0)
video_server   | Servidor IPv4 escuchando en: ('0.0.0.0', 9090)
video_preview  | Iniciando Preview Server en http://0.0.0.0:8080
```

**Monitorear progreso en tiempo real:**
- Abre tu navegador en `http://localhost:8080`
- Verás un dashboard con el progreso de cada video procesándose
- Incluye: frames procesados, FPS, ETA, y preview en GIF

---

## Procesar Videos

### Generar Video de Prueba (opcional)

```bash
python generate_test_video.py --output test.mp4 --duration 3
```

### Procesar con IPv4

```bash
python src/client.py --host 127.0.0.1 --ipv4 --video test.mp4 --processing blur --out output_2.mp4
```

### Procesar con IPv6

```bash
python src/client.py --host ::1 --ipv6 --video test.mp4 --processing edges --out output_3.mp4
```

---

## Tipos de Procesamiento

### Blur
```bash
python src/client.py --host 127.0.0.1 --ipv4 --video input.mp4 --processing blur --out blur.mp4
```

### Edges (Detección de Bordes)
```bash
python src/client.py --host 127.0.0.1 --ipv4 --video input.mp4 --processing edges --out edges.mp4
```

### Faces (Detección de Rostros)
```bash
python src/client.py --host ::1 --ipv6 --video input.mp4 --processing faces --out faces.mp4
```

### Motion (Detección de Movimiento)
```bash
python src/client.py --host ::1 --ipv6 --video input.mp4 --processing motion --out motion.mp4
```

---

## Detener el Sistema

### Detener Docker
```
Ctrl + C
```

O en otra terminal:
```bash
cd docker
docker compose down
```

### Desactivar Entorno Virtual
```bash
deactivate
```

---

## Comandos Útiles

### Ver Logs en Tiempo Real
```bash
docker compose logs -f
```

### Ver Solo Logs del Servidor
```bash
docker compose logs -f server
```

### Ver Solo Logs de Workers
```bash
docker compose logs -f worker1 worker2 worker3 worker4
```

### Reiniciar un Servicio
```bash
docker compose restart server
```

### Escalar Workers
```bash
# Cambiar dinámicamente el número de workers
docker compose up --scale worker=8

# Reiniciar con diferente cantidad
docker compose down
docker compose up --scale worker=16
```

---

## Verificación Rápida

### Redis
```bash
redis-cli ping
```
Debe responder: `PONG`

### Servidor
```bash
# IPv4
nc -zv 127.0.0.1 9090

# IPv6
nc -6 -zv ::1 9090
```

---

Eso es todo. Para más detalles, consulta [README.md](README.md).
