package com.empresa.gestordocumental.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
abstract class CatalogDao {

    @Query("SELECT * FROM categories ORDER BY name")
    abstract fun observeCategories(): Flow<List<CategoryEntity>>

    @Query("SELECT * FROM contacts ORDER BY name")
    abstract fun observeContacts(): Flow<List<ContactEntity>>

    @Upsert
    abstract suspend fun upsertCategories(items: List<CategoryEntity>)

    @Upsert
    abstract suspend fun upsertContacts(items: List<ContactEntity>)

    @Query("DELETE FROM categories WHERE id NOT IN (:keepIds)")
    abstract suspend fun deleteCategoriesNotIn(keepIds: List<Int>)

    @Query("DELETE FROM contacts WHERE id NOT IN (:keepIds)")
    abstract suspend fun deleteContactsNotIn(keepIds: List<String>)

    /** Sustituye la caché de categorías por la lista recibida del servidor. */
    @Transaction
    open suspend fun replaceCategories(items: List<CategoryEntity>) {
        upsertCategories(items)
        deleteCategoriesNotIn(items.map { it.id })
    }

    @Transaction
    open suspend fun replaceContacts(items: List<ContactEntity>) {
        upsertContacts(items)
        deleteContactsNotIn(items.map { it.id })
    }
}

@Dao
interface PendingUploadDao {

    @Insert
    suspend fun insert(item: PendingUploadEntity): Long

    @Query("SELECT * FROM pending_uploads WHERE localId = :id")
    suspend fun getById(id: Long): PendingUploadEntity?

    @Query("SELECT COUNT(*) FROM pending_uploads WHERE status = 'PENDING'")
    fun observePendingCount(): Flow<Int>

    @Query("UPDATE pending_uploads SET attempts = attempts + 1, lastError = :error, status = :status WHERE localId = :id")
    suspend fun markAttempt(id: Long, error: String?, status: PendingUploadStatus)

    @Query("DELETE FROM pending_uploads WHERE localId = :id")
    suspend fun delete(id: Long)
}
