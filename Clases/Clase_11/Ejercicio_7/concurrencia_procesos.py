import multiprocessing
import os
import time
from datetime import datetime

LOG_FILE = "concurrent_log.txt"

def write_log(process_id, lock):
    """
    Función que será ejecutada por cada proceso hijo.
    Escribe su PID y una marca de tiempo en el archivo de log.
    """
    pid = os.getpid()
    print(f"Proceso {process_id} (PID: {pid}) iniciando...")
    
    for i in range(3): # Cada proceso escribe 3 veces
        # Adquirir el lock antes de acceder al recurso compartido (el archivo)
        lock.acquire()
        try:
            with open(LOG_FILE, 'a') as f: # 'a' para modo append (agregar al final)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                log_entry = f"Proceso: {process_id}, PID: {pid}, Iteración: {i+1}, Tiempo: {timestamp}\n"
                f.write(log_entry)
            print(f"Proceso {process_id}: Escribió entrada {i+1}")
        finally:
            # Asegurarse de liberar el lock, incluso si ocurre un error
            lock.release()
        
        time.sleep(0.1) # Pequeña pausa para simular trabajo y aumentar probabilidad de contención

    print(f"Proceso {process_id} (PID: {pid}) finalizando.")

def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE) # Limpiar el log anterior
        print(f"Archivo de log '{LOG_FILE}' limpiado.")

    num_processes = 4
    processes = []
    
    # Crear un objeto Lock que será compartido por todos los procesos
    # Este Lock debe pasarse como argumento a la función de los procesos
    lock = multiprocessing.Lock()

    print(f"Creando {num_processes} procesos...")
    for i in range(num_processes):
        # target es la función que ejecutará el proceso
        # args es una tupla de argumentos para la función target
        p = multiprocessing.Process(target=write_log, args=(i + 1, lock))
        processes.append(p)
        p.start() # Iniciar el proceso

    # Esperar a que todos los procesos terminen
    for p in processes:
        p.join()

    print("Todos los procesos han terminado.")
    print(f"Contenido final del archivo de log '{LOG_FILE}':")
    with open(LOG_FILE, 'r') as f:
        print(f.read())

if __name__ == "__main__":
    main()