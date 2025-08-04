import os
import time

FIFO_PATH = "/tmp/mi_fifo"

def receiver_script():
    print(f"Receptor: Intentando abrir FIFO para lectura: {FIFO_PATH}")
    try:
        # Abrir el FIFO en modo lectura binaria
        # 'rb' para lectura binaria
        with open(FIFO_PATH, 'rb') as fifo:
            print("Receptor: FIFO abierto. Esperando mensajes...")
            while True:
                # Leer una línea del FIFO. read() se bloquea hasta que haya datos.
                line_bytes = fifo.readline()
                if not line_bytes: # Si se lee una línea vacía, significa EOF (escritor cerró su extremo)
                    print("Receptor: Fin de archivo (EOF) alcanzado. El emisor ha cerrado el FIFO.")
                    break
                
                # Decodificar los bytes a una cadena de texto y eliminar el salto de línea
                message = line_bytes.decode('utf-8').strip()
                print(f"Receptor: Recibido: '{message}'")
                
                if message == "FIN_DE_MENSAJES":
                    print("Receptor: Mensaje de fin recibido. Terminando.")
                    break
            
    except FileNotFoundError:
        print(f"Error: FIFO no encontrado en {FIFO_PATH}. Asegúrate de crearlo con 'mkfifo /tmp/mi_fifo'")
    except Exception as e:
        print(f"Ocurrió un error en el receptor: {e}")

if __name__ == "__main__":
    receiver_script()