from pathlib import Path

path = Path("/tmp/tcar/app/build.gradle.kts")
text = path.read_text(encoding="utf-8")

old_signing = '''    signingConfigs {
        create("release") {
            val debugKey = file(System.getProperty("user.home") + "/.android/debug.keystore")
            if (debugKey.exists()) {
                storeFile = debugKey
                storePassword = "android"
                keyAlias = "androiddebugkey"
                keyPassword = "android"
            }
        }
    }
'''

new_signing = '''    signingConfigs {
        create("release") {
            val ksPath = System.getenv("TCAR_KEYSTORE_PATH")
            val ksStorePassword = System.getenv("TCAR_KEYSTORE_PASSWORD")
            val ksAlias = System.getenv("TCAR_KEY_ALIAS")
            val ksKeyPassword = System.getenv("TCAR_KEY_PASSWORD")

            require(!ksPath.isNullOrBlank()) { "TCAR_KEYSTORE_PATH is required" }
            require(!ksStorePassword.isNullOrBlank()) { "TCAR_KEYSTORE_PASSWORD is required" }
            require(!ksAlias.isNullOrBlank()) { "TCAR_KEY_ALIAS is required" }
            require(!ksKeyPassword.isNullOrBlank()) { "TCAR_KEY_PASSWORD is required" }

            storeFile = file(ksPath)
            storePassword = ksStorePassword
            keyAlias = ksAlias
            keyPassword = ksKeyPassword
        }
    }
'''

if old_signing not in text:
    raise RuntimeError("Expected original signingConfigs block not found")

text = text.replace(old_signing, new_signing, 1)

old_release = '            signingConfig = signingConfigs.getByName("debug")'
new_release = '            signingConfig = signingConfigs.getByName("release")'

if old_release not in text:
    raise RuntimeError("Expected debug release signingConfig not found")

text = text.replace(old_release, new_release, 1)
path.write_text(text, encoding="utf-8")
print("Configured stable T-Car release signing")
