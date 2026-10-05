package com.empresa.gestordocumental.data.repository

import com.empresa.gestordocumental.data.api.ApiService
import com.empresa.gestordocumental.data.api.toApiFailure
import com.empresa.gestordocumental.data.local.CatalogDao
import com.empresa.gestordocumental.data.local.CategoryEntity
import com.empresa.gestordocumental.data.local.ContactEntity
import com.empresa.gestordocumental.domain.model.Category
import com.empresa.gestordocumental.domain.model.Contact
import com.empresa.gestordocumental.domain.model.ContactType
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Categorías y contactos: la UI observa siempre Room (fuente única de verdad)
 * y [refresh] sincroniza la caché con el servidor cuando hay conexión.
 */
@Singleton
class CatalogRepository @Inject constructor(
    private val api: ApiService,
    private val dao: CatalogDao,
    private val json: Json,
) {
    val categories: Flow<List<Category>> = dao.observeCategories().map { list ->
        list.map { Category(it.id, it.name, it.colorHex) }
    }

    val contacts: Flow<List<Contact>> = dao.observeContacts().map { list ->
        list.map { Contact(it.id, it.name, ContactType.fromApi(it.type), it.taxId) }
    }

    /** Devuelve null si todo fue bien, o un mensaje de error (la caché se mantiene). */
    suspend fun refresh(): String? = try {
        val categories = api.getCategories().data.orEmpty()
        dao.replaceCategories(categories.filter { it.isActive }.map { CategoryEntity(it.id, it.name, it.colorHex) })

        val contacts = mutableListOf<ContactEntity>()
        var page = 1
        do {
            val response = api.getContacts(page = page, perPage = 100)
            contacts += response.data.orEmpty().map {
                ContactEntity(it.id, it.name, it.type, it.phone, it.email, it.taxId)
            }
            val totalPages = response.meta?.pages ?: 1
            page++
        } while (page <= totalPages && page <= MAX_CONTACT_PAGES)
        dao.replaceContacts(contacts)
        null
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        e.toApiFailure(json).message
    }

    private companion object {
        const val MAX_CONTACT_PAGES = 20
    }
}
