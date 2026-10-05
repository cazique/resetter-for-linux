package com.empresa.gestordocumental.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [CategoryEntity::class, ContactEntity::class, PendingUploadEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun catalogDao(): CatalogDao
    abstract fun pendingUploadDao(): PendingUploadDao

    companion object {
        const val NAME = "gestor_documental.db"
    }
}
