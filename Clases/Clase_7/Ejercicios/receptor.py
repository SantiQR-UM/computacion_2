import signal
import time
import os

def aviso(signum, frame):
    print("Recibí el aviso ✉️ (SIGUSR1) y sigo tranquilo...")

# Asociamos la señal SIGUSR1 a la función personalizada
signal.signal(signal.SIGUSR1, aviso)

print(f"{os.getpid()} Esperando señales...")
while True:
    time.sleep(1)
