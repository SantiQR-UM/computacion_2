import multiprocessing
import os
import time

# Usaremos un Value compartido para el contador
shared_counter_fixed = multiprocessing.Value('i', 0)
# Creamos un Lock para proteger el acceso al contador
counter_lock = multiprocessing.Lock()

def increment_counter_with_lock(iterations, lock):
    global shared_counter_fixed
    pid = os.getpid()
    print(f"Proceso {pid} (con lock) iniciando.")
    for _ in range(iterations):
        # Adquirir el lock antes de acceder al contador
        lock.acquire()
        try:
            current_value = shared_counter_fixed.value
            # time.sleep(0.0001) # Quitar esta pausa o dejarla mínima para no afectar rendimiento con lock
            shared_counter_fixed.value = current_value + 1
        finally:
            # Liberar el lock después de acceder al contador
            lock.release()
    print(f"Proceso {pid} (con lock) finalizando. Contador final: {shared_counter_fixed.value}")

def main_race_condition_fixed():
    print("--- Demostración de Condición de Carrera Corregida (Con Lock) ---")

    # Reiniciar el contador para cada ejecución
    shared_counter_fixed.value = 0
    
    num_processes = 2
    iterations_per_process = 100000 
    
    processes = []
    # El lock se pasa como argumento a los procesos
    for _ in range(num_processes):
        p = multiprocessing.Process(target=increment_counter_with_lock, args=(iterations_per_process, counter_lock))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    expected_value = num_processes * iterations_per_process
    print(f"Valor final del contador (con lock): {shared_counter_fixed.value}")
    print(f"Valor esperado: {expected_value}")
    if shared_counter_fixed.value == expected_value:
        print("¡CORRECTO: El problema de la condición de carrera ha sido solucionado!")
    else:
        print("ERROR: La condición de carrera aún persiste o hay otro problema.")
    print("-" * 50)

if __name__ == "__main__":
    # Puedes ejecutar ambos main_ functions aquí para comparar, o en scripts separados
    #main_race_condition()
    print("\n") # Espacio para separar resultados
    main_race_condition_fixed()