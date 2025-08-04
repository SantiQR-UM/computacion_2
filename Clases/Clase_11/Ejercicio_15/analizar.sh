#!/bin/bash

echo "--- Ejercicio 15: Análisis de Procesos Activos ---"
echo "Recopilando información de procesos desde /proc..."
echo ""

# Encabezados para la tabla
printf "%-8s %-8s %-25s %-15s %s\n" "PID" "PPID" "Nombre Ejecutable" "Estado" "Estado Detallado"
printf "%-8s %-8s %-25s %-15s %s\n" "--------" "--------" "-----------------" "---------------" "----------------"

# Declarar un array asociativo para contar los estados
declare -A process_states
total_processes=0

# Recorrer todos los directorios que parecen PIDs en /proc
for pid_dir in /proc/[0-9]*; do
    if [ -d "$pid_dir" ]; then # Asegurarse de que sea un directorio
        PID=$(basename "$pid_dir")
        
        STATUS_FILE="$pid_dir/status"
        COMM_FILE="$pid_dir/comm" # Nombre del ejecutable
        
        if [ -f "$STATUS_FILE" ]; then
            # Leer el PPID, Nombre y Estado del archivo status
            PPID=$(grep -E '^PPid:' "$STATUS_FILE" | awk '{print $2}')
            PROCESS_NAME=$(grep -E '^Name:' "$STATUS_FILE" | awk '{print $2}')
            STATE_FULL=$(grep -E '^State:' "$STATUS_FILE")
            STATE_CODE=$(echo "$STATE_FULL" | awk '{print $2}') # Ej: S
            STATE_DESCRIPTION=$(echo "$STATE_FULL" | cut -d'(' -f2 | cut -d')' -f1) # Ej: sleeping
            
            # Si el nombre del ejecutable está en comm, usarlo (a veces es más preciso)
            if [ -f "$COMM_FILE" ]; then
                COMM_NAME=$(cat "$COMM_FILE")
                if [ -n "$COMM_NAME" ]; then # Si no está vacío
                    PROCESS_NAME="$COMM_NAME"
                fi
            fi

            # Imprimir la línea de la tabla
            printf "%-8s %-8s %-25s %-15s %s\n" "$PID" "$PPID" "$PROCESS_NAME" "$STATE_CODE" "$STATE_DESCRIPTION"

            # Contar los estados
            process_states["$STATE_CODE"]=$((process_states["$STATE_CODE"] + 1))
            total_processes=$((total_processes + 1))
        fi
    fi
done

echo ""
echo "--- Resumen de Estados de Procesos ---"
echo "Total de procesos analizados: $total_processes"
for state in "${!process_states[@]}"; do
    count="${process_states[$state]}"
    # Obtener la descripción del estado (puedes expandir esto si quieres)
    case "$state" in
        "R") description="Running (En ejecución)" ;;
        "S") description="Sleeping (Durmiendo)" ;;
        "D") description="Disk sleep (Esperando I/O de disco)" ;;
        "Z") description="Zombie (Zombi)" ;;
        "T") description="Stopped (Detenido por señal)" ;;
        "t") description="Tracing stop (Detenido para depuración)" ;;
        "X") description="Dead (Muerto, pero no debería ser visible)" ;;
        "K") description="Wakekill (Esperando una señal de muerte)" ;; # No es un estado común en /proc/status
        "W") description="Paging (Paginando)" ;; # No es un estado común en /proc/status
        *) description="Desconocido" ;;
    esac
    printf "%-5s (%-20s): %s\n" "$state" "$description" "$count"
done
echo "--------------------------------------"