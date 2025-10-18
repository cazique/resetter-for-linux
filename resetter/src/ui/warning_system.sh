#!/bin/bash
# Módulo para el sistema de advertencias y confirmaciones

# Muestra una advertencia crítica y pide al usuario que confirme escribiendo una frase.
# Esta función es un "cortafuegos" para operaciones peligrosas.
# Parámetros:
#   $1: El nombre de la operación que se va a realizar (ej: "FORMATEAR DISCO")
#   $2: La frase de confirmación exacta que el usuario debe escribir (ej: "CONFIRMAR")
confirm_critical_action() {
    local operation_name="$1"
    local confirmation_phrase="$2"

    # Usar colores para máxima alerta
    echo -e "${RED}${BOLD}🚨 ¡ADVERTENCIA DE OPERACIÓN CRÍTICA! 🚨${NC}"
    echo -e "${YELLOW}Estás a punto de realizar la siguiente operación: ${BOLD}${operation_name}${NC}"
    echo -e "${YELLOW}Esta acción puede tener consecuencias irreversibles, como la pérdida de datos.${NC}"
    echo
    echo -e "Para continuar, por favor, escribe la siguiente frase exactamente como aparece:"
    echo -e "  ${BOLD}${confirmation_phrase}${NC}"

    read -p "> " user_input

    if [[ "$user_input" != "$confirmation_phrase" ]]; then
        log_warning "La confirmación no coincide. Operación cancelada por seguridad."
        # Salir o devolver un código de error es una opción, pero por ahora devolvemos 1
        # para que el script que llama decida cómo manejarlo.
        return 1
    fi

    log_info "Confirmación aceptada. Procediendo con la operación..."
    return 0
}

# Muestra una advertencia general no bloqueante
# Parámetros:
#   $1: Mensaje de advertencia a mostrar
show_warning() {
    log_warning "$1"
    echo -e "${YELLOW}Por favor, ten en cuenta la advertencia anterior antes de continuar.${NC}"
    sleep 2 # Pausa para que el usuario pueda leer
}
