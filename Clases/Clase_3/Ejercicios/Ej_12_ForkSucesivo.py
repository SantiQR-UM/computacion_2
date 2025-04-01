import os
import time

# Num de hijos inicial
h = 1
# Num de sucesiones máximo
s = 10

def crear_hijo_recursivo(h, padre):
    if h > s:  # Condición de salida
        return
        
    pid = os.fork()
    
    if pid == 0:  # Proceso hijo
        actual = os.getpid()
        print(f"Soy el hijo {h} y mi pid es: {actual}, y el de mi padre es: {padre}")
        time.sleep(5)
        crear_hijo_recursivo(h+1, actual) # ERROR si uso -
        os._exit(0) 
    
    else:  # Proceso padre
        os.waitpid(pid, 0)  # Esperar a que el hijo termine

print(f"Soy el padre {os.getpid()}")

crear_hijo_recursivo(h, os.getpid())