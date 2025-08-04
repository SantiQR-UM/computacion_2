#!/bin/bash

FIFO="/tmp/mi_fifo_ej17"
COUNT=0

echo "Escritor: Iniciando. Escribiré en $FIFO"

# Abrir el FIFO para escritura
# Esto se bloqueará hasta que el lector abra el FIFO
exec 3>$FIFO

echo "Escritor: FIFO abierto. Comenzando a escribir mensajes..."

while true; do
    COUNT=$((COUNT + 1))
    MESSAGE="Mensaje #$COUNT del escritor"
    echo "$MESSAGE" >&3 # Escribir el mensaje en el descriptor de archivo 3 (el FIFO)
    echo "Escritor: Enviado: \"$MESSAGE\""
    sleep 1
done

echo "Escritor: Finalizando."
exec 3>&- # Cierra el descriptor de archivo 3