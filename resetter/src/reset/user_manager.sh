#!/bin/bash
# Módulo para la gestión de perfiles de usuario durante el reseteo

# Define patrones de exclusión comunes para no respaldar cachés y ficheros temporales
# de los directorios home de los usuarios.
COMMON_EXCLUDES=(
    "--exclude='*.cache'"
    "--exclude='*.Cache'"
    "--exclude='*.thumbnails'"
    "--exclude='*.tmp'"
    "--exclude='Trash'"
    "--exclude='.dbus'"
    "--exclude='.local/share/Trash'"
    "--exclude='.local/share/baloo'"
    "--exclude='.config/pulse'"
    "--exclude='.config/dconf'"
)

# Respalda los ficheros de configuración (dotfiles) de todos los usuarios no root
# Parámetro:
#   $1: Directorio de destino para los backups
backup_all_user_dotfiles() {
    local backup_root_dir="$1"
    ensure_root

    log_info "Iniciando backup de los 'dotfiles' de los usuarios..."
    mkdir -p "$backup_root_dir"

    # Itera sobre todos los usuarios que tienen un directorio home en /home
    getent passwd | grep -E ':/home/[^:]+' | cut -d: -f1,6 | while IFS=: read -r user home_dir; do
        if [[ "$user" == "root" ]]; then
            continue
        fi

        log_info "Respaldando configuraciones del usuario '$user'..."
        local user_backup_dir="${backup_root_dir}/${user}"
        mkdir -p "$user_backup_dir"

        # Copia todos los ficheros y directorios ocultos del home del usuario
        find "$home_dir" -maxdepth 1 -name ".*" -exec cp -a {} "$user_backup_dir/" \;

        log_success "Backup de 'dotfiles' para '$user' completado en '$user_backup_dir'."
    done
}

# Resetea el perfil de todos los usuarios no root eliminando sus ficheros de configuración
reset_all_user_profiles() {
    ensure_root

    # Usar el nuevo sistema de advertencias
    confirm_critical_action "RESETEAR PERFILES DE USUARIO" "CONFIRMAR" || return 1

    getent passwd | grep -E ':/home/[^:]+' | cut -d: -f1,6 | while IFS=: read -r user home_dir; do
        if [[ "$user" == "root" ]]; then
            continue
        fi

        log_info "Reseteando el perfil del usuario '$user'..."

        # Elimina todos los ficheros y directorios ocultos (dotfiles)
        # ¡Esta es una operación destructiva!
        find "$home_dir" -maxdepth 1 -name ".*" -exec rm -rf {} \;

        # Opcional: Restaurar un esqueleto de perfil por defecto si existe
        if [[ -d /etc/skel ]]; then
            log_info "Restaurando ficheros de /etc/skel para '$user'..."
            cp -a /etc/skel/.[^.]* "$home_dir/"
            chown -R "${user}:${user}" "$home_dir"
        fi

        log_success "Perfil de '$user' reseteado a los valores por defecto."
    done
}
