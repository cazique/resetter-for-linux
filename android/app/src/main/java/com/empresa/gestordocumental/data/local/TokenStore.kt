package com.empresa.gestordocumental.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

private val Context.sessionDataStore: DataStore<Preferences> by preferencesDataStore(name = "session")

/**
 * Persistencia de la sesión (tokens JWT y datos básicos del usuario) en DataStore.
 *
 * Mantiene una caché en memoria para que los interceptores de OkHttp (que se
 * ejecutan en hilos de red) no tengan que leer disco en cada petición.
 */
@Singleton
class TokenStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private object Keys {
        val ACCESS = stringPreferencesKey("access_token")
        val REFRESH = stringPreferencesKey("refresh_token")
        val USER_NAME = stringPreferencesKey("user_name")
        val USER_EMAIL = stringPreferencesKey("user_email")
    }

    private data class Cached(val access: String?, val refresh: String?)

    @Volatile
    private var cache: Cached? = null

    private val safeData: Flow<Preferences> = context.sessionDataStore.data
        .catch { e -> if (e is IOException) emit(emptyPreferences()) else throw e }

    val isLoggedIn: Flow<Boolean> = safeData.map { !it[Keys.ACCESS].isNullOrBlank() }

    val userDisplayName: Flow<String?> = safeData.map { it[Keys.USER_NAME] ?: it[Keys.USER_EMAIL] }

    suspend fun saveSession(accessToken: String, refreshToken: String?, fullName: String?, email: String?) {
        context.sessionDataStore.edit { prefs ->
            prefs[Keys.ACCESS] = accessToken
            if (refreshToken != null) prefs[Keys.REFRESH] = refreshToken
            if (fullName != null) prefs[Keys.USER_NAME] = fullName else prefs.remove(Keys.USER_NAME)
            if (email != null) prefs[Keys.USER_EMAIL] = email else prefs.remove(Keys.USER_EMAIL)
        }
        cache = Cached(accessToken, refreshToken ?: cache?.refresh)
    }

    suspend fun updateAccessToken(accessToken: String) {
        context.sessionDataStore.edit { it[Keys.ACCESS] = accessToken }
        cache = Cached(accessToken, cache?.refresh ?: loadFromDisk().refresh)
    }

    suspend fun clear() {
        context.sessionDataStore.edit { it.clear() }
        cache = Cached(null, null)
    }

    // ---- Accesos síncronos para OkHttp (llamados siempre fuera del hilo principal) ----

    fun currentAccessToken(): String? = ensureCache().access

    fun currentRefreshToken(): String? = ensureCache().refresh

    fun updateAccessTokenBlocking(accessToken: String) = runBlocking { updateAccessToken(accessToken) }

    fun clearBlocking() = runBlocking { clear() }

    private fun ensureCache(): Cached = cache ?: runBlocking { loadFromDisk() }.also { cache = it }

    private suspend fun loadFromDisk(): Cached {
        val prefs = safeData.first()
        return Cached(prefs[Keys.ACCESS], prefs[Keys.REFRESH])
    }
}
