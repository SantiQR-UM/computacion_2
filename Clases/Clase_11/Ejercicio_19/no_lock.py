import multiprocessing
import os
import time

LOG_FILE_NO_LOCK = "concurrent_output_no_lock.txt"

def write_data_no_lock(process_id, num_writes):
    """
    Función que escribe datos en un archivo sin usar un lock.
    """
    pid = os.getpid()
    print(f"Proceso {process_id} (PID: {pid}) iniciando escritura sin lock.")
    
    with open(LOG_FILE_NO_LOCK, 'a') as f: # 'a' para append
        for i in range(num_writes):
            # Simular una escritura no atómica de varias líneas
            line1 = f"P{process_id}-L1: {i+1} de {num_writes}\n"
            line2 = f"P{process_id}-L2: {i+1} de {num_writes}\n"
            
            f.write(line1)
            time.sleep(0.00001) # Pequeña pausa para aumentar la probabilidad de interleaving
            f.write(line2)
            time.sleep(0.00001)

    print(f"Proceso {process_id} (PID: {pid}) finalizando escritura sin lock.")

def main_no_lock():
    print("--- Ejercicio 19: Escritura Concurrente SIN Exclusión (Condición de Carrera) ---")
    if os.path.exists(LOG_FILE_NO_LOCK):
        os.remove(LOG_FILE_NO_LOCK)
        print(f"Limpiado archivo de log: {LOG_FILE_NO_LOCK}")

    num_processes = 3
    writes_per_process = 500 # Cada proceso escribirá 500 veces (2 líneas por vez)

    processes = []
    print(f"Creando {num_processes} procesos que escribirán {writes_per_process} veces cada uno sin lock...")
    
    for i in range(num_processes):
        p = multiprocessing.Process(target=write_data_no_lock, args=(i + 1, writes_per_process))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print("\nTodos los procesos sin lock han terminado.")
    print(f"Contenido final de '{LOG_FILE_NO_LOCK}':")
    # Imprimir las primeras y últimas líneas para no inundar la consola
    with open(LOG_FILE_NO_LOCK, 'r') as f:
        lines = f.readlines()
        print(f"Total de líneas esperadas: {num_processes * writes_per_process * 2}")
        print(f"Total de líneas reales: {len(lines)}")
        print("\nPrimeras 10 líneas:")
        for line in lines[:10]:
            print(line.strip())
        print("...")
        print("Últimas 10 líneas:")
        for line in lines[-10:]:
            print(line.strip())
    
    print("\n¡Analiza el archivo 'concurrent_output_no_lock.txt' para ver la corrupción de datos!")
    print("-" * 70)

if __name__ == "__main__":
    main_no_lock()