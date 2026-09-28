from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8")

# Explicitly mark T-Car Media as an independent Android Auto media source.
manifest = replace_once(
    manifest,
    '''        <meta-data
            android:name="com.google.android.gms.car.application"
            android:resource="@xml/automotive_app_desc"/>

''',
    '''        <meta-data
            android:name="com.google.android.gms.car.application"
            android:resource="@xml/automotive_app_desc"/>

        <meta-data
            android:name="androidx.car.app.TintableAttributionIcon"
            android:resource="@drawable/ic_carhud_media"/>

''',
    "Android Auto attribution icon"
)

manifest = replace_once(
    manifest,
    '''        <service
            android:name="com.carhud.aaproxy.CarMediaBrowserService"
            android:exported="true"
            android:label="T-Car Media"
            android:foregroundServiceType="mediaPlayback"
            android:icon="@drawable/ic_carhud_media">
''',
    '''        <service
            android:name="com.carhud.aaproxy.CarMediaBrowserService"
            android:enabled="true"
            android:exported="true"
            android:stopWithTask="false"
            android:label="T-Car Media"
            android:foregroundServiceType="mediaPlayback"
            android:icon="@drawable/ic_carhud_media">
''',
    "media service discovery flags"
)

manifest_path.write_text(manifest, encoding="utf-8")

# Keep the descriptor explicit: one installed APK advertises both T-Car
# (template/navigation surface) and T-Car Media (MediaBrowserService source).
desc_path = ROOT / "app/src/main/res/xml/automotive_app_desc.xml"
desc_path.write_text(
    '''<?xml version="1.0" encoding="utf-8"?>\n'''
    '''<automotiveApp xmlns:android="http://schemas.android.com/apk/res/android">\n'''
    '''    <uses name="media"/>\n'''
    '''    <uses name="template"/>\n'''
    '''</automotiveApp>\n''',
    encoding="utf-8"
)

service_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarMediaBrowserService.kt"
service = service_path.read_text(encoding="utf-8")

# A sticky start makes the same media source stay available when T-Car has
# already been opened, while Android Auto can still bind to it directly from
# the launcher immediately after install.
if "override fun onStartCommand(" not in service:
    insert_at = service.find("    override fun onCreate() {")
    if insert_at < 0:
        raise RuntimeError("CarMediaBrowserService onCreate not found")
    method = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

'''
    service = service[:insert_at] + method + service[insert_at:]

# Give Android Auto a stable session activity for the Media card/source.
session_anchor = '''                setFlags(
                    MediaSessionCompat.FLAG_HANDLES_MEDIA_BUTTONS or
                    MediaSessionCompat.FLAG_HANDLES_TRANSPORT_CONTROLS
                )

'''
if "setSessionActivity(" not in service:
    session_activity = session_anchor + '''                try {
                    val launchIntent = packageManager.getLaunchIntentForPackage(packageName)?.apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    }
                    if (launchIntent != null) {
                        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0
                        setSessionActivity(
                            PendingIntent.getActivity(
                                this@CarMediaBrowserService,
                                2001,
                                launchIntent,
                                flags
                            )
                        )
                    }
                } catch (_: Exception) {}

'''
    service = replace_once(service, session_anchor, session_activity, "media session activity")

service_path.write_text(service, encoding="utf-8")

print("Hardened T-Car Media Android Auto discovery")
