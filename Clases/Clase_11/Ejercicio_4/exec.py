import os
import sys
import time

def exec_replacement_example():
    pid = os.fork()

    if pid == 0:  # Proceso Hijo
        print(f"Soy el proceso hijo (PID: {os.getpid()}). Mi PPID es: {os.getppid()}")
        print("El hijo va a reemplazar su imagen de ejecución con 'ls -l'.")
        
        # Reemplazar la imagen del proceso hijo con 'ls -l'
        # os.execlp("ls", "ls", "-l", "/tmp") # Ejemplo usando un directorio específico
        os.execlp("ls", "ls", "-l") # Ejecuta 'ls -l' en el directorio actual
        
        # Esta línea no se ejecutará si exec() es exitoso
        print("Esto no debería imprimirse si exec() fue exitoso.")
        sys.exit(1) # Si exec() falla por alguna razón, el hijo termina con error
    else:  # Proceso Padre
        print(f"Soy el proceso padre (PID: {os.getpid()}). Mi hijo tiene PID: {pid}")
        print("El padre esperará a que el hijo termine.")
        
        # El padre espera al hijo para recolectar su estado y evitar un zombi
        status = os.waitpid(pid, 0)
        print(f"El proceso hijo (PID: {status[0]}) ha terminado con estado: {status[1]}")
        print("El padre termina.")

if __name__ == "__main__":
    exec_replacement_example()