#!/bin/bash
# Módulo para la gestión de servicios del sistema

# Lista de servicios considerados críticos para reiniciar después de un reseteo.
# Esto incluye red, inicio de sesión gráfico (display manager), y tareas programadas.
CRITICAL_SERVICES=(
    "NetworkManager"      # Gestor de red común
    "network-manager"     # Alternativa en Debian/Ubuntu
    "systemd-networkd"    # Otra alternativa de red
    "gdm"                 # GNOME Display Manager
    "lightdm"             # Un gestor de pantalla ligero y común
    "sddm"                # Gestor de pantalla de KDE
    "cron"                # Servicio de tareas programadas
    "sshd"                # Servicio de acceso remoto SSH
)

# Reinicia los servicios críticos del sistema
restart_critical_services() {
    ensure_root
    log_info "Reiniciando servicios críticos del sistema..."

    if ! command -v systemctl &> /dev/null; then
        log_warning "El comando 'systemctl' no está disponible. No se pueden reiniciar los servicios automáticamente."
        return 1
    fi

    for service in "${CRITICAL_SERVICES[@]}"; do
        # Comprueba si el servicio existe y está activo antes de intentar reiniciarlo
        if systemctl is-active --quiet "${service}.service"; then
            log_info "Reiniciando el servicio: ${service}..."
            if systemctl restart "${service}.service"; then
                log_success "El servicio '${service}' se ha reiniciado correctamente."
            else
                log_warning "No se pudo reiniciar el servicio '${service}'."
            fi
        fi
    done

    log_success "Se ha completado el ciclo de reinicio de servicios."
}

# Habilita un servicio para que se inicie en el arranque del sistema
enable_service() {
    local service_name="$1"
    ensure_root

    if systemctl is-enabled --quiet "${service_name}.service"; then
        log_info "El servicio '${service_name}' ya está habilitado."
    else
        log_info "Habilitando el servicio '${service_name}'..."
        if systemctl enable "${service_name}.service"; then
            log_success "Servicio '${service_name}' habilitado."
        else
            log_error "No se pudo habilitar el servicio '${service_name}'."
        fi
    fi
}
