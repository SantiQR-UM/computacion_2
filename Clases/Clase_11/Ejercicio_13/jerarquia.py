import os
import time

def child_process_function(child_id):
    """Función ejecutada por los procesos hijos."""
    pid = os.getpid()
    ppid = os.getppid()
    print(f"Soy el Hijo {child_id}. Mi PID es {pid}, mi PPID es {ppid}.")
    print(f"Hijo {child_id} (PID: {pid}) esperando 30 segundos para ser observado...")
    time.sleep(30) # El hijo espera para que podamos observarlo
    print(f"Hijo {child_id} (PID: {pid}) terminando.")

def main_process_hierarchy():
    pid_parent = os.getpid()
    print(f"--- Ejercicio 13: Visualización de Jerarquía de Procesos ---")
    print(f"Soy el proceso Padre. Mi PID es {pid_parent}.")
    print("Creando dos procesos hijos...")

    # Lista para guardar los PIDs de los hijos
    child_pids = []

    # Crear el primer hijo
    pid1 = os.fork()
    if pid1 == 0: # Es el primer hijo
        child_process_function(1)
        os._exit(0) # El hijo debe terminar
    else:
        child_pids.append(pid1)

    # Crear el segundo hijo
    pid2 = os.fork()
    if pid2 == 0: # Es el segundo hijo
        child_process_function(2)
        os._exit(0) # El hijo debe terminar
    else:
        child_pids.append(pid2)

    print(f"Padre (PID: {pid_parent}) ha creado hijos con PIDs: {child_pids}")
    print(f"Padre (PID: {pid_parent}) esperando 40 segundos para que observes la jerarquía...")
    print("Usa 'pstree -p' y 'ps --forest' en otra terminal.")
    
    time.sleep(40) # El padre espera más tiempo que los hijos
    
    print("Padre: Ahora recolectando a mis hijos.")
    # El padre espera a todos sus hijos
    for child_pid in child_pids:
        try:
            status = os.waitpid(child_pid, 0)
            print(f"Padre: Hijo {status[0]} terminado.")
        except ChildProcessError:
            print(f"Padre: Hijo {child_pid} ya no existe (probablemente adoptado por init/systemd).")

    print(f"Padre (PID: {pid_parent}) terminando.")

if __name__ == "__main__":
    main_process_hierarchy()