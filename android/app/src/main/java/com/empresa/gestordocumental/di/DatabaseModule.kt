package com.empresa.gestordocumental.di

import android.content.Context
import androidx.room.Room
import com.empresa.gestordocumental.data.local.AppDatabase
import com.empresa.gestordocumental.data.local.CatalogDao
import com.empresa.gestordocumental.data.local.PendingUploadDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, AppDatabase.NAME).build()

    @Provides
    fun provideCatalogDao(db: AppDatabase): CatalogDao = db.catalogDao()

    @Provides
    fun providePendingUploadDao(db: AppDatabase): PendingUploadDao = db.pendingUploadDao()
}
