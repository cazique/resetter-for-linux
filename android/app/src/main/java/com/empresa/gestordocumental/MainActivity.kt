package com.empresa.gestordocumental

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.empresa.gestordocumental.ui.screens.auth.LoginScreen
import com.empresa.gestordocumental.ui.screens.documents.UploadDocumentScreen
import com.empresa.gestordocumental.ui.theme.GestorTheme
import com.empresa.gestordocumental.ui.viewmodels.SessionViewModel
import dagger.hilt.android.AndroidEntryPoint

/**
 * Activity única. Decide qué mostrar según el estado de sesión:
 * lectura en curso → indicador; sin sesión → login; con sesión → alta de documento.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val sessionViewModel: SessionViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            GestorTheme {
                val isLoggedIn by sessionViewModel.isLoggedIn.collectAsStateWithLifecycle()
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    when (isLoggedIn) {
                        null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                        false -> LoginScreen()
                        true -> UploadDocumentScreen(onLogout = sessionViewModel::logout)
                    }
                }
            }
        }
    }
}
