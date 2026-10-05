package com.empresa.gestordocumental.data.api

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import retrofit2.HttpException
import java.io.IOException

/** Fallo de API normalizado para la capa de dominio/UI. */
sealed class ApiFailure(open val message: String) {
    /** Sin conexión / timeout: la operación puede reintentarse más tarde. */
    data class Network(override val message: String) : ApiFailure(message)

    /** Respuesta HTTP de error del backend (validación, permisos...). */
    data class Http(
        val code: Int,
        override val message: String,
        val fieldErrors: Map<String, String> = emptyMap(),
    ) : ApiFailure(message)

    data class Unexpected(override val message: String) : ApiFailure(message)
}

/** Traduce excepciones de Retrofit/OkHttp a [ApiFailure] leyendo el cuerpo JSON de error. */
fun Throwable.toApiFailure(json: Json): ApiFailure = when (this) {
    is HttpException -> {
        val body = response()?.errorBody()?.string()
        val parsed = body?.let { runCatching { json.decodeFromString(ApiErrorDto.serializer(), it) }.getOrNull() }
        val fieldErrors = parsed?.errors.orEmpty().mapValues { (_, value) ->
            when (value) {
                is JsonArray -> value.joinToString(" ") { (it as? JsonPrimitive)?.contentOrNull ?: it.toString() }
                is JsonPrimitive -> value.contentOrNull.orEmpty()
                else -> value.toString()
            }
        }
        val defaultMessage = when (code()) {
            401 -> "La sesión ha caducado. Inicia sesión de nuevo."
            403 -> "No tienes permisos para realizar esta acción."
            413 -> "La imagen es demasiado grande."
            in 500..599 -> "Error del servidor. Inténtalo más tarde."
            else -> "Error ${code()}"
        }
        ApiFailure.Http(code(), parsed?.message ?: defaultMessage, fieldErrors)
    }
    is IOException -> ApiFailure.Network("Sin conexión con el servidor.")
    else -> ApiFailure.Unexpected(localizedMessage ?: "Error inesperado.")
}
