# Ejercicio 4: Simulador de Shell
# Implementa un programa que simule una versión simplificada del operador pipe (|) de la shell. El programa debe ejecutar dos comandos proporcionados por el usuario y conectar la salida del primero con la entrada del segundo.
import os
import sys
import subprocess

def simulate_pipe(cmd1, cmd2):
    """
    Simula el operador pipe (|) de la shell conectando
    la salida de cmd1 con la entrada de cmd2.
    """
    # Crear un pipe
    read_fd, write_fd = os.pipe()
    
    # Bifurcar para el primer comando
    pid1 = os.fork()
    
    if pid1 == 0:  # Proceso hijo para cmd1
        # Redirigir stdout al extremo de escritura del pipe
        os.close(read_fd)  # Cerrar el extremo de lectura que no usamos
        os.dup2(write_fd, sys.stdout.fileno())  # Redirigir stdout
        os.close(write_fd)  # Cerrar el descriptor original ahora que está duplicado
        
        # Ejecutar el primer comando
        try:
            cmd1_parts = cmd1.split()
            os.execvp(cmd1_parts[0], cmd1_parts)
        except Exception as e:
            print(f"Error executing {cmd1}: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Bifurcar para el segundo comando
    pid2 = os.fork()
    
    if pid2 == 0:  # Proceso hijo para cmd2
        # Redirigir stdin al extremo de lectura del pipe
        os.close(write_fd)  # Cerrar el extremo de escritura que no usamos
        os.dup2(read_fd, sys.stdin.fileno())  # Redirigir stdin
        os.close(read_fd)  # Cerrar el descriptor original ahora que está duplicado
        
        # Ejecutar el segundo comando
        try:
            cmd2_parts = cmd2.split()
            os.execvp(cmd2_parts[0], cmd2_parts)
        except Exception as e:
            print(f"Error executing {cmd2}: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Proceso padre: cerrar ambos extremos del pipe y esperar
    os.close(read_fd)
    os.close(write_fd)
    
    # Esperar a que ambos procesos terminen
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)

def main():
    print("Simulador de Pipes de Shell")
    print("Ingrese 'exit' para salir")
    print("Ejemplo: ls -l | grep .py")
    
    while True:
        try:
            user_input = input("\n$ ")
            
            if user_input.lower() == 'exit':
                break
            
            # Verificar si el input contiene el operador pipe
            if '|' not in user_input:
                print("Error: Debe incluir el operador '|' para conectar dos comandos")
                continue
            
            # Dividir la entrada en dos comandos
            cmd1, cmd2 = [cmd.strip() for cmd in user_input.split('|', 1)]
            
            if not cmd1 or not cmd2:
                print("Error: Debe proporcionar dos comandos válidos")
                continue
            
            print(f"Ejecutando: '{cmd1}' | '{cmd2}'")
            simulate_pipe(cmd1, cmd2)
            
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Saliendo del simulador")

if __name__ == "__main__":
    main()