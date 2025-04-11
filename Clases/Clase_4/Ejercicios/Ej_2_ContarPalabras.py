# Ejercicio 2: Contar palabras
# Implementa un sistema donde el proceso padre lee un archivo de texto y envía su contenido línea por línea a un proceso hijo a través de un pipe. El hijo debe contar las palabras en cada línea y devolver el resultado al padre.
import os
import sys

def parent_process(parent_read, parent_write):
    """Proceso padre: envía lineas al hijo y lee respuestas."""
    # Convertir descriptores a objetos de archivo
    with os.fdopen(parent_read) as read_pipe, os.fdopen(parent_write, 'w') as write_pipe:
        #Abrir archivo de texto
        archivo = open("/home/santiago/Documents/_dev/comp2/Clases/Clase_4/Ejercicios/texto.txt", "r")
        
        # Leer todas las lineas del archivo
        lineas = archivo.readlines()
        
        # Cerrar el archivo
        archivo.close()
        
        # Enviar lineas al hijo    
        for linea in lineas:
            print(f"Padre: Enviando linea: {linea}")
            write_pipe.write(linea.rstrip('\n') + '\n')
            write_pipe.flush()
            
            # Leer respuesta del hijo
            response = read_pipe.readline().strip()
            print(f"Padre: Recibió respuesta: {response}")
        write_pipe.close()  # <- Esto le avisa al hijo que no hay más datos


def child_process(child_read, child_write):
    """Proceso hijo: lee lineas del padre, procesa y envía respuestas."""
    # Convertir descriptores a objetos de archivo
    with os.fdopen(child_read) as read_pipe, os.fdopen(child_write, 'w') as write_pipe:
        while True:
            # Leer linea del padre
            linea = read_pipe.readline()
            if not linea:  # EOF (padre cerró su extremo de escritura)
                break
            
            linea = linea.strip()
            print(f"Hijo: Recibió linea: {linea}")
            
            # Procesar el linea y contar las palabras
            try:
                count = 0
                for word in linea.split():
                    print(f"Hijo: Contando palabras: '{word}'")
                    count += 1
                response = f"RESULT {count}"
            except Exception as e:
                response = f"ERROR {str(e)}"
            
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