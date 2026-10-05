package com.empresa.gestordocumental.data.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.PartMap
import retrofit2.http.Query

/** Endpoints autenticados de la API REST (/api/v1). */
interface ApiService {

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequestDto): ApiEnvelope<AuthResponseDto>

    @GET("auth/me")
    suspend fun me(): ApiEnvelope<UserDto>

    @GET("categories")
    suspend fun getCategories(): ApiEnvelope<List<CategoryDto>>

    @GET("contacts")
    suspend fun getContacts(
        @Query("search") search: String? = null,
        @Query("type") type: String? = null,
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 100,
    ): ApiEnvelope<List<ContactDto>>

    /**
     * Alta de documento (multipart/form-data).
     * @param image parte "image" con el JPEG escaneado.
     * @param fields resto de campos de formulario (category_id, title, amount...).
     */
    @Multipart
    @POST("documents")
    suspend fun uploadDocument(
        @Part image: MultipartBody.Part,
        @PartMap fields: Map<String, @JvmSuppressWildcards RequestBody>,
    ): ApiEnvelope<DocumentDto>
}

/**
 * API usada exclusivamente por [TokenAuthenticator] para refrescar el token.
 * Es síncrona (Call) porque el Authenticator de OkHttp se ejecuta en un hilo
 * de red y debe devolver la petición reintentada de forma bloqueante.
 */
interface AuthRefreshApi {
    @POST("auth/refresh")
    fun refresh(@Header("Authorization") bearerRefreshToken: String): Call<ApiEnvelope<AuthResponseDto>>
}
