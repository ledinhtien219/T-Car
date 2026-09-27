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

            if (!ksPath.isNullOrBlank() &&
                !ksStorePassword.isNullOrBlank() &&
                !ksAlias.isNullOrBlank() &&
                !ksKeyPassword.isNullOrBlank()
            ) {
                storeFile = file(ksPath)
                storePassword = ksStorePassword
                keyAlias = ksAlias
                keyPassword = ksKeyPassword
            }
        }
    }
'''

if old_signing not in text:
    raise RuntimeError("Expected original signingConfigs block not found")

text = text.replace(old_signing, new_signing, 1)

old_release = '            signingConfig = signingConfigs.getByName("debug")'
new_release = '''            signingConfig = if (System.getenv("TCAR_KEYSTORE_PATH").isNullOrBlank()) {
                signingConfigs.getByName("debug")
            } else {
                signingConfigs.getByName("release")
            }'''

if old_release not in text:
    raise RuntimeError("Expected debug release signingConfig not found")

text = text.replace(old_release, new_release, 1)
path.write_text(text, encoding="utf-8")
print("Configured stable T-Car release signing")
