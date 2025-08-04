import os
import time
import random
import argparse
import multiprocessing
import subprocess

# --- Función que ejecutará cada proceso hijo ---
def proceso_hijo():
    """
    Esta es la función de trabajo para cada proceso hijo.
    Imprime su PID, duerme un tiempo aleatorio y termina.
    """
    pid = os.getpid()
    ppid = os.getppid()
    
    print(f"    -> [Hijo PID: {pid}] Mi padre es PID: {ppid}.")
    
    tiempo_sleep = random.uniform(1, 5)
    print(f"    -> [Hijo PID: {pid}] Voy a dormir por {tiempo_sleep:.2f} segundos.")
    
    time.sleep(tiempo_sleep)
    
    print(f"    -> [Hijo PID: {pid}] Terminé.")

# --- Bloque principal que se ejecuta al llamar al script ---
if __name__ == "__main__":
    # 1. Configuración de los argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Crea y gestiona procesos hijos.")
    parser.add_argument("--num", type=int, required=True, help="Número de procesos hijos a crear.")
    parser.add_argument("--verbose", action="store_true", help="Activa mensajes detallados.")
    
    args = parser.parse_args()

    # 2. Lógica del Proceso Padre
    pid_padre = os.getpid()
    print(f"[Padre PID: {pid_padre}] Iniciando gestor de procesos.")

    procesos = [] # Lista para mantener los objetos de proceso

    # 3. Creación y lanzamiento de los procesos hijos
    for i in range(args.num):
        if args.verbose:
            print(f"[Padre PID: {pid_padre}] Creando hijo N°{i+1}...")
        
        # Se crea el objeto Proceso, asignando la función 'proceso_hijo'
        proceso = multiprocessing.Process(target=proceso_hijo)
        procesos.append(proceso)
        proceso.start() # Inicia la ejecución del proceso hijo

    if args.verbose:
        print(f"\n[Padre PID: {pid_padre}] {args.num} hijos han sido creados y están ejecutándose.")

    # 4. Espera a que todos los procesos hijos terminen
    for proceso in procesos:
        proceso.join() # El padre se bloquea aquí hasta que el hijo termine

    print(f"\n[Padre PID: {pid_padre}] Todos los procesos hijos han terminado.")

    # 5. Muestra la jerarquía de procesos final
    print("\n--- Jerarquía de Procesos (usando pstree) ---")
    try:
        # Ejecuta el comando 'pstree -p <PID_PADRE>'
        resultado_pstree = subprocess.run(
            ["pstree", "-p", str(pid_padre)], 
            capture_output=True, 
            text=True,
            check=True
        )
        print(resultado_pstree.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: El comando 'pstree' no se encontró o falló.")
        print("Asegúrate de tenerlo instalado (ej: 'sudo apt-get install psmisc')")