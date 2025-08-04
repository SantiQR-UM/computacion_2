#!/bin/bash

# Ejecuta el script Python en segundo plano y guarda su PID
echo "Lanzando sleep_script.py en segundo plano..."
python3 sleep_script.py &
PYTHON_PID=$! # Guarda el PID del último comando en segundo plano

echo "Script sleep_script.py lanzado. Su PID es: $PYTHON_PID"
echo "Puedes verificar su ejecución con: ps aux | grep $PYTHON_PID"
echo "Para terminarlo prematuramente, en otra terminal, usa: kill -SIGTERM $PYTHON_PID"
echo "Esperando que el script termine (o sea terminado)..."

# El script Bash esperará un poco antes de salir para que el usuario tenga tiempo de interactuar
# En un escenario real, aquí podrías tener un loop o esperar un evento.
sleep 15 

echo "Script Bash finalizado."
exit 0