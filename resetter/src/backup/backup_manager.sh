#!/bin/bash

# Cargar módulos de soporte
source "$SCRIPT_DIR/src/backup/compression.sh"
source "$SCRIPT_DIR/src/backup/encryption.sh"
source "$SCRIPT_DIR/src/reset/package_restorer.sh" # Para la función de backup de paquetes

BACKUP_MANAGER_VERSION="3.0"

# Flujo principal de backup
main_backup_flow() {
    local backup_type="$1"

    log_info "Iniciando flujo de backup..."

    # 1. Selección de datos
    local data_selection=$(select_backup_data)

    # 2. Selección de método
    local backup_method=$(select_backup_method "$backup_type")

    # 3. Configuración de cifrado
    local encryption_config=$(configure_encryption)

    # 4. Ejecutar backup
    execute_backup "$data_selection" "$backup_method" "$encryption_config"

    # 5. Verificación
    verify_backup
}

# Selección interactiva de datos
select_backup_data() {
    local selected_data=()

    echo "Selecciona los datos a respaldar:"
    echo "1. Directorio Home completo"
    echo "2. Configuraciones del sistema"
    echo "3. Datos de Docker"
    echo "4. Lista de paquetes instalados"
    echo "5. Configuraciones de servicios"
    echo "6. Datos personalizados"
    echo "7. Todo lo anterior"

    read -p "Selecciona opciones (ej: 1,3,5): " choices

    IFS=',' read -ra options <<< "$choices"

    for option in "${options[@]}"; do
        case $option in
            1) selected_data+=("home") ;;
            2) selected_data+=("configs") ;;
            3) selected_data+=("docker") ;;
            4) selected_data+=("packages") ;;
            5) selected_data+=("services") ;;
            6) selected_data+=("custom") ;;
            7) selected_data+=("all") ;;
        esac
    done

    echo "${selected_data[@]}"
}

# Placeholder: Selección de método de backup
select_backup_method() {
    log_info "Seleccionando método de backup..."
    echo "local" # Devolver 'local' por defecto por ahora
}

# Configurar cifrado con contraseña
configure_encryption() {
    local encryption_config=""

    read -p "¿Cifrar backup con contraseña? (s/n): " encrypt_choice
    if [[ "$encrypt_choice" == "s" ]]; then
        read -sp "Contraseña para cifrado: " password
        echo
        read -sp "Confirmar contraseña: " password_confirm
        echo

        if [[ "$password" != "$password_confirm" ]]; then
            log_error "Las contraseñas no coinciden"
            return 1
        fi

        encryption_config="$password"
    fi

    echo "$encryption_config"
}

# Ejecutar backup
execute_backup() {
    local data_selection="$1"
    local backup_method="$2"
    local encryption_config="$3"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="resetter_backup_${timestamp}"
    local temp_dir="./resetter-data/temp/${backup_name}"

    mkdir -p "$temp_dir"

    log_info "Preparando backup $backup_name..."

    # Recolectar datos seleccionados
    for data_type in $data_selection; do
        case "$data_type" in
            home) backup_home_directory "$temp_dir" ;;
            configs) backup_system_configs "$temp_dir" ;;
            docker) backup_docker_data "$temp_dir" ;;
            packages) backup_package_list "$temp_dir" ;;
            services) backup_service_configs "$temp_dir" ;;
            custom) backup_custom_data "$temp_dir" ;;
            all) backup_complete_system "$temp_dir" ;;
        esac
    done

    # Comprimir y cifrar
    local final_backup=$(compress_and_encrypt "$temp_dir" "$backup_name" "$encryption_config")

    # Mover a destino final
    case "$backup_method" in
        local) move_to_local_storage "$final_backup" ;;
        usb) move_to_usb_storage "$final_backup" ;;
        cloud) upload_to_cloud "$final_backup" ;;
    esac

    # Limpiar temporal
    rm -rf "$temp_dir"

    log_success "Backup completado: $final_backup"
}

