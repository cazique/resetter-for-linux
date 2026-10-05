package com.empresa.gestordocumental.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.empresa.gestordocumental.ui.theme.CategoryColors

/** Opción genérica para [DropdownField]. */
data class DropdownOption<T>(
    val value: T,
    val label: String,
    val supportingText: String? = null,
    val color: Color? = null,
)

/**
 * Campo de selección Material 3 (ExposedDropdownMenu) con soporte de error,
 * texto de ayuda y punto de color opcional por opción.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun <T> DropdownField(
    label: String,
    options: List<DropdownOption<T>>,
    selected: DropdownOption<T>?,
    onSelected: (T) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "Seleccionar",
    enabled: Boolean = true,
    errorText: String? = null,
    leadingIcon: (@Composable () -> Unit)? = null,
) {
    var expanded by remember { mutableStateOf(false) }
    val selectedColor = selected?.color
    val fieldLeadingIcon: (@Composable () -> Unit)? =
        if (selectedColor != null) {
            { ColorDot(selectedColor) }
        } else {
            leadingIcon
        }

    ExposedDropdownMenuBox(
        expanded = expanded && enabled,
        onExpandedChange = { if (enabled) expanded = it },
        modifier = modifier,
    ) {
        OutlinedTextField(
            value = selected?.label.orEmpty(),
            onValueChange = {},
            readOnly = true,
            enabled = enabled,
            label = { Text(label) },
            placeholder = { Text(placeholder) },
            leadingIcon = fieldLeadingIcon,
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            isError = errorText != null,
            supportingText = errorText?.let { { Text(it) } },
            singleLine = true,
            modifier = Modifier
                .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled)
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded && enabled, onDismissRequest = { expanded = false }) {
            if (options.isEmpty()) {
                DropdownMenuItem(text = { Text("Sin opciones disponibles") }, onClick = { expanded = false }, enabled = false)
            }
            options.forEach { option ->
                DropdownMenuItem(
                    text = {
                        if (option.supportingText != null) {
                            Column {
                                Text(option.label, style = MaterialTheme.typography.bodyLarge)
                                Text(
                                    option.supportingText,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        } else {
                            Text(option.label)
                        }
                    },
                    leadingIcon = option.color?.let { color -> @Composable { ColorDot(color) } },
                    onClick = {
                        onSelected(option.value)
                        expanded = false
                    },
                    contentPadding = ExposedDropdownMenuDefaults.ItemContentPadding,
                )
            }
        }
    }
}

@Composable
fun ColorDot(color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .size(12.dp)
            .background(color, CircleShape),
    )
}

/** Botón principal que muestra un indicador de progreso mientras [loading] es true. */
@Composable
fun LoadingButton(
    text: String,
    loading: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    loadingText: String = text,
    icon: (@Composable () -> Unit)? = null,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !loading,
        modifier = modifier
            .fillMaxWidth()
            .height(52.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.onPrimary,
                )
                Spacer(Modifier.width(12.dp))
                Text(loadingText)
            } else {
                icon?.let {
                    it()
                    Spacer(Modifier.width(8.dp))
                }
                Text(text)
            }
        }
    }
}

/** Convierte "#RRGGBB" en [Color] con color de reserva si el formato no es válido. */
fun parseHexColor(hex: String?): Color = runCatching {
    Color(android.graphics.Color.parseColor(hex))
}.getOrDefault(CategoryColors.Fallback)
