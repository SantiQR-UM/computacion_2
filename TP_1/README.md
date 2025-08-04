Este archivo contendrá las instrucciones para ejecutar el sistema.


# Sistema Concurrente de Análisis Biométrico con Cadena de Bloques Local

Este proyecto implementa un sistema distribuido en procesos de Python para simular la generación, procesamiento, verificación y almacenamiento seguro de datos biométricos en una cadena de bloques local.

## Arquitectura

El sistema se compone de los siguientes procesos:

-   **Proceso Principal (Generador)**: Simula la generación de 60 muestras de datos biométricos (frecuencia cardíaca, presión, oxígeno) a razón de una por segundo.
-   **Procesos de Análisis (Proc A, B, C)**: Tres procesos dedicados, uno para cada tipo de señal (Frecuencia, Presión, Oxígeno). Reciben los datos, mantienen una ventana móvil de los últimos 30 segundos, y calculan la media y desviación estándar de su señal.
-   **Proceso Verificador**: Recibe los resultados de los tres analizadores para un mismo timestamp, los valida, detecta alertas, construye un bloque de la cadena de bloques y lo persiste en un archivo JSON.
-   **Cadena de Bloques Local**: Almacenada en `blockchain.json`, garantizando la integridad mediante hashes SHA-256 encadenados.

## Requisitos

-   Python 3.9 o superior.
-   Librerías estándar de Python: `multiprocessing`, `os`, `time`, `random`, `datetime`, `json`, `hashlib`, `statistics`.

## Estructura del Proyecto

- .
- ├── main_system.py
- ├── verificar_cadena.py
- ├── README.md
- ├── blockchain.json  (generado al ejecutar main_system.py)
- └── reporte.txt      (generado al ejecutar verificar_cadena.py)

## Instrucciones de Ejecución

Sigue estos pasos para ejecutar el sistema y generar el reporte:

1.  **Asegúrate de tener Python 3.9+ instalado.**

2.  **Guarda los archivos:**
    Crea los archivos `main_system.py` y `verificar_cadena.py` con el código proporcionado en este documento.

3.  **Ejecuta el Sistema de Análisis Biométrico:**
    Abre una terminal y ejecuta el script principal. Esto iniciará el generador, los analizadores y el verificador. Creará el archivo `blockchain.json`.

    ```bash
    python3 main_system.py
    ```

    Verás una serie de mensajes en la consola que indican el progreso de la generación, análisis y verificación de los bloques. El proceso tomará aproximadamente `NUM_SAMPLES` segundos (60 segundos por defecto).

4.  **Verifica la Cadena de Bloques y Genera el Reporte:**
    Una vez que `main_system.py` haya terminado su ejecución, ejecuta el script de verificación. Esto leerá `blockchain.json`, validará la integridad y generará `reporte.txt`.

    ```bash
    python3 verificar_cadena.py
    ```

    Este script imprimirá un resumen de la verificación en la consola y creará el archivo `reporte.txt` con la información final.

## Observaciones Importantes

-   **Limpieza de Archivos**: `main_system.py` eliminará `blockchain.json` al inicio de cada ejecución para asegurar una cadena limpia. `verificar_cadena.py` generará `reporte.txt`.
-   **Concurrencia y Sincronización**:
    -   La comunicación entre el Generador y los Analizadores se realiza a través de `os.pipe()`.
    -   La comunicación entre los Analizadores y el Verificador se realiza a través de `multiprocessing.Queue()`.
    -   Se utiliza `multiprocessing.Lock()` para proteger la escritura en el archivo `blockchain.json` por parte del proceso Verificador, garantizando que solo un proceso escriba a la vez y evitando la corrupción del archivo.
    -   Se usa `multiprocessing.Event()` para una terminación limpia de todos los procesos hijos.
-   **Simulación Costosa**: La "costo" en los analizadores se simula con `time.sleep()` para hacer el proceso más lento y evidente.
-   **Ventana Móvil**: Los analizadores mantienen una ventana móvil de los últimos 30 segundos de datos para el cálculo de media y desviación estándar.

## Solución de Problemas

-   Si ves `BrokenPipeError`: Asegúrate de que todos los procesos se inician correctamente y que el generador no termine prematuramente antes de que los analizadores puedan leer.
-   Si `blockchain.json` está vacío o corrupto: `verificar_cadena.py` reportará un error JSON. Asegúrate de que `main_system.py` corrió hasta el final.
-   Si los procesos no terminan: Verifica que `os.close()` y `process.join()` se llamen correctamente, y que el `stop_event` se active.


## EXTRA: Consideraciones Adicionales y Puntos Clave (en más detalle)


### IPC (Inter-Process Communication):

1. Generador -> Analizadores: Se usan pipes anónimos (os.pipe()). Cada analizador tiene su propio pipe de lectura, y el generador escribe en los tres pipes de escritura. Es crucial que cada proceso cierre los extremos del pipe que no necesita (os.close()) para evitar deadlocks o que los read se bloqueen indefinidamente.

2. Analizadores -> Verificador: Se usan multiprocessing.Queue(). Estas colas son seguras para hilos y procesos, y manejan automáticamente la sincronización interna.


### Sincronización:

1. multiprocessing.Lock: Se usa un lock (blockchain_lock) para proteger la escritura en el archivo blockchain.json. Esto es vital porque el proceso verificador es el único que puede escribir en este archivo, y el lock asegura que las operaciones de lectura-modificación-escritura del archivo JSON sean atómicas, evitando condiciones de carrera a nivel de archivo.

2. multiprocessing.Event: El stop_event permite al proceso principal señalar a los otros procesos que deben terminar. Es un mecanismo de control para un cierre limpio.

3. Gestión de Ventanas Móviles: Cada analizador mantiene una lista (data_window) y usa append() y pop(0) para mantener solo los últimos WINDOW_SIZE datos.

4. os._exit(0): Los procesos hijos usan os._exit(0) para asegurarse de que terminan inmediatamente y no intentan ejecutar el código del padre después de un fork.

5. Manejo de Errores y Limpieza: Se incluyen try-except para BrokenPipeError, json.JSONDecodeError y otras excepciones, y se asegura el cierre de los descriptores de archivo. El main_system espera a todos sus hijos con join() para evitar procesos zombi.

6. Complejidad del calculate_hash: Para que el hash sea consistente y reproducible en la verificación, es fundamental que el diccionario data se serialice de manera determinística (por ejemplo, sort_keys=True en json.dumps).

7. Manejo de Tiempos y Pausas: El time.sleep(1) en el generador y en el verificador simula el tiempo real de las operaciones. Pequeñas pausas en los analizadores (time.sleep(0.00001)) simulan un "cálculo costoso".

8. Persistencia de la Cadena de Bloques: La cadena de bloques se guarda en blockchain.json después de cada nuevo bloque. Esto asegura que, incluso si el sistema se cierra inesperadamente, los bloques ya procesados no se pierdan.

9. Robustez del Verificador: El verificador usa queue.get(timeout=...) o queue.get_nowait() para evitar bloquearse indefinidamente si uno de los analizadores falla o es lento. También incluye un timeout_per_block para asegurar que el verificador no espere infinitamente por un conjunto completo de resultados de un timestamp.

---
