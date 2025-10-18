#!/bin/bash

# COLORES Y FORMATOS
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'
BOLD='\\033[1m'

# FUNCIONES DE LOG
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

ERROR_HANDLER_VERSION="2.0"

# Códigos de error
declare -A ERROR_CODES=(
    ["DISTRO_NOT_SUPPORTED"]=100
    ["BACKUP_FAILED"]=101
    ["PERMISSION_DENIED"]=102
    ["DISK_SPACE"]=103
    ["NETWORK_ERROR"]=104
    ["GRUB_INSTALL_FAILED"]=105
    ["DEPENDENCY_MISSING"]=106
    ["USER_ABORT"]=107
)

# Manejar errores
handle_error() {
    local error_code="$1"
    local error_message="$2"
    local context="$3"

    log_error "$error_message"

    # Registrar en archivo de log
    echo "$(date): $error_code - $error_message - $context" >> "./resetter-data/logs/errors.log"

    # Acciones específicas por código de error
    case "$error_code" in
        "DISTRO_NOT_SUPPORTED")
            echo "Distribución no soportada. Distribuciones soportadas:"
            echo " - Debian 9-13, Ubuntu 16.04-24.04"
            ;;
        "BACKUP_FAILED")
            echo "El backup falló. Verifica espacio en disco y permisos."
            ;;
        "PERMISSION_DENIED")
            echo "Permisos insuficientes. Ejecuta como root: sudo resetter"
            ;;
        "DISK_SPACE")
            local available_mb=$(df . | awk 'NR==2 {print $4/1024}')
            echo "Espacio insuficiente. Disponible: ${available_mb}MB"
            ;;
        "GRUB_INSTALL_FAILED")
            echo "Error reinstalando GRUB. El sistema puede no arrancar."
            echo "Usa un USB de rescate para reinstalar GRUB manualmente."
            ;;
    esac

    # Sugerir recuperación
    suggest_recovery "$error_code"

    exit "${ERROR_CODES[$error_code]}"
}

# Sugerir acciones de recuperación
suggest_recovery() {
    local error_code="$1"

    case "$error_code" in
        "BACKUP_FAILED")
            echo "Sugerencias:"
            echo "1. Libera espacio en disco"
            echo "2. Usa un directorio de backup diferente"
            echo "3. Verifica permisos de escritura"
            ;;
        "GRUB_INSTALL_FAILED")
            echo "Para recuperar GRUB:"
            echo "1. Usa un USB live"
            echo "2. Monta tu sistema: mount /dev/sdXY /mnt"
            echo "3. Reinstala GRUB: grub-install --root-directory=/mnt /dev/sdX"
            ;;
        "NETWORK_ERROR")
            echo "Verifica tu conexión a internet y repositorios"
            ;;
    esac
}

# Verificar requisitos previos
check_prerequisites() {
    log_info "Verificando requisitos del sistema..."

    # Verificar root
    if [[ $EUID -ne 0 ]]; then
        handle_error "PERMISSION_DENIED" "Se requieren privilegios de root"
    fi

    # Verificar espacio en disco
    local available_kb=$(df . | awk 'NR==2 {print $4}')
    if [[ $available_kb -lt 524288 ]]; then  # 512MB
        handle_error "DISK_SPACE" "Espacio en disco insuficiente"
    fi

    # Verificar comandos esenciales
    local essential_commands=("bash" "tar" "gzip" "curl" "wget")
    for cmd in "${essential_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            handle_error "DEPENDENCY_MISSING" "Comando esencial no encontrado: $cmd"
        fi
    done

    # Verificar sistema de archivos montado como read-write
    if mount | grep -q "on / .*ro,"; then
        handle_error "PERMISSION_DENIED" "Sistema de archivos root en modo solo lectura"
    fi

    log_success "Todos los requisitos verificados"
}

# Función de seguridad para operaciones críticas
safety_check() {
    local operation="$1"

    echo "🚨 OPERACIÓN CRÍTICA: $operation"
    echo "Esta acción no se puede deshacer fácilmente."

    read -p "¿Estás absolutamente seguro? (escribe 'CONFIRMAR' para continuar): " confirmation

    if [[ "$confirmation" != "CONFIRMAR" ]]; then
        log_warning "Operación cancelada por el usuario"
        handle_error "USER_ABORT" "Usuario canceló la operación crítica"
    fi
}
