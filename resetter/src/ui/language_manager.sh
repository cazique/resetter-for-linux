#!/bin/bash

LANGUAGE_MANAGER_VERSION="2.0"

# Idiomas soportados
SUPPORTED_LANGUAGES=("es" "en" "fr" "de" "zh" "hi")

# Cargar textos según idioma
load_language_texts() {
    local language="${1:-auto}"

    if [[ "$language" == "auto" ]]; then
        language=$(detect_system_language)
    fi

    # Verificar soporte
    if ! array_contains "$language" "${SUPPORTED_LANGUAGES[@]}"; then
        language="en"  # Idioma por defecto
    fi

    local lang_file="./resetter/locales/${language}.conf"

    if [[ -f "$lang_file" ]]; then
        source "$lang_file"
        CURRENT_LANGUAGE="$language"
        log_success "Idioma configurado: $language"
    else
        log_error "Archivo de idioma no encontrado: $lang_file"
        # Cargar inglés como fallback si el archivo de idioma no existe
        source "./resetter/locales/en.conf"
        CURRENT_LANGUAGE="en"
    fi
}

# Detectar idioma del sistema
detect_system_language() {
    local system_lang="${LANG%_*}"

    case "$system_lang" in
        es) echo "es" ;;
        en) echo "en" ;;
        fr) echo "fr" ;;
        de) echo "de" ;;
        zh) echo "zh" ;;
        hi) echo "hi" ;;
        *) echo "en" ;;
    esac
}

# Función para obtener texto traducido
t() {
    local key="$1"
    local default="$2"

    # Buscar en variables cargadas
    local var_name="TEXT_${key}"
    local text="${!var_name:-}"

    if [[ -z "$text" ]]; then
        log_warning "Texto no encontrado para clave: $key"
        text="$default"
    fi

    echo "$text"
}

# Mostrar selector de idioma interactivo
show_language_selector() {
    echo "Selecciona idioma / Select language:"
    echo "1. Español"
    echo "2. English"
    echo "3. Français"
    echo "4. Deutsch"
    echo "5. 中文"
    echo "6. हिन्दी"

    read -p "Opción / Option (1-6): " choice

    case $choice in
        1) load_language_texts "es" ;;
        2) load_language_texts "en" ;;
        3) load_language_texts "fr" ;;
        4) load_language_texts "de" ;;
        5) load_language_texts "zh" ;;
        6) load_language_texts "hi" ;;
        *) load_language_texts "en" ;;
    esac
}
