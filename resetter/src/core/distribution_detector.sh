#!/bin/bash

DISTRIBUTION_DETECTOR_VERSION="1.0"

# Cargar configuración de distribuciones
load_distribution_config() {
    local config_file="./resetter/config/distributions.conf"
    if [[ ! -f "$config_file" ]]; then
        log_error "Archivo de configuración de distribuciones no encontrado"
        return 1
    fi

    # Parsear YAML básico
    while IFS=: read -r key value; do
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        case "$key" in
            "debian"|"ubuntu"|"fedora"|"rhel"|"arch"|"opensuse")
                declare -g "DISTRO_${key^^}_CONFIG"="$value"
                ;;
        esac
    done < "$config_file"
}

# Detectar distribución actual
detect_current_distribution() {
    local distro_id="" distro_version="" distro_name=""

    # Método primario: /etc/os-release
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        distro_id="$ID"
        distro_version="$VERSION_ID"
        distro_name="$PRETTY_NAME"

    # Método secundario: archivos específicos
    elif [[ -f /etc/debian_version ]]; then
        distro_id="debian"
        distro_version=$(cat /etc/debian_version)
        distro_name="Debian GNU/Linux $distro_version"
    elif [[ -f /etc/redhat-release ]]; then
        distro_id="rhel"
        distro_version=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release)
        distro_name="Red Hat Enterprise Linux $distro_version"
    elif [[ -f /etc/arch-release ]]; then
        distro_id="arch"
        distro_version="rolling"
        distro_name="Arch Linux"
    fi

    # Validar detección
    if [[ -z "$distro_id" ]]; then
        log_error "No se pudo detectar la distribución"
        return 1
    fi

    # Configurar variables globales
    CURRENT_DISTRO="$distro_id"
    CURRENT_VERSION="$distro_version"
    CURRENT_DISTRO_NAME="$distro_name"

    log_info "Distribución detectada: $CURRENT_DISTRO_NAME"
    return 0
}

# Verificar compatibilidad
check_distribution_compatibility() {
    local supported_versions=()

    case "$CURRENT_DISTRO" in
        debian)
            supported_versions=("13" "12" "11" "10" "9")
            ;;
        ubuntu)
            supported_versions=("24.04" "22.04" "20.04" "18.04" "16.04")
            ;;
        *)
            log_warning "Distribución $CURRENT_DISTRO puede tener compatibilidad limitada"
            return 0
            ;;
    esac

    for version in "${supported_versions[@]}"; do
        if [[ "$CURRENT_VERSION" == "$version" ]]; then
            log_success "Versión $CURRENT_VERSION completamente soportada"
            return 0
        fi
    done

    log_warning "Versión $CURRENT_VERSION puede tener compatibilidad limitada"
    return 0
}

# Obtener gestor de paquetes
get_package_manager() {
    case "$CURRENT_DISTRO" in
        debian|ubuntu|linuxmint)
            echo "apt"
            ;;
        fedora|rhel|centos)
            if command -v dnf >/dev/null; then
                echo "dnf"
            else
                echo "yum"
            fi
            ;;
        arch|manjaro)
            echo "pacman"
            ;;
        opensuse|sles)
            echo "zypper"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}
