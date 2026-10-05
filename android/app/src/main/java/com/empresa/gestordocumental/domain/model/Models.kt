package com.empresa.gestordocumental.domain.model

import java.io.File
import java.math.BigDecimal
import java.time.LocalDate

data class Category(val id: Int, val name: String, val colorHex: String?)

enum class ContactType(val apiValue: String, val label: String) {
    PROVEEDOR("Proveedor", "Proveedor"),
    CLIENTE("Cliente", "Cliente"),
    TRABAJADOR("Trabajador", "Trabajador");

    companion object {
        fun fromApi(value: String): ContactType? = entries.firstOrNull { it.apiValue == value }
    }
}

data class Contact(val id: String, val name: String, val type: ContactType?, val taxId: String?)

/** Datos de un documento listo para enviarse al backend. */
data class DocumentDraft(
    val imageFile: File,
    val categoryId: Int,
    val contactId: String?,
    val title: String,
    val amount: BigDecimal,
    val taxAmount: BigDecimal,
    val date: LocalDate,
    val notes: String?,
)

data class UploadedDocument(
    val id: String,
    val title: String,
    val amount: Double,
    val status: String,
    val categoryName: String?,
)

/** Resultado de intentar subir un documento. */
sealed interface UploadOutcome {
    data class Uploaded(val document: UploadedDocument) : UploadOutcome

    /** Sin conexión: guardado en cola local, se subirá automáticamente. */
    data class Queued(val localId: Long) : UploadOutcome

    data class Rejected(val message: String, val fieldErrors: Map<String, String>) : UploadOutcome
}
