import os
import time

def crear_hijo(nombre):
    pid = os.fork()

    if pid == 0:
        print(f"[HIJO {nombre}] PID: {os.getpid()}")
        time.sleep(1)
        os._exit(0)
        
    else:
        os.wait()

crear_hijo("A")
crear_hijo("B")