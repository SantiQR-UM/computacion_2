import os
import sys
import time

def stage1(write_pipe):
    """Genera números y los envía al siguiente stage."""
    with os.fdopen(write_pipe, 'w') as pipe:
        print("Stage 1: Generando números...")
        for i in range(1, 11):
            pipe.write(f"{i}\n")
            pipe.flush()
            print(f"Stage 1: Envió {i}")
            time.sleep(0.5)  # Simular procesamiento

def stage2(read_pipe, write_pipe):
    """Lee números, calcula sus cuadrados y los envía al siguiente stage."""
    with os.fdopen(read_pipe) as in_pipe, os.fdopen(write_pipe, 'w') as out_pipe:
        print("Stage 2: Calculando cuadrados...")
        for line in in_pipe:
            num = int(line.strip())
            result = num * num
            out_pipe.write(f"{result}\n")
            out_pipe.flush()
            print(f"Stage 2: Recibió {num}, envió {result}")
            time.sleep(0.5)  # Simular procesamiento

def stage3(read_pipe):
    """Lee los cuadrados y calcula su suma."""
    with os.fdopen(read_pipe) as pipe:
        print("Stage 3: Sumando resultados...")
        total = 0
        for line in pipe:
            num = int(line.strip())
            total += num
            print(f"Stage 3: Recibió {num}, suma actual = {total}")
            time.sleep(0.5)  # Simular procesamiento
        print(f"Stage 3: Resultado final = {total}")

def main():
    # Crear pipes para conectar las etapas
    pipe1_r, pipe1_w = os.pipe()  # Conecta Stage 1 -> Stage 2
    pipe2_r, pipe2_w = os.pipe()  # Conecta Stage 2 -> Stage 3
    
    # Bifurcar para Stage 1
    pid1 = os.fork()
    if pid1 == 0:  # Proceso hijo (Stage 1)
        # Cerrar descriptores no utilizados
        os.close(pipe1_r)
        os.close(pipe2_r)
        os.close(pipe2_w)
        
        # Ejecutar Stage 1
        stage1(pipe1_w)
        sys.exit(0)
    
    # Bifurcar para Stage 2
    pid2 = os.fork()
    if pid2 == 0:  # Proceso hijo (Stage 2)
        # Cerrar descriptores no utilizados
        os.close(pipe1_w)
        os.close(pipe2_r)
        
        # Ejecutar Stage 2
        stage2(pipe1_r, pipe2_w)
        sys.exit(0)
    
    # Proceso principal ejecuta Stage 3
    # Cerrar descriptores no utilizados
    os.close(pipe1_r)
    os.close(pipe1_w)
    os.close(pipe2_w)
    
    # Ejecutar Stage 3
    stage3(pipe2_r)
    
    # Esperar a que los procesos hijos terminen
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)
    
    print("Pipeline completado.")

if __name__ == "__main__":
    main()