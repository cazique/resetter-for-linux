#!/bin/bash
set -euo pipefail

# CONFIGURACIÓN
REPO_URL="https://github.com/cazique/resetter-for-linux"
INSTALL_DIR="/usr/local/share/resetter"
BIN_DIR="/usr/local/bin"
BACKUP_DIR="/resetter-for-linux"

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

# DETECCIÓN DE DISTRIBUCIÓN
detect_distribution() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DISTRO_ID="${ID}"
        DISTRO_VERSION="${VERSION_ID}"
        DISTRO_NAME="${NAME}"
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO_ID="rhel"
        DISTRO_VERSION=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release)
        DISTRO_NAME="Red Hat Enterprise Linux"
    else
        log_error "No se pudo detectar la distribución"
        exit 1
    fi

    log_info "Distribución detectada: $DISTRO_NAME $DISTRO_VERSION"
}

# VERIFICACIÓN DE PRIVILEGIOS
check_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script debe ejecutarse como root"
        exit 1
    fi
}

# INSTALACIÓN DE DEPENDENCIAS
install_dependencies() {
    log_info "Instalando dependencias..."

    case $DISTRO_ID in
        debian|ubuntu|linuxmint)
            apt update
            apt install -y curl wget tar gzip gnupg2 lsb-release coreutils \
                         util-linux procps lvm2 cryptsetup grub2-common
            ;;
        fedora|rhel|centos)
            dnf install -y curl wget tar gzip gnupg2 redhat-lsb-core \
                         util-linux procps lvm2 cryptsetup grub2-tools
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm curl wget tar gzip gnupg lsb-release \
                         util-linux procps lvm2 cryptsetup grub
            ;;
        opensuse|sles)
            zypper install -y curl wget tar gzip gnupg2 lsb-release \
                         util-linux procps lvm2 cryptsetup grub2
            ;;
        *)
            log_warning "Distribución no soportada, intentando continuar..."
            ;;
    esac
}

# DESCARGA E INSTALACIÓN
download_and_install() {
    log_info "Descargando Resetter for Linux..."

    # Crear directorios de instalación
    mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$BACKUP_DIR"

    # Crear un directorio temporal para la descarga
    local TEMP_DIR
    TEMP_DIR=$(mktemp -d)

    log_info "Descargando el repositorio en un directorio temporal..."
    if command -v git &> /dev/null; then
        # Usar Git si está disponible para obtener la última versión
        git clone --depth 1 "$REPO_URL" "$TEMP_DIR"
    else
        # Usar wget o curl como alternativa
        wget -qO- "$REPO_URL/archive/main.tar.gz" | tar xz -C "$TEMP_DIR" --strip-components=1
    fi

    # Mover el contenido al directorio de instalación
    # Asumimos que la nueva implementación está en 'resetter/' y 'resetter-data/'
    log_info "Copiando ficheros a la ubicación final..."

    # Copiar la aplicación principal y los módulos
    cp -r "$TEMP_DIR/resetter/"* "$INSTALL_DIR/"

    # Copiar el script ejecutable
    cp "$TEMP_DIR/resetter/resetter" "$BIN_DIR/resetter"

    # Copiar los scripts de instalación
    mkdir -p "$INSTALL_DIR/scripts"
    cp "$TEMP_DIR/scripts/install.sh" "$INSTALL_DIR/scripts/"

    # Configurar permisos
    chmod +x "$BIN_DIR/resetter"
    find "$INSTALL_DIR" -type f -name "*.sh" -exec chmod +x {} \;

    # Limpiar el directorio temporal
    rm -rf "$TEMP_DIR"

    log_success "La descarga e instalación de los ficheros ha finalizado."
}

# CONFIGURACIÓN INICIAL
setup_initial_config() {
    log_info "Configurando entorno..."

    # Crear configuración por defecto
    mkdir -p "$INSTALL_DIR/config"
    cat > "$INSTALL_DIR/config/distributions.conf" << 'EOF'
# Configuración de distribuciones soportadas
debian:
  base: independent
  package_manager: apt
  versions:
    "13": "Trixie"
    "12": "Bookworm"
    "11": "Bullseye"
    "10": "Buster"
    "9": "Stretch"

ubuntu:
  base: debian
  package_manager: apt
  versions:
    "24.04": "Noble Numbat"
    "22.04": "Jammy Jellyfish"
    "20.04": "Focal Fossa"
    "18.04": "Bionic Beaver"
    "16.04": "Xenial Xerus"
EOF

    # Configurar idioma por defecto
    echo "es" > "$INSTALL_DIR/config/default_language"
}

# FUNCIÓN PRINCIPAL
main() {
    log_info "Iniciando instalación de Resetter for Linux..."

    check_privileges
    detect_distribution
    install_dependencies
    download_and_install
    setup_initial_config

    log_success "Instalación completada exitosamente"
    log_info "Ejecuta 'resetter' para comenzar"
}

# MANEJADOR DE ERRORES
trap 'log_error "Error en línea $LINENO. Instalación abortada."; exit 1' ERR

# EJECUCIÓN
main "$@"
