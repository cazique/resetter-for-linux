#!/bin/bash

# Este fichero contendrá la lógica para los menús interactivos.
# Por ahora, se definen las funciones vacías para que el script principal no falle.

backup_menu() {
    echo "Funcionalidad de menú de backup no implementada todavía."
    sleep 2
}

reset_menu() {
    echo "Funcionalidad de menú de reseteo no implementada todavía."
    sleep 2
}

dry_run_menu() {
    # Llamar a la función de simulación del módulo dry_run
    simulate_system_changes
    read -p "Presiona Enter para continuar..."
}

report_menu() {
    echo "Funcionalidad de menú de reportes no implementada todavía."
    sleep 2
}

restore_menu() {
    echo "Funcionalidad de menú de restauración no implementada todavía."
    sleep 2
}

settings_menu() {
    show_language_selector
}

show_safety_warning() {
    echo "ADVERTENCIA: Estás a punto de usar una herramienta potente."
    echo "Asegúrate de saber lo que haces."
    sleep 3
}

# La función array_contains es necesaria para el language_manager.sh
array_contains() {
    local seeking=$1; shift
    for element; do
        if [[ "$element" == "$seeking" ]]; then
            return 0
        fi
    done
    return 1
}
