#!/bin/bash

FIFO="/tmp/mi_fifo_ej17"

echo "Lector: Iniciando. Leeré desde $FIFO"

# Abrir el FIFO para lectura
# Esto se bloqueará hasta que el escritor abra el FIFO
exec 3<$FIFO

echo "Lector: FIFO abierto. Comenzando a leer mensajes..."

while IFS= read -r line <&3; do # Leer línea por línea desde el descriptor de archivo 3
    echo "Lector: Recibido: \"$line\""
    sleep 0.5 # Pequeña pausa para simular procesamiento
done

echo "Lector: El escritor ha cerrado el FIFO o ha terminado."
exec 3>&- # Cierra el descriptor de archivo 3