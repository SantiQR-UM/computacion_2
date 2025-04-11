import os
import tempfile

def main():
    file = tempfile.NamedTemporaryFile(delete=False)
    file_name = file.name
    file.close()

    create_children(file_name, "Soy el hijo 1")
    create_children(file_name, "Soy el hijo 2")

    # Esperar a ambos hijos
    while True:
        try:
            os.wait()
        except ChildProcessError:
            break  # No quedan hijos por esperar

    print(f"\nSoy el padre, mi PID es {os.getpid()}")
    print("Contenido final del archivo:")
    with open(file_name, 'r') as f:
        print(f.read())

    os.unlink(file_name)  # Opcional: eliminar el archivo temporal

def create_children(file_name, message):
    pid = os.fork()
    if pid == 0:
        print(f"{message}, mi PID es {os.getpid()}, el id de mi padre es {os.getppid()}")

        try:
            with open(file_name, 'r') as f:
                contenido = f.read()
                print(f"Contenido leído por {os.getpid()}: {contenido}")
        except Exception as e:
            print(f"Error leyendo el archivo: {e}")

        # Escribir en modo 'append' para no pisar lo anterior
        with open(file_name, 'a') as f:
            f.write(f"{message}, escribiendo desde el hijo PID {os.getpid()}\n")

        os._exit(0)

if __name__ == "__main__":
    main()
