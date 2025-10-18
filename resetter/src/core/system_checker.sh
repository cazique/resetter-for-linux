#!/bin/bash
# Módulo para realizar comprobaciones del estado del sistema

# Verifica si hay suficiente espacio en disco en una ruta determinada
# Parámetros:
#   $1: Ruta a comprobar (ej: /)
#   $2: Espacio mínimo requerido en KB
check_disk_space() {
    local path="$1"
    local min_space_kb="$2"

    local available_kb=$(df "$path" | awk 'NR==2 {print $4}')

    if [[ $available_kb -lt $min_space_kb ]]; then
        local available_mb=$((available_kb / 1024))
        local required_mb=$((min_space_kb / 1024))
        log_error "Espacio en disco insuficiente en '${path}'."
        handle_error "DISK_SPACE" "Se requieren ${required_mb}MB, pero solo hay ${available_mb}MB disponibles."
        return 1
    fi

    log_success "Verificación de espacio en disco superada para '${path}'."
    return 0
}

# Verifica si el sistema de ficheros raíz está montado en modo de escritura
check_filesystem_writable() {
    log_info "Verificando que el sistema de ficheros raíz sea escribible..."
    if mount | grep -q "on / .*ro,"; then
        log_error "El sistema de ficheros raíz está montado en modo de solo lectura."
        handle_error "PERMISSION_DENIED" "El sistema de ficheros está en modo de solo lectura."
        return 1
    fi
    log_success "El sistema de ficheros raíz es escribible."
    return 0
}

# Verifica la conexión a Internet intentando resolver un dominio conocido
check_network_connection() {
    log_info "Verificando la conexión a Internet..."
    if ! ping -c 1 -W 3 "8.8.8.8" &> /dev/null; then
        log_warning "No se pudo hacer ping a 8.8.8.8. La conexión a Internet puede ser limitada."
        return 1
    fi
    log_success "La conexión a Internet parece estar activa."
    return 0
}
