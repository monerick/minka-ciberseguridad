[app]

title = MINKA VOZ
package.name = minkavoz
package.domain = org.minkavoz

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,spec

version = 2.0.0

requirements = python3,
    pillow,
    sqlite3,
    bcrypt,
    cryptography

orientation = portrait

fullscreen = 0

android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

android.api = 31
android.minapi = 24
android.ndk = 25b
android.sdk = 31
android.accept_sdk_license = True

android.arch = arm64-v8a
android.arch_back = armeabi-v7a

# Proveedor degradación
android.enable_degradation = False

# Número de versión de la compilación
android.numeric_version = 2

# Ícono
#android.icon = %(source.dir)s/assets/icon.png
#android.adaptive_icon_fg = %(source.dir)s/assets/icon_fg.png
#android.adaptive_icon_bg = %(source.dir)s/assets/icon_bg.png

# Splash
#android.presplash = %(source.dir)s/assets/splash.png

# Orientación
android.orientation = portrait

# Gradle
android.use_gradle = True
android.gradle_dependencies = com.android.support:appcompat-v7:28.0.0

# Pantalla
android.add_classes = org.minkavoz.MinkaVozActivity

# Solo portrait
android.allow_backup = True

# Permissions extras
android.license = 

# Archivos para incluir
source.include_patterns = assets/*

# Archivos de configuración
p4a.branch = develop

# Logs
log_level = 2

# Archivos que se incluyen
#presplash = assets/splash.png
#icon = assets/icon.png

# Splash
#splash = assets/splash.png

# Android X
android.enable_androidx = True
android.enable_jetpack = True

# compileo
android.compile_sdk_version = 31
android.build_tools_version = 31.0.3

# Permisos
