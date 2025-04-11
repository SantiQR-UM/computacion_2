import os
import sys

def parent_process(parent_read, parent_write):
    """Proceso padre: envía comandos al hijo y lee respuestas."""
    # Convertir descriptores a objetos de archivo
    with os.fdopen(parent_read) as read_pipe, os.fdopen(parent_write, 'w') as write_pipe:
        # Enviar algunos comandos al hijo
        commands = ["HELLO", "ECHO This is a test", "CALCULATE 5 + 7", "EXIT"]
        
        for command in commands:
            print(f"Padre: Enviando comando: {command}")
            write_pipe.write(f"{command}\n")
            write_pipe.flush()
            
            # Leer respuesta del hijo
            response = read_pipe.readline().strip()
            print(f"Padre: Recibió respuesta: {response}")
            
            if command == "EXIT":
                break

def child_process(child_read, child_write):
    """Proceso hijo: lee comandos del padre, procesa y envía respuestas."""
    # Convertir descriptores a objetos de archivo
    with os.fdopen(child_read) as read_pipe, os.fdopen(child_write, 'w') as write_pipe:
        while True:
            # Leer comando del padre
            command = read_pipe.readline().strip()
            if not command:  # EOF (padre cerró su extremo de escritura)
                break
                
            print(f"Hijo: Recibió comando: {command}")
            
            # Procesar el comando
            if command == "HELLO":
                response = "GREETING Hello from child process!"
            elif command.startswith("ECHO "):
                response = "ECHOED " + command[5:]
            elif command.startswith("CALCULATE "):
                # Evaluar expresión matemática simple
                try:
                    expression = command[10:]
                    result = eval(expression)
                    response = f"RESULT {result}"
                except Exception as e:
                    response = f"ERROR {str(e)}"
            elif command == "EXIT":
                response = "GOODBYE"
                # Enviar respuesta y salir
                write_pipe.write(f"{response}\n")
                write_pipe.flush()
                break
            else:
                response = f"UNKNOWN command: {command}"
            
            # Enviar respuesta al padre
            write_pipe.write(f"{response}\n")
            write_pipe.flush()

def main():
    # Crear pipes para comunicación bidireccional
    # Pipe para mensajes del padre al hijo
    parent_to_child_r, parent_to_child_w = os.pipe()
    
    # Pipe para mensajes del hijo al padre
    child_to_parent_r, child_to_parent_w = os.pipe()
    
    # Bifurcar el proceso
    pid = os.fork()
    
    if pid > 0:  # Proceso padre
        # Cerrar extremos no utilizados
        os.close(parent_to_child_r)
        os.close(child_to_parent_w)
        
        # Ejecutar lógica del padre
        parent_process(child_to_parent_r, parent_to_child_w)
        
        # Esperar a que el hijo termine
        os.waitpid(pid, 0)
        print("Padre: El proceso hijo ha terminado.")
        
    else:  # Proceso hijo
        # Cerrar extremos no utilizados
        os.close(parent_to_child_w)
        os.close(child_to_parent_r)
        
        # Ejecutar lógica del hijo
        child_process(parent_to_child_r, child_to_parent_w)
        
        print("Hijo: Terminando.")
        sys.exit(0)

if __name__ == "__main__":
    main()