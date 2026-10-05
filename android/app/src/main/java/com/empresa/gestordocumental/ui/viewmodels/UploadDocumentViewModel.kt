package com.empresa.gestordocumental.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.empresa.gestordocumental.data.repository.CatalogRepository
import com.empresa.gestordocumental.data.repository.DocumentRepository
import com.empresa.gestordocumental.domain.model.Category
import com.empresa.gestordocumental.domain.model.Contact
import com.empresa.gestordocumental.domain.model.DocumentDraft
import com.empresa.gestordocumental.domain.model.UploadOutcome
import com.empresa.gestordocumental.domain.model.UploadedDocument
import com.empresa.gestordocumental.ui.scanner.ScanResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File
import java.math.BigDecimal
import java.time.LocalDate
import javax.inject.Inject

/** Estado del envío del formulario. */
sealed interface SubmitState {
    data object Idle : SubmitState
    data object Uploading : SubmitState
    data class Success(val document: UploadedDocument) : SubmitState
    data object Queued : SubmitState
}

/** Nombres de campo alineados con los del backend para reutilizar sus errores. */
object Field {
    const val IMAGE = "image"
    const val CATEGORY = "category_id"
    const val CONTACT = "contact_id"
    const val TITLE = "title"
    const val AMOUNT = "amount"
    const val TAX = "tax_amount"
    const val DATE = "date"
    const val NOTES = "notes"
}

data class UploadDocumentUiState(
    val pages: List<File> = emptyList(),
    val selectedPageIndex: Int = 0,
    val isPreparingScan: Boolean = false,
    val categories: List<Category> = emptyList(),
    val contacts: List<Contact> = emptyList(),
    val isRefreshingCatalog: Boolean = false,
    val categoryId: Int? = null,
    val contactId: String? = null,
    val title: String = "",
    val amount: String = "",
    val taxAmount: String = "",
    val date: LocalDate = LocalDate.now(),
    val notes: String = "",
    val fieldErrors: Map<String, String> = emptyMap(),
    val submitState: SubmitState = SubmitState.Idle,
    /** Mensaje puntual para Snackbar (se consume con [UploadDocumentViewModel.messageShown]). */
    val userMessage: String? = null,
) {
    val selectedPage: File? get() = pages.getOrNull(selectedPageIndex)
    val selectedCategory: Category? get() = categories.firstOrNull { it.id == categoryId }
    val selectedContact: Contact? get() = contacts.firstOrNull { it.id == contactId }
    val isBusy: Boolean get() = isPreparingScan || submitState == SubmitState.Uploading
    val canSubmit: Boolean get() = pages.isNotEmpty() && !isBusy
}

