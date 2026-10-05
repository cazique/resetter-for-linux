package com.empresa.gestordocumental.ui.screens.documents

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.PressInteraction
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.DocumentScanner
import androidx.compose.material.icons.filled.Euro
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SelectableDates
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import com.empresa.gestordocumental.domain.model.Category
import com.empresa.gestordocumental.domain.model.Contact
import com.empresa.gestordocumental.domain.model.ContactType
import com.empresa.gestordocumental.domain.model.UploadedDocument
import com.empresa.gestordocumental.ui.components.DropdownField
import com.empresa.gestordocumental.ui.components.DropdownOption
import com.empresa.gestordocumental.ui.components.LoadingButton
import com.empresa.gestordocumental.ui.components.parseHexColor
import com.empresa.gestordocumental.ui.scanner.rememberDocumentScanner
import com.empresa.gestordocumental.ui.theme.GestorTheme
import com.empresa.gestordocumental.ui.viewmodels.Field
import com.empresa.gestordocumental.ui.viewmodels.SubmitState
import com.empresa.gestordocumental.ui.viewmodels.UploadDocumentUiState
import com.empresa.gestordocumental.ui.viewmodels.UploadDocumentViewModel
import java.io.File
import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

private val DATE_FORMAT: DateTimeFormatter = DateTimeFormatter.ofPattern("dd/MM/yyyy")
private val SPANISH = Locale("es", "ES")

/**
 * Pantalla de alta de documento:
 *  1. Lanza el escáner ML Kit y muestra las páginas capturadas.
 *  2. Formulario: categoría, contacto, título, importe, IVA, fecha y notas.
 *  3. Sube la página seleccionada al backend (Retrofit multipart) o la encola
 *     si no hay conexión.
 */
@Composable
fun UploadDocumentScreen(
    onLogout: () -> Unit,
    viewModel: UploadDocumentViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val scanner = rememberDocumentScanner(onResult = viewModel::onScanResult)

    UploadDocumentContent(
        state = state,
        onScan = scanner::launch,
        onSelectPage = viewModel::selectPage,
        onClearScan = viewModel::clearScan,
        onCategorySelected = viewModel::onCategorySelected,
        onContactSelected = viewModel::onContactSelected,
        onTitleChanged = viewModel::onTitleChanged,
        onAmountChanged = viewModel::onAmountChanged,
        onTaxAmountChanged = viewModel::onTaxAmountChanged,
        onDateSelected = viewModel::onDateSelected,
        onNotesChanged = viewModel::onNotesChanged,
        onSubmit = viewModel::submit,
        onNewDocument = viewModel::startNewDocument,
        onRefreshCatalog = viewModel::refreshCatalog,
        onMessageShown = viewModel::messageShown,
        onLogout = onLogout,
    )
}

