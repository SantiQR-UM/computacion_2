import multiprocessing
import os
import time

LOG_FILE_WITH_LOCK = "concurrent_output_with_lock.txt"

def write_data_with_lock(process_id, num_writes, lock):
    """
    Función que escribe datos en un archivo usando un lock para sincronización.
    """
    pid = os.getpid()
    print(f"Proceso {process_id} (PID: {pid}) iniciando escritura CON lock.")
    
    for i in range(num_writes):
        # Adquirir el lock antes de acceder al recurso compartido (el archivo)
        lock.acquire()
        try:
            with open(LOG_FILE_WITH_LOCK, 'a') as f: # 'a' para append
                # Escribir un bloque de líneas que debe ser atómico
                line1 = f"P{process_id}-L1: {i+1} de {num_writes}\n"
                line2 = f"P{process_id}-L2: {i+1} de {num_writes}\n"
                
                f.write(line1)
                # La pausa aquí simula una operación compleja o lenta.
                # Con el lock, no hay problema de interleaving.
                time.sleep(0.00001) 
                f.write(line2)
                time.sleep(0.00001)
        finally:
            # Asegurarse de liberar el lock, incluso si ocurre un error
            lock.release()
    
    print(f"Proceso {process_id} (PID: {pid}) finalizando escritura CON lock.")

def main_with_lock():
    print("--- Ejercicio 19: Escritura Concurrente CON Exclusión (Corregido con Lock) ---")
    if os.path.exists(LOG_FILE_WITH_LOCK):
        os.remove(LOG_FILE_WITH_LOCK)
        print(f"Limpiado archivo de log: {LOG_FILE_WITH_LOCK}")

    num_processes = 3
    writes_per_process = 500 # Cada proceso escribirá 500 veces (2 líneas por vez)

    processes = []
    
    # Crear un objeto Lock que será compartido por todos los procesos
    file_lock = multiprocessing.Lock()

    print(f"Creando {num_processes} procesos que escribirán {writes_per_process} veces cada uno CON lock...")
    
    for i in range(num_processes):
        # Pasar el lock como argumento a la función target
        p = multiprocessing.Process(target=write_data_with_lock, args=(i + 1, writes_per_process, file_lock))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print("\nTodos los procesos CON lock han terminado.")
    print(f"Contenido final de '{LOG_FILE_WITH_LOCK}':")
    
    with open(LOG_FILE_WITH_LOCK, 'r') as f:
        lines = f.readlines()
        expected_lines = num_processes * writes_per_process * 2
        print(f"Total de líneas esperadas: {expected_lines}")
        print(f"Total de líneas reales: {len(lines)}")
        
        # Verificar integridad: cada L1 debe ser seguido por su L2
        corrupted_blocks = 0
        for j in range(0, len(lines), 2):
            if j + 1 < len(lines):
                # Extraer ID de proceso e iteración de L1
                try:
                    parts1 = lines[j].strip().split(': ')
                    proc_id1 = parts1[0].split('-')[0]
                    iter_val1 = parts1[1].split(' ')[0]

                    # Extraer ID de proceso e iteración de L2
                    parts2 = lines[j+1].strip().split(': ')
                    proc_id2 = parts2[0].split('-')[0]
                    iter_val2 = parts2[1].split(' ')[0]

                    if not (proc_id1 == proc_id2 and iter_val1 == iter_val2 and 'L1' in lines[j] and 'L2' in lines[j+1]):
                        corrupted_blocks += 1
                except IndexError:
                    corrupted_blocks += 1 # Malformación de línea

        if corrupted_blocks == 0 and len(lines) == expected_lines:
            print("\n¡El archivo está CORRECTO y SIN CORRUPCIÓN de datos!")
        else:
            print(f"\n¡ADVERTENCIA: El archivo podría contener corrupción o un número incorrecto de líneas! Bloques corruptos detectados: {corrupted_blocks}")

        print("\nPrimeras 10 líneas:")
        for line in lines[:10]:
            print(line.strip())
        print("...")
        print("Últimas 10 líneas:")
        for line in lines[-10:]:
            print(line.strip())
    
    print("-" * 70)

if __name__ == "__main__":
    main_with_lock()