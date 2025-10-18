#!/bin/bash
# Módulo para funciones de cifrado y descifrado

# Cifra un fichero usando GPG con una contraseña (cifrado simétrico)
# Parámetros:
#   $1: Ruta al fichero a cifrar
#   $2: Contraseña para el cifrado
# Salida: Ruta al fichero cifrado (.gpg)
encrypt_file() {
    local source_file="$1"
    local password="$2"

    local encrypted_file="${source_file}.gpg"

    log_info "Cifrando el fichero '$source_file'..."

    echo "$password" | gpg --batch --yes --passphrase-fd 0 \
        --pinentry-mode loopback \
        --symmetric --cipher-algo AES256 \
        --output "$encrypted_file" "$source_file"

    if [[ $? -eq 0 ]]; then
        log_success "Fichero cifrado correctamente en '$encrypted_file'."
        # Opcional: eliminar el fichero original sin cifrar por seguridad
        # rm "$source_file"
        echo "$encrypted_file"
        return 0
    else
        log_error "Falló el cifrado del fichero."
        return 1
    fi
}

# Descifra un fichero .gpg usando una contraseña
# Parámetros:
#   $1: Ruta al fichero .gpg a descifrar
#   $2: Contraseña para el descifrado
# Salida: Ruta al fichero descifrado
decrypt_file() {
    local encrypted_file="$1"
    local password="$2"

    # Elimina la extensión .gpg para el nombre del fichero de salida
    local decrypted_file="${encrypted_file%.gpg}"

    log_info "Descifrando el fichero '$encrypted_file'..."

    echo "$password" | gpg --batch --yes --passphrase-fd 0 \
        --pinentry-mode loopback \
        --output "$decrypted_file" --decrypt "$encrypted_file"

    if [[ $? -eq 0 ]]; then
        log_success "Fichero descifrado correctamente en '$decrypted_file'."
        echo "$decrypted_file"
        return 0
    else
        log_error "Falló el descifrado. La contraseña puede ser incorrecta."
        return 1
    fi
}