@HiltViewModel
class UploadDocumentViewModel @Inject constructor(
    private val documentRepository: DocumentRepository,
    private val catalogRepository: CatalogRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(UploadDocumentUiState())
    val uiState: StateFlow<UploadDocumentUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            catalogRepository.categories.collect { categories ->
                _uiState.update { state ->
                    val stillValid = categories.any { it.id == state.categoryId }
                    state.copy(categories = categories, categoryId = state.categoryId.takeIf { stillValid })
                }
            }
        }
        viewModelScope.launch {
            catalogRepository.contacts.collect { contacts ->
                _uiState.update { state ->
                    val stillValid = contacts.any { it.id == state.contactId }
                    state.copy(contacts = contacts, contactId = state.contactId.takeIf { stillValid })
                }
            }
        }
        refreshCatalog()
    }

    fun refreshCatalog() {
        if (_uiState.value.isRefreshingCatalog) return
        viewModelScope.launch {
            _uiState.update { it.copy(isRefreshingCatalog = true) }
            val error = catalogRepository.refresh()
            _uiState.update {
                it.copy(
                    isRefreshingCatalog = false,
                    userMessage = error?.let { msg -> "No se pudieron actualizar categorías y contactos: $msg" }
                        ?: it.userMessage,
                )
            }
        }
    }

    // ------------------------------------------------------------------ //
    // Escáner
    // ------------------------------------------------------------------ //
    fun onScanResult(result: ScanResult) {
        when (result) {
            is ScanResult.Success -> importScannedPages(result)
            ScanResult.Cancelled -> Unit
            is ScanResult.Error -> _uiState.update { it.copy(userMessage = result.message) }
        }
    }

    private fun importScannedPages(result: ScanResult.Success) {
        viewModelScope.launch {
            _uiState.update { it.copy(isPreparingScan = true) }
            try {
                val files = result.pages.map { documentRepository.persistScannedPage(it) }
                val previous = _uiState.value.pages
                documentRepository.discardScans(previous)
                _uiState.update {
                    it.copy(
                        pages = files,
                        selectedPageIndex = 0,
                        isPreparingScan = false,
                        fieldErrors = it.fieldErrors - Field.IMAGE,
                        submitState = SubmitState.Idle,
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(isPreparingScan = false, userMessage = e.message ?: "No se pudo importar el escaneo.")
                }
            }
        }
    }

    fun selectPage(index: Int) = _uiState.update {
        if (index in it.pages.indices) it.copy(selectedPageIndex = index) else it
    }

    fun clearScan() {
        val pages = _uiState.value.pages
        _uiState.update { it.copy(pages = emptyList(), selectedPageIndex = 0) }
        viewModelScope.launch { documentRepository.discardScans(pages) }
    }

    // ------------------------------------------------------------------ //
    // Formulario
    // ------------------------------------------------------------------ //
    fun onCategorySelected(id: Int) = _uiState.update {
        it.copy(categoryId = id, fieldErrors = it.fieldErrors - Field.CATEGORY)
    }

    fun onContactSelected(id: String?) = _uiState.update {
        it.copy(contactId = id, fieldErrors = it.fieldErrors - Field.CONTACT)
    }

    fun onTitleChanged(value: String) = _uiState.update {
        it.copy(title = value.take(MAX_TITLE), fieldErrors = it.fieldErrors - Field.TITLE)
    }

    fun onAmountChanged(value: String) = _uiState.update {
        it.copy(amount = sanitizeDecimalInput(value), fieldErrors = it.fieldErrors - Field.AMOUNT)
    }

    fun onTaxAmountChanged(value: String) = _uiState.update {
        it.copy(taxAmount = sanitizeDecimalInput(value), fieldErrors = it.fieldErrors - Field.TAX)
    }

    fun onDateSelected(date: LocalDate) = _uiState.update {
        it.copy(date = date, fieldErrors = it.fieldErrors - Field.DATE)
    }

    fun onNotesChanged(value: String) = _uiState.update {
        it.copy(notes = value.take(MAX_NOTES), fieldErrors = it.fieldErrors - Field.NOTES)
    }

    fun messageShown() = _uiState.update { it.copy(userMessage = null) }

    // ------------------------------------------------------------------ //
    // Envío
    // ------------------------------------------------------------------ //
    fun submit() {
        val state = _uiState.value
        if (state.isBusy) return

        val (draft, errors) = validate(state)
        if (draft == null) {
            _uiState.update { it.copy(fieldErrors = errors, userMessage = "Revisa los campos marcados.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(submitState = SubmitState.Uploading, fieldErrors = emptyMap()) }
            when (val outcome = documentRepository.upload(draft)) {
                is UploadOutcome.Uploaded -> finishWith(SubmitState.Success(outcome.document), draft.imageFile)
                is UploadOutcome.Queued -> finishWith(SubmitState.Queued, draft.imageFile)
                is UploadOutcome.Rejected -> _uiState.update {
                    it.copy(
                        submitState = SubmitState.Idle,
                        fieldErrors = outcome.fieldErrors,
                        userMessage = outcome.message,
                    )
                }
            }
        }
    }

    /** Tras subir/encolar, descarta las páginas no seleccionadas. */
    private suspend fun finishWith(result: SubmitState, uploadedFile: File) {
        val leftovers = _uiState.value.pages.filter { it != uploadedFile }
        documentRepository.discardScans(leftovers)
        _uiState.update { it.copy(submitState = result, pages = emptyList(), selectedPageIndex = 0) }
    }

    /** Limpia el formulario para escanear un documento nuevo (conserva el catálogo). */
    fun startNewDocument() = _uiState.update {
        UploadDocumentUiState(categories = it.categories, contacts = it.contacts)
    }

    private fun validate(state: UploadDocumentUiState): Pair<DocumentDraft?, Map<String, String>> {
        val errors = mutableMapOf<String, String>()
        val image = state.selectedPage
        if (image == null || !image.exists()) errors[Field.IMAGE] = "Escanea un documento antes de subirlo."
        if (state.categoryId == null) errors[Field.CATEGORY] = "Selecciona una categoría."
        if (state.title.isBlank()) errors[Field.TITLE] = "El título es obligatorio."

        val amount = state.amount.toBigDecimalOrNull()
        when {
            state.amount.isBlank() -> errors[Field.AMOUNT] = "El importe es obligatorio."
            amount == null -> errors[Field.AMOUNT] = "Importe no válido."
            amount < BigDecimal.ZERO -> errors[Field.AMOUNT] = "El importe no puede ser negativo."
            amount.scale() > 2 -> errors[Field.AMOUNT] = "Máximo dos decimales."
        }
        val tax = if (state.taxAmount.isBlank()) BigDecimal.ZERO else state.taxAmount.toBigDecimalOrNull()
        when {
            tax == null -> errors[Field.TAX] = "IVA no válido."
            tax < BigDecimal.ZERO -> errors[Field.TAX] = "El IVA no puede ser negativo."
            tax.scale() > 2 -> errors[Field.TAX] = "Máximo dos decimales."
            amount != null && tax > amount -> errors[Field.TAX] = "El IVA no puede superar el importe."
        }
        if (state.date.isAfter(LocalDate.now().plusDays(1))) errors[Field.DATE] = "La fecha no puede ser futura."

        if (errors.isNotEmpty() || image == null || amount == null || tax == null || state.categoryId == null) {
            return null to errors
        }
        return DocumentDraft(
            imageFile = image,
            categoryId = state.categoryId,
            contactId = state.contactId,
            title = state.title.trim(),
            amount = amount,
            taxAmount = tax,
            date = state.date,
            notes = state.notes.trim().ifBlank { null },
        ) to emptyMap()
    }

    override fun onCleared() {
        // Borra copias locales no enviadas (ficheros pequeños, operación rápida).
        _uiState.value.pages.forEach { documentRepository.deleteLocalFileSync(it) }
        super.onCleared()
    }

    private companion object {
        const val MAX_TITLE = 200
        const val MAX_NOTES = 5000

        /** Acepta coma o punto decimal y descarta cualquier otro carácter. */
        fun sanitizeDecimalInput(raw: String): String {
            val normalized = raw.replace(',', '.').filter { it.isDigit() || it == '.' }
            val firstDot = normalized.indexOf('.')
            return if (firstDot == -1) {
                normalized.take(10)
            } else {
                normalized.substring(0, firstDot).take(10) + "." +
                    normalized.substring(firstDot + 1).replace(".", "").take(2)
            }
        }
    }
}
