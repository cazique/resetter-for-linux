package com.empresa.gestordocumental.ui.theme

import androidx.compose.ui.graphics.Color

/*
 * Paleta corporativa (azul petróleo + ámbar) generada siguiendo los roles
 * tonales de Material 3. Todos los pares "on*" cumplen contraste WCAG AA
 * (≥ 4.5:1) sobre su color base.
 */

// ---------- Modo claro ----------
val md_light_primary = Color(0xFF0D4F8B)
val md_light_onPrimary = Color(0xFFFFFFFF)
val md_light_primaryContainer = Color(0xFFD3E4FF)
val md_light_onPrimaryContainer = Color(0xFF001C38)
val md_light_secondary = Color(0xFF545F71)
val md_light_onSecondary = Color(0xFFFFFFFF)
val md_light_secondaryContainer = Color(0xFFD8E3F8)
val md_light_onSecondaryContainer = Color(0xFF111C2B)
val md_light_tertiary = Color(0xFF8A5100)
val md_light_onTertiary = Color(0xFFFFFFFF)
val md_light_tertiaryContainer = Color(0xFFFFDCBE)
val md_light_onTertiaryContainer = Color(0xFF2C1600)
val md_light_error = Color(0xFFBA1A1A)
val md_light_onError = Color(0xFFFFFFFF)
val md_light_errorContainer = Color(0xFFFFDAD6)
val md_light_onErrorContainer = Color(0xFF410002)
val md_light_background = Color(0xFFF8F9FC)
val md_light_onBackground = Color(0xFF191C20)
val md_light_surface = Color(0xFFF8F9FC)
val md_light_onSurface = Color(0xFF191C20)
val md_light_surfaceVariant = Color(0xFFDFE2EB)
val md_light_onSurfaceVariant = Color(0xFF43474E)
val md_light_outline = Color(0xFF73777F)
val md_light_outlineVariant = Color(0xFFC3C6CF)
val md_light_inverseSurface = Color(0xFF2E3135)
val md_light_inverseOnSurface = Color(0xFFEFF0F4)
val md_light_inversePrimary = Color(0xFFA2C9FF)
val md_light_surfaceContainerLowest = Color(0xFFFFFFFF)
val md_light_surfaceContainerLow = Color(0xFFF2F3F7)
val md_light_surfaceContainer = Color(0xFFECEEF2)
val md_light_surfaceContainerHigh = Color(0xFFE6E8EC)
val md_light_surfaceContainerHighest = Color(0xFFE1E2E6)
val md_light_scrim = Color(0xFF000000)

// ---------- Modo oscuro ----------
val md_dark_primary = Color(0xFFA2C9FF)
val md_dark_onPrimary = Color(0xFF00315B)
val md_dark_primaryContainer = Color(0xFF004880)
val md_dark_onPrimaryContainer = Color(0xFFD3E4FF)
val md_dark_secondary = Color(0xFFBCC7DC)
val md_dark_onSecondary = Color(0xFF263141)
val md_dark_secondaryContainer = Color(0xFF3D4758)
val md_dark_onSecondaryContainer = Color(0xFFD8E3F8)
val md_dark_tertiary = Color(0xFFFFB871)
val md_dark_onTertiary = Color(0xFF4A2800)
val md_dark_tertiaryContainer = Color(0xFF693C00)
val md_dark_onTertiaryContainer = Color(0xFFFFDCBE)
val md_dark_error = Color(0xFFFFB4AB)
val md_dark_onError = Color(0xFF690005)
val md_dark_errorContainer = Color(0xFF93000A)
val md_dark_onErrorContainer = Color(0xFFFFDAD6)
val md_dark_background = Color(0xFF0F1419)
val md_dark_onBackground = Color(0xFFE1E2E8)
val md_dark_surface = Color(0xFF0F1419)
val md_dark_onSurface = Color(0xFFE1E2E8)
val md_dark_surfaceVariant = Color(0xFF43474E)
val md_dark_onSurfaceVariant = Color(0xFFC3C6CF)
val md_dark_outline = Color(0xFF8D9199)
val md_dark_outlineVariant = Color(0xFF43474E)
val md_dark_inverseSurface = Color(0xFFE1E2E8)
val md_dark_inverseOnSurface = Color(0xFF2E3135)
val md_dark_inversePrimary = Color(0xFF0D4F8B)
val md_dark_surfaceContainerLowest = Color(0xFF0A0E13)
val md_dark_surfaceContainerLow = Color(0xFF181C21)
val md_dark_surfaceContainer = Color(0xFF1C2025)
val md_dark_surfaceContainerHigh = Color(0xFF262A30)
val md_dark_surfaceContainerHighest = Color(0xFF31353B)
val md_dark_scrim = Color(0xFF000000)

// ---------- Colores semánticos de negocio ----------
/** Colores de estado de documento, con variante para cada modo. */
object StatusColors {
    val PendingLight = Color(0xFF8A5100)
    val PendingDark = Color(0xFFFFB871)
    val ProcessedLight = Color(0xFF1B6C37)
    val ProcessedDark = Color(0xFF8BD89B)
    val ArchivedLight = Color(0xFF545F71)
    val ArchivedDark = Color(0xFFBCC7DC)
}

/** Colores por defecto de las categorías predefinidas (coinciden con el backend). */
object CategoryColors {
    val FacturaProveedor = Color(0xFF1E88E5)
    val FacturaCliente = Color(0xFF43A047)
    val TicketComida = Color(0xFFFB8C00)
    val TicketGasolina = Color(0xFFE53935)
    val Varios = Color(0xFF8E24AA)
    val Fallback = Color(0xFF607D8B)
}
