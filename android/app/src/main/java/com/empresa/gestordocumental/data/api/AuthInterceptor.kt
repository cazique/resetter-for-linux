package com.empresa.gestordocumental.data.api

import com.empresa.gestordocumental.data.local.TokenStore
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import javax.inject.Inject
import javax.inject.Singleton

private const val AUTH_HEADER = "Authorization"
private const val BEARER = "Bearer "

/** Añade "Authorization: Bearer <access_token>" a todas las peticiones salvo login/refresh. */
@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenStore: TokenStore,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        if (request.header(AUTH_HEADER) != null || request.isPublicEndpoint()) {
            return chain.proceed(request)
        }
        val token = tokenStore.currentAccessToken()
        val authenticated = if (token.isNullOrBlank()) {
            request
        } else {
            request.newBuilder().header(AUTH_HEADER, BEARER + token).build()
        }
        return chain.proceed(authenticated)
    }
}

/**
 * Gestiona respuestas 401: intenta refrescar el access token con el refresh
 * token y reintenta la petición original una única vez. Si el refresh falla,
 * se cierra la sesión localmente (la UI vuelve a la pantalla de login).
 */
@Singleton
class TokenAuthenticator @Inject constructor(
    private val tokenStore: TokenStore,
    private val refreshApi: AuthRefreshApi,
) : Authenticator {

    private val lock = Any()

    override fun authenticate(route: Route?, response: Response): Request? {
        val request = response.request
        if (request.isPublicEndpoint() || response.priorResponseCount() >= 1) return null

        val failedToken = request.header(AUTH_HEADER)?.removePrefix(BEARER)

        synchronized(lock) {
            // Otro hilo pudo refrescar el token mientras esperábamos el lock.
            val current = tokenStore.currentAccessToken()
            if (!current.isNullOrBlank() && current != failedToken) {
                return request.withBearer(current)
            }

            val refreshToken = tokenStore.currentRefreshToken() ?: run {
                tokenStore.clearBlocking()
                return null
            }

            val newAccess = try {
                val refreshResponse = refreshApi.refresh(BEARER + refreshToken).execute()
                if (refreshResponse.isSuccessful) refreshResponse.body()?.data?.accessToken else null
            } catch (e: Exception) {
                null
            }

            if (newAccess.isNullOrBlank()) {
                tokenStore.clearBlocking()
                return null
            }
            tokenStore.updateAccessTokenBlocking(newAccess)
            return request.withBearer(newAccess)
        }
    }

    private fun Request.withBearer(token: String): Request =
        newBuilder().header(AUTH_HEADER, BEARER + token).build()

    private fun Response.priorResponseCount(): Int {
        var count = 0
        var prior = priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}

private fun Request.isPublicEndpoint(): Boolean {
    val path = url.encodedPath
    return path.endsWith("/auth/login") || path.endsWith("/auth/register") || path.endsWith("/auth/refresh")
}