/** Contenido sin estado (facilita previews y tests de UI). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UploadDocumentContent(
    state: UploadDocumentUiState,
    onScan: () -> Unit,
    onSelectPage: (Int) -> Unit,
    onClearScan: () -> Unit,
    onCategorySelected: (Int) -> Unit,
    onContactSelected: (String?) -> Unit,
    onTitleChanged: (String) -> Unit,
    onAmountChanged: (String) -> Unit,
    onTaxAmountChanged: (String) -> Unit,
    onDateSelected: (LocalDate) -> Unit,
    onNotesChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    onNewDocument: () -> Unit,
    onRefreshCatalog: () -> Unit,
    onMessageShown: () -> Unit,
    onLogout: () -> Unit,
) {
    val snackbarHostState = remember { SnackbarHostState() }
    val scrollBehavior = TopAppBarDefaults.pinnedScrollBehavior()

    LaunchedEffect(state.userMessage) {
        state.userMessage?.let {
            snackbarHostState.showSnackbar(it)
            onMessageShown()
        }
    }

    Scaffold(
        modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
        topBar = {
            TopAppBar(
                title = { Text("Nuevo documento") },
                actions = {
                    IconButton(onClick = onRefreshCatalog, enabled = !state.isRefreshingCatalog) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Actualizar categorías y contactos")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = "Cerrar sesión")
                    }
                },
                scrollBehavior = scrollBehavior,
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            if (state.isRefreshingCatalog || state.submitState == SubmitState.Uploading) {
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            AnimatedContent(
                targetState = state.submitState is SubmitState.Success || state.submitState == SubmitState.Queued,
                transitionSpec = { fadeIn() togetherWith fadeOut() },
                label = "upload-content",
            ) { finished ->
                if (finished) {
                    UploadResultContent(state.submitState, onNewDocument)
                } else {
                    UploadForm(
                        state = state,
                        onScan = onScan,
                        onSelectPage = onSelectPage,
                        onClearScan = onClearScan,
                        onCategorySelected = onCategorySelected,
                        onContactSelected = onContactSelected,
                        onTitleChanged = onTitleChanged,
                        onAmountChanged = onAmountChanged,
                        onTaxAmountChanged = onTaxAmountChanged,
                        onDateSelected = onDateSelected,
                        onNotesChanged = onNotesChanged,
                        onSubmit = onSubmit,
                    )
                }
            }
        }
    }
}

// --------------------------------------------------------------------------- //
// Formulario
// --------------------------------------------------------------------------- //
@Composable
private fun UploadForm(
    state: UploadDocumentUiState,
    onScan: () -> Unit,
    onSelectPage: (Int) -> Unit,
    onClearScan: () -> Unit,
    onCategorySelected: (Int) -> Unit,
    onContactSelected: (String?) -> Unit,
    onTitleChanged: (String) -> Unit,
    onAmountChanged: (String) -> Unit,
    onTaxAmountChanged: (String) -> Unit,
    onDateSelected: (LocalDate) -> Unit,
    onNotesChanged: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val enabled = !state.isBusy
    var showDatePicker by rememberSaveable { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        ScanSection(
            pages = state.pages,
            selectedIndex = state.selectedPageIndex,
            isPreparing = state.isPreparingScan,
            enabled = enabled,
            errorText = state.fieldErrors[Field.IMAGE],
            onScan = onScan,
            onSelectPage = onSelectPage,
            onClear = onClearScan,
        )

        Text(
            "Datos del documento",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(top = 4.dp),
        )

        CategoryField(
            categories = state.categories,
            selected = state.selectedCategory,
            enabled = enabled,
            errorText = state.fieldErrors[Field.CATEGORY],
            onSelected = onCategorySelected,
        )

        ContactField(
            contacts = state.contacts,
            selected = state.selectedContact,
            enabled = enabled,
            errorText = state.fieldErrors[Field.CONTACT],
            onSelected = onContactSelected,
        )

        OutlinedTextField(
            value = state.title,
            onValueChange = onTitleChanged,
            label = { Text("Título *") },
            placeholder = { Text("p. ej. Factura Repsol octubre") },
            enabled = enabled,
            singleLine = true,
            isError = state.fieldErrors[Field.TITLE] != null,
            supportingText = state.fieldErrors[Field.TITLE]?.let { { Text(it) } },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences, imeAction = ImeAction.Next),
            modifier = Modifier.fillMaxWidth(),
        )

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            MoneyField(
                value = state.amount,
                onValueChange = onAmountChanged,
                label = "Importe total *",
                enabled = enabled,
                errorText = state.fieldErrors[Field.AMOUNT],
                modifier = Modifier.weight(1f),
            )
            MoneyField(
                value = state.taxAmount,
                onValueChange = onTaxAmountChanged,
                label = "IVA",
                enabled = enabled,
                errorText = state.fieldErrors[Field.TAX],
                modifier = Modifier.weight(1f),
            )
        }

        DateField(
            date = state.date,
            enabled = enabled,
            errorText = state.fieldErrors[Field.DATE],
            onClick = { showDatePicker = true },
        )

        OutlinedTextField(
            value = state.notes,
            onValueChange = onNotesChanged,
            label = { Text("Notas") },
            enabled = enabled,
            minLines = 2,
            maxLines = 5,
            isError = state.fieldErrors[Field.NOTES] != null,
            supportingText = state.fieldErrors[Field.NOTES]?.let { { Text(it) } },
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            modifier = Modifier.fillMaxWidth(),
        )

        LoadingButton(
            text = "Subir documento",
            loadingText = "Subiendo…",
            loading = state.submitState == SubmitState.Uploading,
            enabled = state.canSubmit,
            onClick = onSubmit,
            icon = { Icon(Icons.Filled.CloudUpload, contentDescription = null) },
            modifier = Modifier.padding(top = 4.dp),
        )
        if (state.pages.isEmpty()) {
            Text(
                "Escanea un documento para poder subirlo.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
            )
        }
        Spacer(Modifier.height(24.dp))
    }

    if (showDatePicker) {
        DocumentDatePickerDialog(
            initialDate = state.date,
            onDismiss = { showDatePicker = false },
            onConfirm = {
                onDateSelected(it)
                showDatePicker = false
            },
        )
    }
}

// --------------------------------------------------------------------------- //
// Sección de escaneo
// --------------------------------------------------------------------------- //
@Composable
private fun ScanSection(
    pages: List<File>,
    selectedIndex: Int,
    isPreparing: Boolean,
    enabled: Boolean,
    errorText: String?,
    onScan: () -> Unit,
    onSelectPage: (Int) -> Unit,
    onClear: () -> Unit,
) {
    ElevatedCard(Modifier.fillMaxWidth()) {
        when {
            isPreparing -> Box(
                Modifier.fillMaxWidth().height(220.dp),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator()
                    Spacer(Modifier.height(12.dp))
                    Text("Preparando imágenes…", style = MaterialTheme.typography.bodyMedium)
                }
            }

            pages.isEmpty() -> Column(
                Modifier
                    .fillMaxWidth()
                    .clickable(enabled = enabled, onClick = onScan)
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Icon(
                    Icons.Filled.DocumentScanner,
                    contentDescription = null,
                    modifier = Modifier.size(56.dp),
                    tint = if (errorText != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                )
                Spacer(Modifier.height(12.dp))
                Text("Escanea una factura o ticket", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Recorte automático, corrección de perspectiva e importación desde galería.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 4.dp),
                )
                Spacer(Modifier.height(16.dp))
                FilledTonalButton(onClick = onScan, enabled = enabled) {
                    Icon(Icons.Filled.DocumentScanner, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Escanear documento")
                }
                errorText?.let {
                    Text(
                        it,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }

            else -> Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                val selected = pages.getOrNull(selectedIndex)
                AsyncImage(
                    model = selected,
                    contentDescription = "Página ${selectedIndex + 1} escaneada",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(3f / 4f)
                        .clip(RoundedCornerShape(12.dp)),
                )
                if (pages.size > 1) {
                    Text(
                        "Selecciona la página que se adjuntará (${pages.size} escaneadas)",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(horizontal = 2.dp),
                    ) {
                        itemsIndexed(pages, key = { _, file -> file.absolutePath }) { index, file ->
                            PageThumbnail(
                                file = file,
                                index = index,
                                selected = index == selectedIndex,
                                onClick = { onSelectPage(index) },
                            )
                        }
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onScan, enabled = enabled, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Filled.DocumentScanner, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("Volver a escanear")
                    }
                    OutlinedButton(onClick = onClear, enabled = enabled) {
                        Icon(Icons.Outlined.Delete, contentDescription = "Descartar escaneo")
                    }
                }
            }
        }
    }
}

@Composable
private fun PageThumbnail(file: File, index: Int, selected: Boolean, onClick: () -> Unit) {
    val borderColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant
    AsyncImage(
        model = file,
        contentDescription = "Página ${index + 1}" + if (selected) " (seleccionada)" else "",
        contentScale = ContentScale.Crop,
        modifier = Modifier
            .size(width = 60.dp, height = 80.dp)
            .clip(RoundedCornerShape(8.dp))
            .border(BorderStroke(if (selected) 3.dp else 1.dp, borderColor), RoundedCornerShape(8.dp))
            .clickable(onClick = onClick),
    )
}

// --------------------------------------------------------------------------- //
// Campos
// --------------------------------------------------------------------------- //
@Composable
private fun CategoryField(
    categories: List<Category>,
    selected: Category?,
    enabled: Boolean,
    errorText: String?,
    onSelected: (Int) -> Unit,
) {
    val options = remember(categories) {
        categories.map { DropdownOption(it.id, it.name, color = parseHexColor(it.colorHex)) }
    }
    DropdownField(
        label = "Categoría *",
        options = options,
        selected = options.firstOrNull { it.value == selected?.id },
        onSelected = onSelected,
        enabled = enabled,
        errorText = errorText,
        placeholder = if (categories.isEmpty()) "Cargando categorías…" else "Seleccionar",
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun ContactField(
    contacts: List<Contact>,
    selected: Contact?,
    enabled: Boolean,
    errorText: String?,
    onSelected: (String?) -> Unit,
) {
    val options = remember(contacts) {
        listOf(DropdownOption<String?>(null, "Sin contacto")) + contacts.map { contact ->
            val subtitle = listOfNotNull(contact.type?.label, contact.taxId).joinToString(" · ").ifBlank { null }
            DropdownOption<String?>(contact.id, contact.name, supportingText = subtitle)
        }
    }
    DropdownField(
        label = "Contacto (proveedor / cliente)",
        options = options,
        selected = options.firstOrNull { it.value == selected?.id } ?: options.first(),
        onSelected = onSelected,
        enabled = enabled,
        errorText = errorText,
        leadingIcon = { Icon(Icons.Filled.Person, contentDescription = null) },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun MoneyField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    enabled: Boolean,
    errorText: String?,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = { Text("0,00") },
        enabled = enabled,
        singleLine = true,
        trailingIcon = { Icon(Icons.Filled.Euro, contentDescription = null) },
        isError = errorText != null,
        supportingText = errorText?.let { { Text(it) } },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Next),
        modifier = modifier,
    )
}

@Composable
private fun DateField(date: LocalDate, enabled: Boolean, errorText: String?, onClick: () -> Unit) {
    // Campo de solo lectura: un toque abre el selector de fecha.
    val interactionSource = remember { MutableInteractionSource() }
    LaunchedEffect(interactionSource, enabled) {
        interactionSource.interactions.collect { interaction ->
            if (enabled && interaction is PressInteraction.Release) onClick()
        }
    }
    OutlinedTextField(
        value = date.format(DATE_FORMAT),
        onValueChange = {},
        readOnly = true,
        enabled = enabled,
        label = { Text("Fecha del documento *") },
        trailingIcon = {
            IconButton(onClick = onClick, enabled = enabled) {
                Icon(Icons.Filled.CalendarMonth, contentDescription = "Elegir fecha")
            }
        },
        isError = errorText != null,
        supportingText = errorText?.let { { Text(it) } },
        interactionSource = interactionSource,
        modifier = Modifier
            .fillMaxWidth()
            .semantics { contentDescription = "Fecha del documento ${date.format(DATE_FORMAT)}" },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DocumentDatePickerDialog(
    initialDate: LocalDate,
    onDismiss: () -> Unit,
    onConfirm: (LocalDate) -> Unit,
) {
    val todayLimit = remember {
        LocalDate.now().plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()
    }
    val pickerState = rememberDatePickerState(
        initialSelectedDateMillis = initialDate.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli(),
        selectableDates = object : SelectableDates {
            override fun isSelectableDate(utcTimeMillis: Long): Boolean = utcTimeMillis < todayLimit
        },
    )
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(
                onClick = {
                    pickerState.selectedDateMillis?.let { millis ->
                        onConfirm(Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate())
                    } ?: onDismiss()
                },
            ) { Text("Aceptar") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancelar") } },
    ) {
        DatePicker(state = pickerState)
    }
}

// --------------------------------------------------------------------------- //
// Resultado
// --------------------------------------------------------------------------- //
@Composable
private fun UploadResultContent(submitState: SubmitState, onNewDocument: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        val queued = submitState == SubmitState.Queued
        Icon(
            imageVector = if (queued) Icons.Filled.CloudOff else Icons.Filled.CheckCircle,
            contentDescription = null,
            tint = if (queued) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(72.dp),
        )
        Spacer(Modifier.height(16.dp))
        Text(
            if (queued) "Guardado sin conexión" else "Documento subido",
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            if (queued) {
                "El documento se subirá automáticamente en cuanto haya conexión."
            } else {
                "El documento se ha procesado y guardado correctamente."
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        if (submitState is SubmitState.Success) {
            Spacer(Modifier.height(16.dp))
            UploadedSummaryCard(submitState.document)
        }
        Spacer(Modifier.height(24.dp))
        LoadingButton(
            text = "Escanear otro documento",
            loading = false,
            onClick = onNewDocument,
            icon = { Icon(Icons.Filled.DocumentScanner, contentDescription = null) },
        )
    }
}

@Composable
private fun UploadedSummaryCard(document: UploadedDocument) {
    val currency = remember { NumberFormat.getCurrencyInstance(SPANISH) }
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(document.title, style = MaterialTheme.typography.titleMedium)
            document.categoryName?.let {
                Text(it, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(currency.format(document.amount), style = MaterialTheme.typography.titleLarge)
                Text(document.status, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.tertiary)
            }
        }
    }
}

// --------------------------------------------------------------------------- //
// Previews
// --------------------------------------------------------------------------- //
private val previewState = UploadDocumentUiState(
    categories = listOf(
        Category(1, "Factura Proveedor", "#1E88E5"),
        Category(4, "Ticket Gasolina", "#E53935"),
    ),
    contacts = listOf(Contact("c1", "Repsol S.A.", ContactType.PROVEEDOR, "A12345678")),
    categoryId = 4,
    title = "Repostaje octubre",
    amount = "60.50",
    taxAmount = "10.50",
)

@Preview(name = "Claro", showBackground = true)
@Preview(name = "Oscuro", showBackground = true, uiMode = android.content.res.Configuration.UI_MODE_NIGHT_YES)
@Composable
private fun UploadDocumentPreview() {
    GestorTheme {
        UploadDocumentContent(
            state = previewState,
            onScan = {}, onSelectPage = {}, onClearScan = {}, onCategorySelected = {},
            onContactSelected = {}, onTitleChanged = {}, onAmountChanged = {}, onTaxAmountChanged = {},
            onDateSelected = {}, onNotesChanged = {}, onSubmit = {}, onNewDocument = {},
            onRefreshCatalog = {}, onMessageShown = {}, onLogout = {},
        )
    }
}
