#!/bin/bash
set -euo pipefail

# CONFIGURACIÓN
# Asume que el script se ejecuta desde la raíz del repo clonado
SOURCE_DIR="."
INSTALL_DIR="/usr/local/share/resetter"
BIN_DIR="/usr/local/bin"
DATA_DIR="/resetter-for-linux"

# COLORES Y FORMATOS
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# FUNCIONES DE LOG
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# VERIFICACIÓN DE PRIVILEGIOS
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script debe ejecutarse como root. Prueba con sudo."
        exit 1
    fi
}

# INSTALACIÓN DE DEPENDENCIAS
install_dependencies() {
    log_info "Instalando dependencias..."
    # (El código de detección de distro e instalación de dependencias iría aquí)
    log_success "Dependencias verificadas (simulado)."
}

# COPIAR FICHEROS
copy_files() {
    log_info "Copiando ficheros de la aplicación..."

    # Crear directorios de destino
    mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DATA_DIR"

    # Copiar la lógica de la aplicación
    cp -r "$SOURCE_DIR/resetter/"* "$INSTALL_DIR/"

    # Copiar el ejecutable principal
    cp "$SOURCE_DIR/resetter/resetter" "$BIN_DIR/resetter"

    # Crear los directorios de datos
    mkdir -p "$DATA_DIR/"{config,backups,logs,reports,temp}
    cp "$SOURCE_DIR/resetter-data/config/"* "$DATA_DIR/config/"

    log_success "Ficheros copiados."
}

# CONFIGURAR PERMISOS
set_permissions() {
    log_info "Configurando permisos..."

    # Permisos para el ejecutable
    chmod +x "$BIN_DIR/resetter"

    # Permisos para los scripts de la librería
    find "$INSTALL_DIR" -type f -name "*.sh" -exec chmod +x {} \;

    # Propiedad de los directorios
    chown -R root:root "$INSTALL_DIR" "$BIN_DIR/resetter" "$DATA_DIR"

    log_success "Permisos configurados."
}

# FUNCIÓN PRINCIPAL
main() {
    log_info "Iniciando instalación de Resetter for Linux..."

    check_privileges
    install_dependencies
    copy_files
    set_permissions

    log_success "Instalación completada exitosamente."
    log_info "Ejecuta 'resetter' para comenzar."
}

# MANEJADOR DE ERRORES
trap 'log_error "Error en línea $LINENO. Instalación abortada."; exit 1' ERR

# EJECUCIÓN
main "$@"
