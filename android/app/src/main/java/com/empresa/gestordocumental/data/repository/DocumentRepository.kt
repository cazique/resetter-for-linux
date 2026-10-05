package com.empresa.gestordocumental.data.repository

import android.content.Context
import android.net.Uri
import com.empresa.gestordocumental.data.api.ApiFailure
import com.empresa.gestordocumental.data.api.ApiService
import com.empresa.gestordocumental.data.api.toApiFailure
import com.empresa.gestordocumental.data.local.PendingUploadDao
import com.empresa.gestordocumental.data.local.PendingUploadEntity
import com.empresa.gestordocumental.data.local.PendingUploadStatus
import com.empresa.gestordocumental.data.work.UploadDocumentWorker
import com.empresa.gestordocumental.domain.model.DocumentDraft
import com.empresa.gestordocumental.domain.model.UploadOutcome
import com.empresa.gestordocumental.domain.model.UploadedDocument
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.IOException
import java.math.BigDecimal
import java.math.RoundingMode
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/** Resultado del intento de subida desde el Worker. */
sealed interface PendingUploadResult {
    data object Done : PendingUploadResult
    data object RetryLater : PendingUploadResult
    data class PermanentFailure(val message: String) : PendingUploadResult
}

@Singleton
class DocumentRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val api: ApiService,
    private val pendingDao: PendingUploadDao,
    private val json: Json,
) {
    private val textPlain = "text/plain".toMediaType()
    private val imageJpeg = "image/jpeg".toMediaType()

    val pendingUploadsCount: Flow<Int> = pendingDao.observePendingCount()

    /**
     * Copia la página escaneada (caché temporal de ML Kit) al almacenamiento
     * interno de la app para que sobreviva a reinicios y a la cola offline.
     */
    suspend fun persistScannedPage(uri: Uri): File = withContext(Dispatchers.IO) {
        val dir = File(context.filesDir, SCANS_DIR).apply { mkdirs() }
        val target = File(dir, "scan_${System.currentTimeMillis()}_${UUID.randomUUID()}.jpg")
        val input = context.contentResolver.openInputStream(uri)
            ?: throw IOException("No se pudo leer la imagen escaneada.")
        input.use { source -> target.outputStream().use { sink -> source.copyTo(sink) } }
        if (target.length() == 0L) {
            target.delete()
            throw IOException("La imagen escaneada está vacía.")
        }
        target
    }

    /** Sube el documento; si no hay conexión lo encola para WorkManager. */
    suspend fun upload(draft: DocumentDraft): UploadOutcome {
        return try {
            val response = api.uploadDocument(imagePart(draft.imageFile), formFields(draft))
            val dto = response.data
                ?: return UploadOutcome.Rejected(response.message ?: "Respuesta vacía del servidor.", emptyMap())
            deleteLocalFile(draft.imageFile)
            UploadOutcome.Uploaded(
                UploadedDocument(
                    id = dto.id,
                    title = dto.title.orEmpty(),
                    amount = dto.amount,
                    status = dto.status,
                    categoryName = dto.category?.name,
                ),
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            when (val failure = e.toApiFailure(json)) {
                is ApiFailure.Network -> UploadOutcome.Queued(enqueue(draft))
                is ApiFailure.Http -> UploadOutcome.Rejected(failure.message, failure.fieldErrors)
                is ApiFailure.Unexpected -> UploadOutcome.Rejected(failure.message, emptyMap())
            }
        }
    }

    /** Invocado por [UploadDocumentWorker] para procesar un elemento de la cola. */
    suspend fun uploadPending(localId: Long): PendingUploadResult {
        val pending = pendingDao.getById(localId) ?: return PendingUploadResult.Done
        val file = File(pending.filePath)
        if (!file.exists()) {
            pendingDao.markAttempt(localId, "La imagen local ya no existe.", PendingUploadStatus.FAILED)
            return PendingUploadResult.PermanentFailure("La imagen local ya no existe.")
        }
        val draft = DocumentDraft(
            imageFile = file,
            categoryId = pending.categoryId,
            contactId = pending.contactId,
            title = pending.title,
            amount = BigDecimal(pending.amount),
            taxAmount = BigDecimal(pending.taxAmount),
            date = LocalDate.parse(pending.date, DateTimeFormatter.ISO_LOCAL_DATE),
            notes = pending.notes,
        )
        return try {
            api.uploadDocument(imagePart(file), formFields(draft))
            pendingDao.delete(localId)
            deleteLocalFile(file)
            PendingUploadResult.Done
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            when (val failure = e.toApiFailure(json)) {
                is ApiFailure.Network -> {
                    pendingDao.markAttempt(localId, failure.message, PendingUploadStatus.PENDING)
                    PendingUploadResult.RetryLater
                }
                is ApiFailure.Http -> if (failure.code == 401 || failure.code >= 500) {
                    // Sesión caducada o error temporal del servidor: se reintenta más tarde.
                    pendingDao.markAttempt(localId, failure.message, PendingUploadStatus.PENDING)
                    PendingUploadResult.RetryLater
                } else {
                    pendingDao.markAttempt(localId, failure.message, PendingUploadStatus.FAILED)
                    PendingUploadResult.PermanentFailure(failure.message)
                }
                is ApiFailure.Unexpected -> {
                    pendingDao.markAttempt(localId, failure.message, PendingUploadStatus.FAILED)
                    PendingUploadResult.PermanentFailure(failure.message)
                }
            }
        }
    }

    private suspend fun enqueue(draft: DocumentDraft): Long {
        val id = pendingDao.insert(
            PendingUploadEntity(
                filePath = draft.imageFile.absolutePath,
                categoryId = draft.categoryId,
                contactId = draft.contactId,
                title = draft.title,
                amount = draft.amount.toPlainString(),
                taxAmount = draft.taxAmount.toPlainString(),
                date = draft.date.format(DateTimeFormatter.ISO_LOCAL_DATE),
                notes = draft.notes,
            ),
        )
        UploadDocumentWorker.enqueue(context, id)
        return id
    }

    /** Elimina copias locales de páginas escaneadas que no se van a subir. */
    suspend fun discardScans(files: Collection<File>) = withContext(Dispatchers.IO) {
        files.forEach { deleteLocalFileSync(it) }
    }

    private fun imagePart(file: File): MultipartBody.Part =
        MultipartBody.Part.createFormData("image", file.name, file.asRequestBody(imageJpeg))

    private fun formFields(draft: DocumentDraft): Map<String, RequestBody> = buildMap {
        put("category_id", draft.categoryId.toString().toRequestBody(textPlain))
        put("title", draft.title.toRequestBody(textPlain))
        put("amount", draft.amount.setScale(2, RoundingMode.HALF_UP).toPlainString().toRequestBody(textPlain))
        put("tax_amount", draft.taxAmount.setScale(2, RoundingMode.HALF_UP).toPlainString().toRequestBody(textPlain))
        put("date", draft.date.format(DateTimeFormatter.ISO_LOCAL_DATE).toRequestBody(textPlain))
        draft.contactId?.let { put("contact_id", it.toRequestBody(textPlain)) }
        draft.notes?.takeIf { it.isNotBlank() }?.let { put("notes", it.toRequestBody(textPlain)) }
    }

    private suspend fun deleteLocalFile(file: File) = withContext(Dispatchers.IO) { deleteLocalFileSync(file) }

    /** Solo borra ficheros dentro del directorio interno de escaneos. */
    fun deleteLocalFileSync(file: File) {
        if (file.parentFile?.name == SCANS_DIR) file.delete()
    }

    private companion object {
        const val SCANS_DIR = "scans"
    }
}
