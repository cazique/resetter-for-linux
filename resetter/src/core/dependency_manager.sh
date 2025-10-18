#!/bin/bash
# Módulo para la gestión de dependencias

# Lista de dependencias esenciales para el funcionamiento de Resetter
CORE_DEPENDENCIES=("bash" "tar" "gzip" "gpg" "curl" "wget" "util-linux" "procps" "lsb-release")

# Lista de dependencias opcionales para funcionalidades extendidas
OPTIONAL_DEPENDENCIES=("rclone" "docker" "docker-compose" "lvm2" "cryptsetup" "grub2-common")

# Función para verificar si un array de dependencias está instalado
# Salida: 0 si todas están, 1 si falta alguna.
check_dependencies() {
    local -n dependencies_array=$1 # Referencia indirecta al array
    local all_found=true

    log_info "Verificando dependencias..."
    for dep in "${dependencies_array[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_warning "Dependencia no encontrada: $dep"
            all_found=false
        fi
    done

    if ! $all_found; then
        log_error "Faltan una o más dependencias. La funcionalidad puede estar limitada."
        return 1
    fi

    log_success "Todas las dependencias necesarias están presentes."
    return 0
}
