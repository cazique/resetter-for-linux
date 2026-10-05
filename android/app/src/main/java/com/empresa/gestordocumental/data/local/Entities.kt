package com.empresa.gestordocumental.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/** Caché local de categorías (para el formulario sin conexión). */
@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey val id: Int,
    val name: String,
    val colorHex: String?,
)

/** Caché local de contactos. */
@Entity(tableName = "contacts", indices = [Index("name"), Index("type")])
data class ContactEntity(
    @PrimaryKey val id: String,
    val name: String,
    val type: String,
    val phone: String?,
    val email: String?,
    val taxId: String?,
)

/** Estado de una subida diferida. */
enum class PendingUploadStatus { PENDING, FAILED }

/**
 * Documento escaneado pendiente de subir (cola offline gestionada por WorkManager).
 * Los importes se guardan como texto para no perder precisión decimal.
 */
@Entity(tableName = "pending_uploads")
data class PendingUploadEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val filePath: String,
    val categoryId: Int,
    val contactId: String?,
    val title: String,
    val amount: String,
    val taxAmount: String,
    val date: String,
    val notes: String?,
    val status: PendingUploadStatus = PendingUploadStatus.PENDING,
    val attempts: Int = 0,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
)
