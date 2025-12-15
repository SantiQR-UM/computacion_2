# Guía de Instalación Completa

Esta guía te lleva paso a paso desde cero hasta tener el sistema funcionando.

## Requisitos del Sistema

- **Sistema Operativo**: Linux, macOS o Windows 10/11
- **RAM**: Mínimo 4GB, recomendado 8GB
- **Disco**: Al menos 2GB libres
- **Conexión a Internet**: Para descargar dependencias

---

## Instalación Paso a Paso

### 1. Instalar Python 3.11+

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

#### macOS
```bash
brew install python@3.11
```

#### Windows
Descargar desde https://www.python.org/downloads/ y ejecutar el instalador.
**IMPORTANTE**: Marcar la opción "Add Python to PATH"

### 2. Instalar Docker y Docker Compose

#### Linux (Ubuntu/Debian)
```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Añadir usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo apt install docker-compose-plugin
```

#### macOS
Descargar e instalar Docker Desktop desde https://www.docker.com/products/docker-desktop/

#### Windows
Descargar e instalar Docker Desktop desde https://www.docker.com/products/docker-desktop/

**Verificar instalación:**
```bash
docker --version
docker compose version
```

### 3. Clonar el Repositorio

```bash
git clone <url-del-repositorio>
cd FINAL
```

### 4. Crear y Activar Entorno Virtual

#### Linux/macOS
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### Windows (CMD)
```bash
python -m venv .venv
.venv\Scripts\activate.bat
```

### 5. Instalar Dependencias Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Verificar Instalación

```bash
# Verificar Python
python --version  # Debe mostrar 3.11 o superior

# Verificar dependencias
python -c "import cv2; import celery; print('OK')"

# Verificar Docker
docker ps
```

---

## Primera Ejecución

### Con Docker (Recomendado)

```bash
cd docker
docker-compose up --build
```

Por defecto lanza **4 workers**. Para cambiar el número de workers:
```bash
# 2 workers
docker-compose up --build --scale worker=2

# 8 workers
docker-compose up --build --scale worker=8

# 1 worker
docker-compose up --build --scale worker=1
```

Espera a que todos los servicios estén corriendo. Deberías ver:
```
video_redis    | Ready to accept connections
video_server   | Servidor IPv6 escuchando en: ('::', 9090, 0, 0)
video_server   | Servidor IPv4 escuchando en: ('0.0.0.0', 9090)
video_preview  | Iniciando Preview Server en http://0.0.0.0:8080
worker_1       | [INFO/MainProcess] Connected to redis://redis:6379/0
worker_2       | [INFO/MainProcess] Connected to redis://redis:6379/0
...
```

### Sin Docker

**Terminal 1 - Redis:**
```bash
# Linux/macOS
sudo systemctl start redis
# o
redis-server

# Verificar
redis-cli ping  # Debe responder PONG
```

**Terminal 2 - Servidor:**
```bash
source .venv/bin/activate  # Linux/macOS
# o
.venv\Scripts\activate  # Windows

python src/server.py --bind :: --port 9090
```

**Terminales 3-6 - Workers:**
```bash
source .venv/bin/activate  # En cada terminal

celery -A src.worker.app worker --loglevel=INFO -Q frames -n worker1@%h
celery -A src.worker.app worker --loglevel=INFO -Q frames -n worker2@%h
celery -A src.worker.app worker --loglevel=INFO -Q frames -n worker3@%h
celery -A src.worker.app worker --loglevel=INFO -Q frames -n worker4@%h
```

---

## Probar el Sistema

### Generar Video de Prueba

```bash
source .venv/bin/activate  # Linux/macOS
# o
.venv\Scripts\activate  # Windows

python generate_test_video.py --output test_video.mp4 --duration 3
```

### Procesar el Video

**Con IPv4:**
```bash
python src/client.py --host 127.0.0.1 --ipv4 --video test_video.mp4 --processing blur --out output_blur.mp4
```

**Con IPv6:**
```bash
python src/client.py --host ::1 --ipv6 --video test_video.mp4 --processing edges --out output_edges.mp4
```

Si todo funciona, verás una barra de progreso y el video procesado se guardará.

---

## Configuración Avanzada

### Variables de Entorno

Crear archivo `.env` en el directorio raíz:

```bash
REDIS_URL=redis://localhost:6379/0
PYTHONUNBUFFERED=1
```

### Escalar Workers

El sistema permite escalar dinámicamente el número de workers sin modificar archivos:

```bash
# Lanzar con N workers (recomendado: 4-8 para videos normales)
docker-compose up --scale worker=N

# Ejemplos:
docker-compose up --scale worker=2   # Para máquinas con pocos recursos
docker-compose up --scale worker=8   # Para procesamiento rápido
docker-compose up --scale worker=16  # Para videos largos o múltiples clientes
```

**Nota**: Más workers = más rápido, pero consume más RAM (aprox. 200-300MB por worker).

---

## Solución de Problemas

### "No se pudo conectar a Redis"
```bash
# Verificar que Redis está corriendo
redis-cli ping

# Si no responde, iniciar Redis
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

### "Port 9090 already in use"
```bash
# Usar otro puerto
python src/server.py --port 9091
python src/client.py --port 9091 ...
```

### "No module named 'cv2'"
```bash
pip install opencv-python
```

### Docker: "Cannot connect to the Docker daemon"
```bash
# Linux
sudo systemctl start docker

# Verificar que tu usuario está en el grupo docker
groups | grep docker
```

### Windows: Error con paths largos
Ejecutar PowerShell como administrador:
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

---

## Desinstalación

### Con Docker
```bash
cd docker
docker-compose down -v
docker system prune -a
```

### Sin Docker
```bash
# Detener Redis
sudo systemctl stop redis

# Desactivar venv
deactivate

# Eliminar directorio
cd ..
rm -rf FINAL
```

---

## Próximos Pasos

Una vez instalado, consulta [QUICKSTART.md](QUICKSTART.md) para uso diario.
