#!/bin/bash
# Módulo para mostrar indicadores de progreso

# Muestra un 'spinner' mientras se ejecuta un comando en segundo plano.
# Esto proporciona feedback al usuario durante operaciones largas.
#
# Uso:
#   long_running_command &
#   show_spinner $! "Procesando datos..."
#
# Parámetros:
#   $1: El PID del proceso en segundo plano a monitorear.
#   $2: El mensaje de texto a mostrar junto al spinner.

show_spinner() {
    local pid=$1
    local message=$2
    local spinstr='|/-\\'

    # Ocultar el cursor
    tput civis

    echo -n "$message "
    while kill -0 "$pid" 2>/dev/null; do
        local temp=${spinstr#?}
        printf "%c" "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep 0.1
        printf "\\b"
    done

    # Restaurar el cursor
    tput cnorm

    # Comprobar el código de salida del proceso
    wait "$pid"
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✓ Hecho${NC}"
    else
        echo -e "${RED}✗ Falló (código de salida: $exit_code)${NC}"
    fi

    return $exit_code
}

# Ejemplo de uso (puede ser ejecutado directamente para probar):
# if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
#   echo "Probando el spinner durante 5 segundos..."
#   sleep 5 &
#   show_spinner $! "Esperando..."
# fi
