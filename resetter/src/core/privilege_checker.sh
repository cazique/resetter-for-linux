#!/bin/bash
# Módulo para verificar privilegios

# Función para comprobar si el script se ejecuta como root
# Termina el script si no se cumplen los privilegios.
ensure_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        log_error "Este script o función requiere privilegios de root."
        handle_error "PERMISSION_DENIED" "Se requieren privilegios de root para esta operación."
    fi
}
