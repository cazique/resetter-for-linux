package com.empresa.gestordocumental.data.work

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.empresa.gestordocumental.data.repository.DocumentRepository
import com.empresa.gestordocumental.data.repository.PendingUploadResult
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

/** Sube en segundo plano un documento encolado cuando vuelve la conexión. */
@HiltWorker
class UploadDocumentWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val repository: DocumentRepository,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val localId = inputData.getLong(KEY_LOCAL_ID, -1L)
        if (localId <= 0L) return Result.failure()
        if (runAttemptCount >= MAX_ATTEMPTS) {
            Log.w(TAG, "Subida $localId abandonada tras $runAttemptCount intentos")
            return Result.failure()
        }
        return when (val result = repository.uploadPending(localId)) {
            PendingUploadResult.Done -> Result.success()
            PendingUploadResult.RetryLater -> Result.retry()
            is PendingUploadResult.PermanentFailure -> {
                Log.w(TAG, "Subida $localId rechazada: ${result.message}")
                Result.failure(workDataOf(KEY_ERROR to result.message))
            }
        }
    }

    companion object {
        private const val TAG = "UploadDocumentWorker"
        private const val KEY_LOCAL_ID = "local_id"
        const val KEY_ERROR = "error"
        private const val MAX_ATTEMPTS = 10

        fun enqueue(context: Context, localId: Long) {
            val request = OneTimeWorkRequestBuilder<UploadDocumentWorker>()
                .setInputData(workDataOf(KEY_LOCAL_ID to localId))
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .addTag("document_upload")
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork("upload_document_$localId", ExistingWorkPolicy.KEEP, request)
        }
    }
}
