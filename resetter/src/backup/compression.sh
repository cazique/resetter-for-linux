#!/bin/bash
# Módulo para funciones de compresión

# Comprime un directorio en un archivo .tar.gz
# Parámetros:
#   $1: Directorio de origen a comprimir
#   $2: Nombre del fichero de backup de salida (sin extensión)
#   $3: Directorio de destino para el archivo comprimido
# Salida: Ruta completa al archivo comprimido
compress_directory() {
    local source_dir="$1"
    local backup_name="$2"
    local output_dir="$3"

    local compressed_file="${output_dir}/${backup_name}.tar.gz"

    log_info "Comprimiendo el directorio '$source_dir' en '$compressed_file'..."

    if tar -czf "$compressed_file" -C "$source_dir" .; then
        log_success "Compresión completada."
        echo "$compressed_file"
        return 0
    else
        log_error "Falló la compresión del directorio '$source_dir'."
        return 1
    fi
}

# Descomprime un archivo .tar.gz en un directorio
# Parámetros:
#   $1: Ruta al archivo .tar.gz
#   $2: Directorio de destino para la extracción
decompress_archive() {
    local archive_file="$1"
    local destination_dir="$2"

    log_info "Extrayendo '$archive_file' en '$destination_dir'..."
    mkdir -p "$destination_dir"

    if tar -xzf "$archive_file" -C "$destination_dir"; then
        log_success "Extracción completada."
        return 0
    else
        log_error "Falló la extracción del archivo '$archive_file'."
        return 1
    fi
}
