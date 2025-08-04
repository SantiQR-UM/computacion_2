import multiprocessing
import os
import time
import random

def access_resource(process_id, semaphore):
    """
    Función que simula el intento de acceso a un recurso limitado.
    """
    pid = os.getpid()
    print(f"Proceso {process_id} (PID: {pid}) intentando acceder al recurso...")
    
    # Intentar adquirir un "permiso" del semáforo
    # Esto se bloqueará si no hay permisos disponibles
    semaphore.acquire() 
    try:
        print(f"Proceso {process_id} (PID: {pid}) HA ACCEDIDO al recurso.")
        # Simular trabajo en la zona crítica
        work_time = random.uniform(0.5, 2.0)
        time.sleep(work_time)
        print(f"Proceso {process_id} (PID: {pid}) liberando el recurso después de {work_time:.2f} segundos.")
    finally:
        # Asegurarse de liberar el "permiso" del semáforo
        semaphore.release()
    print(f"Proceso {process_id} (PID: {pid}) ha salido de la zona crítica.")

def main_semaphore():
    print("--- Demostración de Semáforo (Puestos Limitados) ---")
    
    num_processes = 10
    max_concurrent_accesses = 3 # Número máximo de procesos permitidos simultáneamente

    # Crear un semáforo con un valor inicial de 3.
    # Esto significa que 3 procesos pueden adquirir el semáforo simultáneamente.
    semaphore = multiprocessing.Semaphore(max_concurrent_accesses)

    processes = []
    print(f"Creando {num_processes} procesos que intentarán acceder a {max_concurrent_accesses} puestos limitados...")
    
    for i in range(num_processes):
        p = multiprocessing.Process(target=access_resource, args=(i + 1, semaphore))
        processes.append(p)
        p.start()

    # Esperar a que todos los procesos terminen
    for p in processes:
        p.join()

    print("Todos los procesos han terminado. Demostración de semáforo finalizada.")
    print("-" * 50)

if __name__ == "__main__":
    main_semaphore()