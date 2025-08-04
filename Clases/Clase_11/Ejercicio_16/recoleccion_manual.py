import os
import time
import random

def child_task(child_id, sleep_time):
    """Función ejecutada por cada proceso hijo."""
    pid = os.getpid()
    ppid = os.getppid()
    print(f"Hijo {child_id} (PID: {pid}, PPID: {ppid}): Iniciando, dormiré por {sleep_time} segundos.")
    time.sleep(sleep_time)
    print(f"Hijo {child_id} (PID: {pid}): Desperté y terminaré ahora.")
    # El hijo simplemente termina su ejecución
    os._exit(0) 

def main_manual_waitpid():
    parent_pid = os.getpid()
    print(f"--- Ejercicio 16: Recolección Manual de Estado de Hijos ---")
    print(f"Proceso Padre (PID: {parent_pid}) iniciando.")

    num_children = 3
    children_info = [] # Lista para guardar (child_id, pid)
    
    # Crear los procesos hijos
    print(f"Padre: Creando {num_children} hijos.")
    for i in range(1, num_children + 1):
        # Asignar un tiempo de sueño aleatorio a cada hijo
        sleep_time = random.uniform(1, 5) 
        pid = os.fork()

        if pid == 0:  # Proceso Hijo
            child_task(i, sleep_time)
            # os._exit(0) se llama dentro de child_task
            
        else:  # Proceso Padre
            children_info.append({'id': i, 'pid': pid, 's_time': sleep_time})
            print(f"Padre: Creado Hijo {i} (PID: {pid}) que dormirá {sleep_time:.2f}s.")

    print(f"Padre: Todos los hijos creados. Hijos a esperar: {children_info}")
    print("Padre: Comenzando a recolectar estados de hijos...")

    terminated_order = [] # Lista para registrar el orden de terminación

    # Recolectar el estado de los hijos a medida que terminan
    # Bucle hasta que todos los hijos hayan sido recolectados
    while children_info:
        # os.waitpid(0, 0) espera a CUALQUIER hijo
        # pid_terminated: PID del hijo que terminó
        # status: Código de estado de salida del hijo
        try:
            pid_terminated, status = os.waitpid(0, 0) 
            
            # Encontrar la información del hijo terminado
            found_child = None
            for child in children_info:
                if child['pid'] == pid_terminated:
                    found_child = child
                    break
            
            if found_child:
                print(f"Padre: Recolectado Hijo {found_child['id']} (PID: {pid_terminated}). Estado: {status}")
                terminated_order.append(found_child['id'])
                children_info.remove(found_child) # Eliminar de la lista de hijos a esperar
            else:
                print(f"Padre: Recolectado PID desconocido {pid_terminated}. Esto no debería ocurrir en este ejemplo.")
        except ChildProcessError:
            # Esto puede ocurrir si no hay hijos esperando o si todos ya fueron recolectados
            print("Padre: No quedan hijos para recolectar.")
            break
        except Exception as e:
            print(f"Padre: Error al esperar hijo: {e}")
            break

    print("\n--- Orden de Terminación de los Hijos ---")
    print(f"Los hijos terminaron en el siguiente orden: {terminated_order}")
    print(f"Proceso Padre (PID: {parent_pid}) finalizando.")

if __name__ == "__main__":
    main_manual_waitpid()