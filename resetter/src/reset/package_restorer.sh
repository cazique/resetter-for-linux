#!/bin/bash
# Módulo para restaurar y purgar paquetes del sistema

# Guarda la lista de paquetes instalados por el usuario en un fichero
# Parámetro:
#   $1: Fichero de destino para la lista de paquetes
backup_user_packages_list() {
    local backup_file="$1"
    log_info "Guardando la lista de paquetes instalados por el usuario en: $backup_file"

    # Llama a la función del gestor de paquetes para obtener la lista
    list_installed_packages > "$backup_file"

    if [[ -s "$backup_file" ]]; then
        log_success "Lista de paquetes guardada. Se encontraron $(wc -l < "$backup_file") paquetes."
    else
        log_warning "No se encontraron paquetes instalados por el usuario o el gestor de paquetes no es compatible."
    fi
}

# Elimina todos los paquetes que no son parte del sistema base
# ¡OPERACIÓN MUY DESTRUCTIVA!
purge_all_user_packages() {
    ensure_root

    # Usar el nuevo sistema de advertencias
    confirm_critical_action "PURGAR PAQUETES DE USUARIO" "CONFIRMAR" || return 1

    local packages_to_purge

    # Obtener la lista de paquetes
    mapfile -t packages_to_purge < <(list_installed_packages)

    if [[ ${#packages_to_purge[@]} -eq 0 ]]; then
        log_success "No se encontraron paquetes de usuario para eliminar."
        return
    fi

    log_info "Se eliminarán los siguientes paquetes: ${packages_to_purge[*]}"

    # Llama a la función del gestor de paquetes para purgar la lista
    purge_packages packages_to_purge

    log_success "Se han eliminado todos los paquetes no esenciales."
}

# Reinstala una lista de paquetes desde un fichero
# Parámetro:
#   $1: Fichero con la lista de paquetes a instalar
reinstall_packages_from_list() {
    local package_list_file="$1"
    ensure_root

    if [[ ! -f "$package_list_file" ]]; then
        log_error "El fichero de lista de paquetes no existe: $package_list_file"
        return 1
    fi

    log_info "Reinstalando paquetes desde la lista: $package_list_file..."

    local package_manager=$(get_package_manager)
    local packages_to_install
    mapfile -t packages_to_install < "$package_list_file"

    case "$package_manager" in
        apt)
            apt-get update
            apt-get install -y --ignore-missing "${packages_to_install[@]}"
            ;;
        dnf|yum)
            dnf install -y "${packages_to_install[@]}"
            ;;
        pacman)
            pacman -S --noconfirm --needed - < "$package_list_file"
            ;;
        *)
            log_error "Gestor de paquetes '$package_manager' no soportado para reinstalación desde lista."
            return 1
            ;;
    esac

    log_success "Se ha completado la reinstalación de paquetes."
}
