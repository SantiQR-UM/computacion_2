# Ejecutar despues de leer_fifo_os.py
import os

fd = os.open('/tmp/test_fifo', os.O_WRONLY)
os.write(fd, b'Hola desde os.write\n')
os.write(fd, b'Hola 2 desde os.write\n') # No va a ser leida por el lector
os.close(fd)