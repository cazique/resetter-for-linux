#!/bin/bash
# Módulo que define la lógica de los menús interactivos

# Cargar dependencias de módulos para tener acceso a sus funciones
source "$SCRIPT_DIR/src/core/package_manager.sh"

# --- Menú de Copia de Seguridad ---
backup_menu() {
    clear
    echo "--- MENÚ DE COPIA DE SEGURIDAD ---"
    echo "Este asistente te guiará para crear una copia de seguridad."
    # Llama al flujo principal de backup definido en el backup_manager.sh
    main_backup_flow "interactive"
    read -p "Presiona Enter para volver al menú principal..."
}

# --- Menú de Reseteo ---
reset_menu() {
    while true; do
        clear
        echo "--- MENÚ DE RESTABLECIMIENTO ---"
        echo -e "${YELLOW}Por favor, selecciona el tipo de reseteo que deseas realizar.${NC}"
        echo
        echo "1. Reseteo Suave (Recomendado)"
        echo "   - Restaura las configuraciones de los usuarios a sus valores por defecto."
        echo "   - No elimina programas instalados."
        echo
        echo "2. Reseteo Completo (Avanzado)"
        echo "   - ${RED}¡ACCIÓN DESTRUCTIVA!${NC}"
        echo "   - Elimina todos los programas instalados por el usuario."
        echo "   - Restaura el sistema a un estado similar al de la instalación inicial."
        echo
        echo "3. Volver al menú principal"

        read -p "Selecciona una opción: " choice

        case $choice in
            1)
                perform_soft_reset
                read -p "Reseteo suave completado. Presiona Enter para continuar..."
                ;;
            2)
                perform_full_reset
                read -p "Reseteo completo completado. Presiona Enter para continuar..."
                ;;
            3)
                break
                ;;
            *)
                echo "Opción no válida. Inténtalo de nuevo."; sleep 2
                ;;
        esac
    done
}

# --- Menú de Dry Run ---
dry_run_menu() {
    clear
    echo "--- SIMULACIÓN DRY RUN ---"
    # Llama a la función de simulación del módulo dry_run
    simulate_system_changes
    read -p "Simulación completada. Presiona Enter para volver al menú principal..."
}

# --- Menú de Reportes (Implementación simple) ---
report_menu() {
    clear
    echo "--- GENERADOR DE REPORTES ---"
    local report_file="./resetter-data/reports/system_report_$(date +%Y%m%d_%H%M%S).txt"
    log_info "Generando reporte del sistema en: $report_file"

    {
        echo "--- REPORTE DEL SISTEMA - $(date) ---"
        echo
        echo "Distribución: $CURRENT_DISTRO_NAME"
        echo "Kernel: $(uname -r)"
        echo
        echo "--- Espacio en Disco ---"
        df -h
        echo
        echo "--- Memoria ---"
        free -h
        echo
        echo "--- Paquetes Instalados por el Usuario ---"
        list_installed_packages
    } > "$report_file"

    log_success "Reporte generado exitosamente."
    read -p "Presiona Enter para continuar..."
}

# --- Menú de Restauración (Placeholder con lógica de selección) ---
restore_menu() {
    clear
    echo "--- MENÚ DE RESTAURACIÓN DE BACKUP ---"
    local backup_dir="./resetter-data/backups"

    if [[ ! -d "$backup_dir" || -z "$(ls -A "$backup_dir")" ]]; then
        log_warning "No se encontraron backups en el directorio: $backup_dir"
        read -p "Presiona Enter para continuar..."
        return
    fi

    echo "Por favor, selecciona el backup que deseas restaurar:"
    select backup_file in "$backup_dir"/*; do
        if [[ -n "$backup_file" ]]; then
            log_info "Has seleccionado: $backup_file"
            # Aquí iría la lógica de restauración, que es compleja y se deja para el futuro
            log_warning "La funcionalidad de restauración aún no está implementada."
            read -p "Presiona Enter para continuar..."
            break
        else
            log_warning "Selección no válida."
        fi
    done
}

# --- Menú de Configuración ---
settings_menu() {
    clear
    echo "--- MENÚ DE CONFIGURACIÓN ---"
    show_language_selector
}

# --- Advertencia de Seguridad Inicial ---
show_safety_warning() {
    echo -e "${YELLOW}Bienvenido a Resetter. Esta es una herramienta potente.${NC}"
    echo "Úsala con precaución. Se recomienda hacer un 'Dry Run' primero."
    sleep 3
}

# --- Función de ayuda para el gestor de idiomas ---
array_contains() {
    local seeking=$1; shift
    for element; do
        if [[ "$element" == "$seeking" ]]; then
            return 0
        fi
    done
    return 1
}
