package com.empresa.gestordocumental.ui.scanner

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.net.Uri
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResult
import androidx.activity.result.ActivityResultCaller
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import com.google.mlkit.vision.documentscanner.GmsDocumentScanner
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult

/** Resultado tipado de una sesión de escaneo. */
sealed interface ScanResult {
    /**
     * @param pages imágenes JPEG de cada página (Uri `file://` en la caché de la app).
     * @param pdfUri PDF multipágina generado por ML Kit (puede ser null).
     */
    data class Success(val pages: List<Uri>, val pdfUri: Uri?, val pageCount: Int) : ScanResult

    /** El usuario cerró el escáner sin guardar. */
    data object Cancelled : ScanResult

    data class Error(val message: String, val cause: Throwable? = null) : ScanResult
}

/**
 * Encapsula Google ML Kit Document Scanner:
 *  - Configuración (modo FULL, JPEG + PDF, importación desde galería, límite de páginas).
 *  - Lanzamiento mediante [ActivityResultLauncher]<[IntentSenderRequest]>.
 *  - Traducción del resultado a [ScanResult].
 *
 * Uso desde Activity/Fragment:
 * ```
 * private val scanner = DocumentScannerManager()
 * override fun onCreate(...) { scanner.register(this) { result -> ... } }
 * button.setOnClickListener { scanner.launch(this) }
 * ```
 * Uso desde Compose: [rememberDocumentScanner].
 */
class DocumentScannerManager(
    pageLimit: Int = DEFAULT_PAGE_LIMIT,
    galleryImportAllowed: Boolean = true,
) {
    init {
        require(pageLimit in 1..MAX_PAGE_LIMIT) { "pageLimit debe estar entre 1 y $MAX_PAGE_LIMIT" }
    }

    private val options: GmsDocumentScannerOptions = GmsDocumentScannerOptions.Builder()
        .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
        .setResultFormats(
            GmsDocumentScannerOptions.RESULT_FORMAT_JPEG,
            GmsDocumentScannerOptions.RESULT_FORMAT_PDF,
        )
        .setGalleryImportAllowed(galleryImportAllowed)
        .setPageLimit(pageLimit)
        .build()

    private val scanner: GmsDocumentScanner = GmsDocumentScanning.getClient(options)

    private var launcher: ActivityResultLauncher<IntentSenderRequest>? = null
    private var resultCallback: ((ScanResult) -> Unit)? = null

    /**
     * Registra el launcher. Debe llamarse antes de que la Activity/Fragment
     * alcance el estado STARTED (p. ej. en onCreate).
     */
    fun register(caller: ActivityResultCaller, onResult: (ScanResult) -> Unit) {
        resultCallback = onResult
        launcher = caller.registerForActivityResult(
            ActivityResultContracts.StartIntentSenderForResult(),
        ) { result -> onResult(parseResult(result)) }
    }

    /** Asocia un launcher creado externamente (p. ej. desde Compose). */
    fun attach(launcher: ActivityResultLauncher<IntentSenderRequest>, onResult: (ScanResult) -> Unit) {
        this.launcher = launcher
        this.resultCallback = onResult
    }

    /**
     * Solicita a Play Services el IntentSender del escáner y lo lanza.
     * Los errores previos al lanzamiento (módulo no descargado, dispositivo no
     * compatible...) se notifican por el mismo callback de resultado.
     */
    fun launch(activity: Activity) {
        val currentLauncher = launcher
        val callback = resultCallback
        if (currentLauncher == null || callback == null) {
            Log.e(TAG, "launch() llamado sin register()/attach() previo")
            callback?.invoke(ScanResult.Error("El escáner no está inicializado."))
            return
        }
        scanner.getStartScanIntent(activity)
            .addOnSuccessListener { intentSender ->
                try {
                    currentLauncher.launch(IntentSenderRequest.Builder(intentSender).build())
                } catch (e: Exception) {
                    Log.e(TAG, "No se pudo lanzar el escáner", e)
                    callback(ScanResult.Error("No se pudo abrir el escáner.", e))
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Error obteniendo el intent del escáner", e)
                callback(mapStartError(e))
            }
    }

    /** Convierte el [ActivityResult] devuelto por ML Kit en un [ScanResult]. */
    fun parseResult(result: ActivityResult): ScanResult {
        return when (result.resultCode) {
            Activity.RESULT_OK -> {
                val scanningResult = GmsDocumentScanningResult.fromActivityResultIntent(result.data)
                    ?: return ScanResult.Error("El escáner no devolvió ningún resultado.")
                val pages = scanningResult.pages.orEmpty().map { it.imageUri }
                val pdf = scanningResult.pdf
                if (pages.isEmpty() && pdf == null) {
                    ScanResult.Error("No se ha escaneado ninguna página.")
                } else {
                    ScanResult.Success(
                        pages = pages,
                        pdfUri = pdf?.uri,
                        pageCount = pdf?.pageCount ?: pages.size,
                    )
                }
            }
            Activity.RESULT_CANCELED -> ScanResult.Cancelled
            else -> ScanResult.Error("El escáner terminó con un código inesperado (${result.resultCode}).")
        }
    }

    private fun mapStartError(e: Exception): ScanResult.Error {
        val raw = e.message.orEmpty()
        val message = when {
            raw.contains("unavailable", ignoreCase = true) || raw.contains("download", ignoreCase = true) ->
                "El módulo de escaneo se está descargando. Inténtalo de nuevo en unos segundos."
            raw.contains("unsupported", ignoreCase = true) || raw.contains("not supported", ignoreCase = true) ->
                "Este dispositivo no es compatible con el escáner de documentos."
            else -> "No se pudo iniciar el escáner: ${e.localizedMessage ?: "error desconocido"}"
        }
        return ScanResult.Error(message, e)
    }

    companion object {
        private const val TAG = "DocumentScanner"
        const val DEFAULT_PAGE_LIMIT = 10
        const val MAX_PAGE_LIMIT = 100
    }
}

/** Manejador estable que la UI usa para lanzar el escáner. */
@Stable
class DocumentScannerHandle internal constructor(private val onLaunch: () -> Unit) {
    fun launch() = onLaunch()
}

/**
 * Versión Compose: crea el launcher ligado al ciclo de vida de la composición
 * y devuelve un [DocumentScannerHandle] para lanzar el escáner.
 */
@Composable
fun rememberDocumentScanner(
    pageLimit: Int = DocumentScannerManager.DEFAULT_PAGE_LIMIT,
    galleryImportAllowed: Boolean = true,
    onResult: (ScanResult) -> Unit,
): DocumentScannerHandle {
    val context = LocalContext.current
    val currentOnResult by rememberUpdatedState(onResult)
    val manager = remember(pageLimit, galleryImportAllowed) {
        DocumentScannerManager(pageLimit, galleryImportAllowed)
    }
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result -> currentOnResult(manager.parseResult(result)) }

    return remember(manager, launcher, context) {
        manager.attach(launcher) { result -> currentOnResult(result) }
        DocumentScannerHandle {
            val activity = context.findActivity()
            if (activity == null) {
                currentOnResult(ScanResult.Error("No se encontró la Activity para abrir el escáner."))
            } else {
                manager.launch(activity)
            }
        }
    }
}

/** Recorre los ContextWrapper hasta encontrar la Activity anfitriona. */
tailrec fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
