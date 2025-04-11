# Ejercicio 6: Servidor de Matemáticas
# Crea un "servidor" de operaciones matemáticas usando pipes. El proceso cliente envía operaciones matemáticas como cadenas (por ejemplo, "5 + 3", "10 * 2"), y el servidor las evalúa y devuelve el resultado. Implementa manejo de errores para operaciones inválidas.
import os
import sys
import math
import time
import signal

def setup_signal_handler():
    """Configura el manejador de señales para salir limpiamente con Ctrl+C"""
    def signal_handler(sig, frame):
        print("\nFinalizando servidor...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

def servidor(read_pipe, write_pipe):
    """Función del servidor: recibe operaciones y las evalúa"""
    try:
        # Convertir descriptores a objetos de archivo
        with os.fdopen(read_pipe) as read_pipe, os.fdopen(write_pipe, 'w') as write_pipe:
            while True:
                # Leer operación del cliente
                operation = read_pipe.readline().strip()
                if not operation:  # EOF (cliente cerró su extremo de escritura)
                    break
                
                # Procesar la operación con un pequeño retraso para simular procesamiento
                time.sleep(0.5)

                # Evaluar operación
                try:
                    result = eval(operation)
                    response = f"RESULT {result}"
                except Exception as e:
                    response = f"ERROR {str(e)}"
                
                # Enviar respuesta al cliente
                write_pipe.write(f"{response}\n")
                write_pipe.flush()

    except Exception as e:
        print(f"Error en la comunicación con el servidor: {e}")
    finally:
        try:
            read_pipe.close()
        except:
            pass
        try:
            write_pipe.close()
        except:
            pass

def cliente(read_pipe, write_pipe):
    """Función del cliente: envia operaciones y espera respuestas"""
    try:
        # Convertir descriptores a objetos de archivo
        with os.fdopen(read_pipe) as read_pipe, os.fdopen(write_pipe, 'w') as write_pipe:
            while True:
                # Pedir operación al usuario si escribe 'exit' salir
                operation = input("Operación: ")
                if operation.lower() == 'exit':
                    break
                
                # Enviar operación al servidor manejando errores
                try:
                    write_pipe.write(f"{operation}\n")
                    write_pipe.flush()
                except BrokenPipeError:
                    print("El servidor ha cerrado la conexión. Saliendo...")
                    break
                
                # Leer respuesta del servidor
                response = read_pipe.readline().strip()
                print(f"Respuesta del servidor: {response}")
                
                # Procesar respuesta
                if response.startswith("RESULT "):
                    result = float(response[7:])
                    print(f"Resultado: {result}")
                elif response.startswith("ERROR "):
                    print(f"Error: {response[6:]}")
                else:
                    print(f"Respuesta desconocida: {response}")
    except Exception as e:
        print(f"Error en la comunicación del cliente: {e}")
    finally:
        try:
            read_pipe.close()
        except:
            pass
        try:
            write_pipe.close()
        except:
            pass

def main():

    setup_signal_handler()

    # Crear pipes para comunicación bidireccional
    # Pipe para mensajes del cliente al servidor
    client_to_server_r, client_to_server_w = os.pipe()
    
    # Pipe para mensajes del servidor al cliente
    server_to_client_r, server_to_client_w = os.pipe()
    
    # Bifurcar el proceso
    pid = os.fork()
    
    if pid > 0:  # Proceso padre cliente
        # Cerrar extremos no utilizados
        os.close(client_to_server_r)
        os.close(server_to_client_w)
        
        # Primer mensaje
        print("Escriba su operacion (por ejemplo, '5 + 3') y luego 'exit' para salir.")

        # Funcion para comunicar con el servidor
        cliente(server_to_client_r, client_to_server_w)
        
        # Esperar a que el servidor termine
        os.waitpid(pid, 0)
        print("Cliente: El proceso del servidor ha terminado.")
        
    else:  # Proceso servidor
        # Cerrar extremos no utilizados
        os.close(client_to_server_w)
        os.close(server_to_client_r)
        
        # Funcion para comunicar con el cliente
        servidor(client_to_server_r, server_to_client_w)
        
        # Salir del proceso servidor
        print("Servidor: Terminando.")
        sys.exit(0)

if __name__ == "__main__":
    main()