# Placeholder: Mover a almacenamiento local
move_to_local_storage() {
    log_info "Moviendo backup a almacenamiento local..."
}
# Placeholder: Mover a USB
move_to_usb_storage() {
    log_warning "Funcionalidad de mover a USB no implementada."
}
# Placeholder: Subir a la nube
upload_to_cloud() {
    log_warning "Funcionalidad de subir a la nube no implementada."
}

# Backup de directorio home
backup_home_directory() {
    local temp_dir="$1"

    log_info "Respaldando directorios home..."

    # Excluir archivos temporales y cache
    local exclude_patterns=(
        "--exclude=*.tmp"
        "--exclude=*.temp"
        "--exclude=*.cache"
        "--exclude=*.Cache"
        "--exclude=Trash"
        "--exclude=.thumbnails"
        "--exclude=.local/share/Trash"
    )

    # Respaldar cada home de usuario
    getent passwd | grep -E '/home/[^/]+' | cut -d: -f6 | \
    while read home_dir; do
        if [[ -d "$home_dir" ]]; then
            local user_name=$(basename "$home_dir")
            log_info "Respaldando home de $user_name"

            tar "${exclude_patterns[@]}" -czf \
                "$temp_dir/home_${user_name}.tar.gz" \
                -C "/home" "$user_name"
        fi
    done
}

# Backup de configuraciones críticas del sistema desde /etc
backup_system_configs() {
    local temp_dir="$1"
    log_info "Respaldando configuraciones críticas del sistema..."

    local config_backup_dir="${temp_dir}/system_configs"
    mkdir -p "$config_backup_dir"

    local critical_configs=(
        "/etc/fstab"
        "/etc/hostname"
        "/etc/hosts"
        "/etc/network/interfaces"
        "/etc/resolv.conf"
        "/etc/nsswitch.conf"
        "/etc/sudoers"
        "/etc/sudoers.d/"
    )

    for config_path in "${critical_configs[@]}"; do
        if [[ -e "$config_path" ]]; then
            cp -aR "$config_path" "$config_backup_dir/"
        fi
    done
    log_success "Copia de seguridad de configuraciones del sistema completada."
}

# Backup de la lista de paquetes instalados por el usuario
backup_package_list() {
    local temp_dir="$1"
    local package_list_file="${temp_dir}/packages.list"

    # Reutiliza la función del módulo de restauración de paquetes
    backup_user_packages_list "$package_list_file"
}

# Backup de configuraciones de servicios comunes (ej: web servers)
backup_service_configs() {
    local temp_dir="$1"
    log_info "Respaldando configuraciones de servicios..."

    local service_config_dir="${temp_dir}/service_configs"
    mkdir -p "$service_config_dir"

    # Ejemplo para Nginx y Apache
    if [[ -d "/etc/nginx" ]]; then
        cp -aR "/etc/nginx" "$service_config_dir/"
        log_info "Configuración de Nginx respaldada."
    fi
    if [[ -d "/etc/apache2" ]]; then
        cp -aR "/etc/apache2" "$service_config_dir/"
        log_info "Configuración de Apache2 respaldada."
    fi
}

# Permite al usuario especificar un directorio personalizado para el backup
backup_custom_data() {
    local temp_dir="$1"
    read -rp "Introduce la ruta absoluta al directorio personalizado que quieres respaldar: " custom_path

    if [[ -d "$custom_path" ]]; then
        log_info "Respaldando directorio personalizado: $custom_path"
        local custom_backup_dir="${temp_dir}/custom_data"
        mkdir -p "$custom_backup_dir"
        cp -aR "$custom_path" "$custom_backup_dir/"
        log_success "Directorio personalizado respaldado."
    else
        log_warning "La ruta '$custom_path' no es un directorio válido. Se omitirá."
    fi
}

# Realiza un backup completo llamando a todas las funciones de backup individuales
backup_complete_system() {
    local temp_dir="$1"
    log_info "Iniciando backup completo del sistema..."

    backup_home_directory "$temp_dir"
    backup_system_configs "$temp_dir"
    backup_package_list "$temp_dir"
    backup_service_configs "$temp_dir"
    backup_docker_data "$temp_dir"
}

