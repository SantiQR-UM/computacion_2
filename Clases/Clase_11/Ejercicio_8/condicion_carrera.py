import multiprocessing
import os
import time

# Usaremos un Value compartido para el contador
# 'i' para entero, 0 para valor inicial
shared_counter = multiprocessing.Value('i', 0) 

def increment_counter_no_lock(iterations):
    global shared_counter
    pid = os.getpid()
    print(f"Proceso {pid} (sin lock) iniciando.")
    for _ in range(iterations):
        # Acceso no sincronizado al contador compartido
        current_value = shared_counter.value
        time.sleep(0.0001) # Pequeña pausa para aumentar la probabilidad de carrera
        shared_counter.value = current_value + 1
    print(f"Proceso {pid} (sin lock) finalizando. Contador final: {shared_counter.value}")

def main_race_condition():
    print("--- Demostración de Condición de Carrera (Sin Lock) ---")
    
    # Reiniciar el contador para cada ejecución
    shared_counter.value = 0 
    
    num_processes = 2
    iterations_per_process = 100000 # Un número grande para asegurar la carrera
    
    processes = []
    for _ in range(num_processes):
        p = multiprocessing.Process(target=increment_counter_no_lock, args=(iterations_per_process,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    expected_value = num_processes * iterations_per_process
    print(f"Valor final del contador (sin lock): {shared_counter.value}")
    print(f"Valor esperado: {expected_value}")
    if shared_counter.value != expected_value:
        print("¡ADVERTENCIA: Condición de carrera detectada! El valor es INCORRECTO.")
    else:
        print("Resultado CORRECTO (raro, vuelve a ejecutarlo o aumenta las iteraciones).")
    print("-" * 50)

if __name__ == "__main__":
    main_race_condition()