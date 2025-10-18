#!/bin/bash
# Módulo para abstraer las operaciones del gestor de paquetes

# Obtiene la lista de paquetes instalados explícitamente por el usuario
# Esto ayuda a distinguir los paquetes base de los que el usuario añadió.
list_installed_packages() {
    log_info "Obteniendo la lista de paquetes instalados por el usuario..."
    local package_manager=$(get_package_manager)

    case "$package_manager" in
        apt)
            # Para sistemas Debian/Ubuntu, filtra los paquetes que no son esenciales o dependencias automáticas.
            apt-mark showmanual
            ;;
        dnf|yum)
            # Para sistemas Fedora/RHEL, muestra los paquetes instalados por el usuario.
            dnf history userinstalled | awk 'NR>1 {print $1}'
            ;;
        pacman)
            # Para sistemas Arch, muestra los paquetes instalados explícitamente.
            pacman -Qqe
            ;;
        zypper)
            # Para sistemas openSUSE.
            zypper pa --installed-only | awk -F'|' 'NR>4 {print $2}'
            ;;
        *)
            log_error "Gestor de paquetes '$package_manager' no soportado para listar paquetes."
            return 1
            ;;
    esac
}

# Reinstala los paquetes esenciales del sistema
reinstall_core_packages() {
    log_info "Reinstalando paquetes esenciales del sistema..."
    local package_manager=$(get_package_manager)

    # Lista de paquetes considerados "esenciales" para un sistema base
    local core_packages

    case "$package_manager" in
        apt)
            core_packages=("ubuntu-minimal" "bash" "coreutils" "apt" "dpkg") # Ejemplo para Ubuntu
            apt-get install --reinstall -y "${core_packages[@]}"
            ;;
        dnf|yum)
            core_packages=("@core" "bash" "coreutils" "dnf") # Ejemplo para Fedora
            dnf reinstall -y "${core_packages[@]}"
            ;;
        pacman)
            core_packages=("base" "bash") # Ejemplo para Arch
            pacman -S --noconfirm "${core_packages[@]}"
            ;;
        *)
            log_error "Gestor de paquetes '$package_manager' no soportado para reinstalación."
            return 1
            ;;
    esac
}

# Elimina una lista de paquetes
purge_packages() {
    local -n packages_to_purge=$1
    log_warning "Eliminando ${#packages_to_purge[@]} paquetes..."
    local package_manager=$(get_package_manager)

    case "$package_manager" in
        apt)
            apt-get remove --purge -y "${packages_to_purge[@]}"
            apt-get autoremove --purge -y
            ;;
        dnf|yum)
            dnf remove -y "${packages_to_purge[@]}"
            dnf autoremove -y
            ;;
        pacman)
            pacman -Rns --noconfirm "${packages_to_purge[@]}"
            ;;
        *)
            log_error "Gestor de paquetes '$package_manager' no soportado para purgar paquetes."
            return 1
            ;;
    esac
}