# Backup de datos Docker
backup_docker_data() {
    local temp_dir="$1"

    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker no está instalado, omitiendo..."
        return 0
    fi

    log_info "Respaldando datos de Docker..."

    # Backup de contenedores en ejecución
    docker ps -q | while read container; do
        local container_name=$(docker inspect --format='{{.Name}}' "$container" | sed 's/^\///')
        log_info "Respaldando contenedor: $container_name"

        # Exportar configuración
        docker inspect "$container" > "$temp_dir/docker_container_${container_name}.json"

        # Generar docker-compose
        docker container inspect "$container" --format='{{json .Config}}' > \
            "$temp_dir/docker_config_${container_name}.json"
    done

    # Backup de volúmenes
    docker volume ls -q | while read volume; do
        log_info "Respaldando volumen: $volume"

        # Crear backup del volumen
        docker run --rm -v "$volume":/data -v "$temp_dir":/backup \
            alpine tar czf "/backup/docker_volume_${volume}.tar.gz" -C /data .
    done

    # Backup de imágenes
    docker images --format "{{.Repository}}:{{.Tag}}" | while read image; do
        if [[ "$image" != "<none>:<none>" ]]; then
            local image_name=$(echo "$image" | tr '/:' '_')
            log_info "Respaldando imagen: $image"

            docker save "$image" | gzip > "$temp_dir/docker_image_${image_name}.tar.gz"
        fi
    done

    # Generar script de restauración
    generate_docker_restore_script "$temp_dir"
}

# Generar script de restauración Docker
generate_docker_restore_script() {
    local temp_dir="$1"

    cat > "$temp_dir/restore_docker.sh" << 'EOF'
#!/bin/bash
# Script de restauración Docker generado por Resetter

set -e

echo "Restaurando contenedores Docker..."

# Restaurar imágenes
for image_file in docker_image_*.tar.gz; do
    if [[ -f "$image_file" ]]; then
        echo "Cargando imagen: $image_file"
        docker load -i "$image_file"
    fi
done

# Restaurar volúmenes
for volume_file in docker_volume_*.tar.gz; do
    if [[ -f "$volume_file" ]]; then
        volume_name=$(echo "$volume_file" | sed 's/docker_volume_//' | sed 's/.tar.gz//')
        echo "Restaurando volumen: $volume_name"

        docker volume create "$volume_name"
        docker run --rm -v "$volume_name":/data -v $(pwd):/backup \
            alpine tar xzf "/backup/$volume_file" -C /data
    fi
done

echo "Restauración Docker completada"
EOF

    chmod +x "$temp_dir/restore_docker.sh"
}

# Comprimir y, opcionalmente, cifrar el directorio temporal del backup
compress_and_encrypt() {
    local temp_dir="$1"
    local backup_name="$2"
    local password="$3"

    # Define el directorio de salida para los backups
    local output_dir="./resetter-data/backups"

    # 1. Comprimir el directorio
    local compressed_file
    compressed_file=$(compress_directory "$temp_dir" "$backup_name" "$output_dir")

    if [[ $? -ne 0 ]]; then
        log_error "El proceso de backup se detuvo debido a un error de compresión."
        return 1
    fi

    # 2. Cifrar el archivo comprimido si se proporcionó una contraseña
    if [[ -n "$password" ]]; then
        local encrypted_file
        encrypted_file=$(encrypt_file "$compressed_file" "$password")

        if [[ $? -eq 0 ]]; then
            # Si el cifrado fue exitoso, eliminamos el archivo comprimido sin cifrar
            rm "$compressed_file"
            echo "$encrypted_file"
        else
            log_error "El proceso de backup se detuvo debido a un error de cifrado."
            return 1
        fi
    else
        # Si no hay contraseña, devolvemos la ruta al archivo comprimido
        echo "$compressed_file"
    fi
}

# Placeholder: Verificar backup
verify_backup() {
    log_info "Verificando el backup..."
    log_success "Verificación de backup completada (placeholder)."
}
