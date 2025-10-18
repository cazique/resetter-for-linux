#!/bin/bash
# Módulo principal que orquesta el proceso de reseteo del sistema

# Cargar todos los módulos de reseteo necesarios
source "$SCRIPT_DIR/src/reset/user_manager.sh"
source "$SCRIPT_DIR/src/reset/package_restorer.sh"
source "$SCRIPT_DIR/src/reset/service_manager.sh"
# Nota: grub_manager.sh ya se carga en el script principal

# --- FLUJOS DE RESETEO ---

# FLUJO 1: Reseteo Suave (Solo perfiles de usuario)
# Este reseteo limpia las configuraciones de los usuarios pero no toca los paquetes del sistema.
perform_soft_reset() {
    log_info "--- INICIANDO RESETEO SUAVE DEL SISTEMA ---"

    # 1. Realizar comprobaciones previas
    ensure_root
    check_filesystem_writable

    # 2. Crear un backup temporal de las configuraciones de usuario
    local user_backup_dir="./resetter-data/backups/soft_reset_users_$(date +%Y%m%d_%H%M%S)"
    backup_all_user_dotfiles "$user_backup_dir"

    # 3. Resetear los perfiles de usuario
    reset_all_user_profiles

    # 4. Reiniciar servicios críticos (especialmente el gestor de pantalla)
    restart_critical_services

    log_success "--- RESETEO SUAVE COMPLETADO ---"
    log_info "Se recomienda reiniciar la sesión o el sistema para aplicar todos los cambios."
}

# FLUJO 2: Reseteo Completo (Perfiles de usuario Y paquetes)
# ¡ADVERTENCIA! Esto devolverá el sistema a un estado similar al de la instalación inicial.
perform_full_reset() {
    log_info "--- INICIANDO RESETEO COMPLETO DEL SISTEMA ---"

    # 1. Realizar comprobaciones previas
    ensure_root
    check_filesystem_writable
    check_network_connection
    check_disk_space "/" 2097152 # Requerir al menos 2GB libres

    # 2. Crear backups
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local user_backup_dir="./resetter-data/backups/full_reset_users_${backup_timestamp}"
    local packages_backup_file="./resetter-data/backups/full_reset_packages_${backup_timestamp}.list"

    backup_all_user_dotfiles "$user_backup_dir"
    backup_user_packages_list "$packages_backup_file"
    backup_grub_config # Función de grub_manager.sh

    # 3. Purgar paquetes de usuario
    purge_all_user_packages

    # 4. Reinstalar paquetes esenciales para asegurar la estabilidad
    reinstall_core_packages

    # 5. Resetear perfiles de usuario
    reset_all_user_profiles

    # 6. Reinstalar y actualizar GRUB
    # (Asumiendo que detectamos el dispositivo de arranque, por ahora es un placeholder)
    local boot_device
    boot_device=$(df / | awk 'NR==2 {print $1}' | sed 's/[0-9]*$//') # Estimación simple
    reinstall_grub "$boot_device"
    update_grub_config

    # 7. Limpiar kernels antiguos
    cleanup_old_kernels

    # 8. Reiniciar servicios
    restart_critical_services

    log_success "--- RESETEO COMPLETO COMPLETADO ---"
    log_warning "Es IMPERATIVO reiniciar el sistema ahora."
}
