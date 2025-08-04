# Lector Fifo que va a esperar hasta que exista un escritor
# Primero ejecutar "mkfifo /tmp/test_fifo"
# Despues ejecutar escribir_fifo_os.py
import os

fd = os.open('/tmp/test_fifo', os.O_RDONLY)
data = os.read(fd, 1024)
print('Lectura:', data.decode())
os.close(fd)