# Gestor Documental — App Android (Kotlin + Jetpack Compose)

Clean Architecture + MVVM, Hilt, Retrofit/OkHttp (JWT con refresh automático),
Room (caché + cola offline), WorkManager (subida diferida), DataStore (sesión)
y Google ML Kit Document Scanner.

## Ejecutar

1. Arranca el backend (`backend/README.md`) en el puerto 5000.
2. Abre `android/` en Android Studio (Koala o superior, JDK 17) y ejecuta en un
   emulador. En debug la app apunta a `http://10.0.2.2:5000/api/v1/`; la URL de
   release se define en `app/build.gradle.kts`.
3. El escáner necesita Google Play Services (emulador con imagen "Google Play").

## Estructura

```
app/src/main/java/com/empresa/gestordocumental/
├── data/api          Retrofit (ApiService), DTOs, AuthInterceptor + TokenAuthenticator, errores
├── data/local        Room (caché de categorías/contactos, cola de subidas) y TokenStore (DataStore)
├── data/repository   AuthRepository, CatalogRepository, DocumentRepository
├── data/work         UploadDocumentWorker (WorkManager + Hilt)
├── domain/model      Modelos de dominio
├── di                Módulos Hilt (red, base de datos)
├── ui/theme          Color.kt, Theme.kt (claro/oscuro), Type.kt
├── ui/scanner        DocumentScannerManager (ML Kit)
├── ui/components     Componentes reutilizables
├── ui/screens        auth/LoginScreen, documents/UploadDocumentScreen
└── ui/viewmodels     SessionViewModel, LoginViewModel, UploadDocumentViewModel
```
