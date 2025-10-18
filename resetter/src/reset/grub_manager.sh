#!/bin/bash

GRUB_MANAGER_VERSION="2.0"

# Detectar configuración de GRUB
detect_grub_config() {
    local grub_config=""

    # Buscar archivo de configuración GRUB
    for config in "/boot/grub/grub.cfg" "/boot/grub2/grub.cfg" "/boot/efi/EFI/*/grub.cfg"; do
        if [[ -f $config ]]; then
            grub_config="$config"
            break
        fi
    done

    if [[ -z "$grub_config" ]]; then
        log_warning "No se encontró configuración GRUB"
        return 1
    fi

    echo "$grub_config"
    return 0
}

# Respaldar configuración GRUB
backup_grub_config() {
    local backup_dir="./resetter-data/backups/grub"
    mkdir -p "$backup_dir"

    local grub_config=$(detect_grub_config)
    if [[ -n "$grub_config" ]]; then
        local backup_file="$backup_dir/grub.cfg.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$grub_config" "$backup_file"
        log_success "Configuración GRUB respaldada en $backup_file"
    fi

    # Respaldar configuración de dispositivos
    if command -v grub-probe >/dev/null 2>&1; then
        grub-probe -t device / > "$backup_dir/boot_device.info" 2>/dev/null
    fi
}

# Reinstalar GRUB
reinstall_grub() {
    local target_device="$1"

    log_info "Reinstalando GRUB en $target_device..."

    # Detectar si es UEFI o BIOS
    if [[ -d /sys/firmware/efi ]]; then
        log_info "Sistema UEFI detectado"
        reinstall_grub_uefi "$target_device"
    else
        log_info "Sistema BIOS detectado"
        reinstall_grub_bios "$target_device"
    fi
}

# Reinstalación GRUB para UEFI
reinstall_grub_uefi() {
    local target_device="$1"

    # Montar EFI system partition
    local efi_partition=$(findmnt -n -o SOURCE /boot/efi 2>/dev/null)
    if [[ -z "$efi_partition" ]]; then
        efi_partition=$(lsblk -o NAME,MOUNTPOINT | grep '/boot/efi' | awk '{print $1}')
    fi

    if [[ -n "$efi_partition" ]]; then
        log_info "Instalando GRUB para UEFI en $efi_partition"

        # Instalar GRUB
        if grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB; then
            log_success "GRUB UEFI instalado exitosamente"
        else
            log_error "Error instalando GRUB UEFI"
            return 1
        fi
    else
        log_error "No se pudo encontrar partición EFI"
        return 1
    fi
}

# Reinstalación GRUB para BIOS
reinstall_grub_bios() {
    local target_device="$1"

    log_info "Instalando GRUB para BIOS en $target_device"

    if grub-install "$target_device"; then
        log_success "GRUB BIOS instalado exitosamente en $target_device"
    else
        log_error "Error instalando GRUB BIOS en $target_device"
        return 1
    fi
}

# Actualizar configuración GRUB
update_grub_config() {
    log_info "Actualizando configuración GRUB..."

    if command -v update-grub >/dev/null 2>&1; then
        # Debian/Ubuntu
        if update-grub; then
            log_success "Configuración GRUB actualizada"
        else
            log_error "Error actualizando GRUB con update-grub"
            return 1
        fi
    elif command -v grub2-mkconfig >/dev/null 2>&1; then
        # Fedora/RHEL
        if grub2-mkconfig -o /boot/grub2/grub.cfg; then
            log_success "Configuración GRUB actualizada"
        else
            log_error "Error actualizando GRUB con grub2-mkconfig"
            return 1
        fi
    else
        log_error "No se encontró comando para actualizar GRUB"
        return 1
    fi
}

# Verificar instalación GRUB
verify_grub_installation() {
    local target_device="$1"

    log_info "Verificando instalación GRUB..."

    # Verificar que GRUB está instalado en el dispositivo
    if [[ -f /usr/sbin/grub-install ]]; then
        if grub-install --version >/dev/null 2>&1; then
            log_success "GRUB instalado correctamente"
        else
            log_error "GRUB no está funcionando correctamente"
            return 1
        fi
    fi

    # Verificar archivo de configuración
    local grub_config=$(detect_grub_config)
    if [[ -n "$grub_config" && -s "$grub_config" ]]; then
        log_success "Configuración GRUB válida encontrada"
    else
        log_error "Configuración GRUB no válida o vacía"
        return 1
    fi

    return 0
}

# Manejar kernels antiguos
cleanup_old_kernels() {
    log_info "Limpiando kernels antiguos..."

    case "$(get_package_manager)" in
        apt)
            # Debian/Ubuntu
            if command -v apt-autoremove >/dev/null 2>&1; then
                apt autoremove --purge -y
            fi

            # Limpiar kernels antiguos específicamente
            current_kernel=$(uname -r)
            dpkg -l | grep 'linux-image' | grep -v "$current_kernel" | \
            awk '{print $2}' | while read pkg; do
                log_info "Eliminando kernel antiguo: $pkg"
                apt remove --purge -y "$pkg"
            done
            ;;
        dnf|yum)
            # Fedora/RHEL
            package-cleanup --oldkernels --count=1 -y
            ;;
    esac

    log_success "Limpieza de kernels completada"
}
