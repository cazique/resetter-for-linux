package com.empresa.gestordocumental.data.repository

import com.empresa.gestordocumental.data.api.ApiService
import com.empresa.gestordocumental.data.api.LoginRequestDto
import com.empresa.gestordocumental.data.api.toApiFailure
import com.empresa.gestordocumental.data.local.TokenStore
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val tokenStore: TokenStore,
    private val json: Json,
) {
    val isLoggedIn: Flow<Boolean> = tokenStore.isLoggedIn
    val userDisplayName: Flow<String?> = tokenStore.userDisplayName

    /** Devuelve null si el login fue correcto o el mensaje de error en caso contrario. */
    suspend fun login(email: String, password: String): String? = try {
        val response = api.login(LoginRequestDto(email.trim(), password))
        val auth = response.data ?: return response.message ?: "Respuesta vacía del servidor."
        tokenStore.saveSession(auth.accessToken, auth.refreshToken, auth.user?.fullName, auth.user?.email)
        null
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        e.toApiFailure(json).message
    }

    suspend fun logout() = tokenStore.clear()
}
