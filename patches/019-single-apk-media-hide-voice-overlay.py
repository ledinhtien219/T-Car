from pathlib import Path
import re

ROOT = Path("/tmp/tcar")

# ---------------------------------------------------------------------------
# One APK only: T-Car also advertises its built-in media service as T-Car Media.
# ---------------------------------------------------------------------------
settings_path = ROOT / "settings.gradle.kts"
settings = settings_path.read_text(encoding="utf-8")
settings = re.sub(r'\n?include\(":mediaapp"\)\s*', '\n', settings)
settings_path.write_text(settings, encoding="utf-8")

desc_path = ROOT / "app/src/main/res/xml/automotive_app_desc.xml"
desc = desc_path.read_text(encoding="utf-8")
if '<uses name="media"/>' not in desc:
    desc = desc.replace('</automotiveApp>', '    <uses name="media"/>\n</automotiveApp>')
desc_path.write_text(desc, encoding="utf-8")

manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8")

# The main package's MediaBrowserService is the Android Auto media source.
service_start = re.search(
    r'<service\s+[^>]*android:name="com\.carhud\.aaproxy\.CarMediaBrowserService"[^>]*>',
    manifest,
    re.S
)
if not service_start:
    raise RuntimeError("CarMediaBrowserService manifest entry not found")

tag = service_start.group(0)
if 'android:label=' in tag:
    tag = re.sub(r'android:label="[^"]*"', 'android:label="T-Car Media"', tag, count=1)
else:
    tag = tag[:-1] + '\n            android:label="T-Car Media">'

if 'android:icon=' not in tag:
    tag = tag[:-1] + '\n            android:icon="@drawable/ic_carhud_media">'

manifest = manifest[:service_start.start()] + tag + manifest[service_start.end():]

# Ensure the media browse intent is still present inside that service block.
service_pos = manifest.find('android:name="com.carhud.aaproxy.CarMediaBrowserService"')
service_end = manifest.find('</service>', service_pos)
if service_end < 0:
    raise RuntimeError("CarMediaBrowserService closing tag not found")
service_block = manifest[service_pos:service_end]
if 'android.media.browse.MediaBrowserService' not in service_block:
    insert_at = manifest.find('>', service_pos) + 1
    intent = '''
            <intent-filter>
                <action android:name="android.media.browse.MediaBrowserService" />
            </intent-filter>'''
    manifest = manifest[:insert_at] + intent + manifest[insert_at:]

# One installed package, but expose a second launcher entry named T-Car Media.
# It targets the same app/data; there is no second APK and no second signature.
if 'android:name=".TCarMediaLauncher"' not in manifest:
    alias = '''
        <activity-alias
            android:name=".TCarMediaLauncher"
            android:targetActivity="com.carhud.aaproxy.MainActivity"
            android:exported="true"
            android:label="T-Car Media"
            android:icon="@drawable/ic_carhud_media">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity-alias>
'''
    manifest = manifest.replace('</application>', alias + '    </application>', 1)

manifest_path.write_text(manifest, encoding="utf-8")

# ---------------------------------------------------------------------------
# Hide the floating voice/search banner on the car display.
# Voice recognition/search continues to work; only the overlay is suppressed.
# ---------------------------------------------------------------------------
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")
car = re.sub(
    r'(searchOverlay\.visibility\s*=\s*)View\.VISIBLE',
    r'\1View.GONE',
    car
)

# Also hide immediately after construction so it never flashes for one frame.
needle = 'searchOverlay = '
pos = car.find(needle)
if pos >= 0:
    line_end = car.find('\n', pos)
    # Construction is often a multiline apply block, so rely on the first
    # later addView/search setup point and insert a safe GONE assignment once.
    marker = 'addView(searchOverlay)'
    if marker in car and 'searchOverlay.visibility = View.GONE // always hidden on car' not in car:
        car = car.replace(
            marker,
            marker + '\n        searchOverlay.visibility = View.GONE // always hidden on car',
            1
        )

car_path.write_text(car, encoding="utf-8")

print("Restored single-APK T-Car + T-Car Media and hid car voice overlay")
