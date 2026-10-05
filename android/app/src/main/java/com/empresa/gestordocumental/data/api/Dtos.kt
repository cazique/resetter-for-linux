package com.empresa.gestordocumental.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/** Envoltorio estándar de respuesta del backend: {success, data, message, meta}. */
@Serializable
data class ApiEnvelope<T>(
    val success: Boolean,
    val data: T? = null,
    val message: String? = null,
    val meta: PageMetaDto? = null,
)

/** Cuerpo de error del backend: {success:false, message, errors:{campo:[...]}}. */
@Serializable
data class ApiErrorDto(
    val success: Boolean = false,
    val message: String? = null,
    val errors: Map<String, JsonElement>? = null,
)

@Serializable
data class PageMetaDto(
    val page: Int,
    @SerialName("per_page") val perPage: Int,
    val total: Int,
    val pages: Int,
)

@Serializable
data class LoginRequestDto(val email: String, val password: String)

@Serializable
data class AuthResponseDto(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("token_type") val tokenType: String? = null,
    val user: UserDto? = null,
)

@Serializable
data class UserDto(
    val id: String,
    val email: String,
    @SerialName("full_name") val fullName: String? = null,
    val role: String,
)

@Serializable
data class CategoryDto(
    val id: Int,
    val name: String,
    @SerialName("color_hex") val colorHex: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
)

@Serializable
data class ContactDto(
    val id: String,
    val name: String,
    val type: String,
    val phone: String? = null,
    val email: String? = null,
    @SerialName("tax_id") val taxId: String? = null,
)

@Serializable
data class ContactSummaryDto(val id: String, val name: String, val type: String)

@Serializable
data class DocumentDto(
    val id: String,
    val title: String? = null,
    val amount: Double = 0.0,
    @SerialName("tax_amount") val taxAmount: Double = 0.0,
    val date: String,
    val status: String,
    val notes: String? = null,
    @SerialName("category_id") val categoryId: Int,
    @SerialName("contact_id") val contactId: String? = null,
    val category: CategoryDto? = null,
    val contact: ContactSummaryDto? = null,
    @SerialName("thumbnail_url") val thumbnailUrl: String? = null,
    @SerialName("image_url") val imageUrl: String? = null,
)
