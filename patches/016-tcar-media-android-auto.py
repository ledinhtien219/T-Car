from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8")

# Advertise both Android Auto surfaces from the same installed APK.
# T-Car is the Car App Library/navigation surface; T-Car Media is the
# independent MediaBrowserService surface discovered by Android Auto.
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

        <meta-data
            android:name="com.google.android.gms.car.notification.SmallIcon"
            android:resource="@drawable/ic_bar_play"/>

''',
    "Android Auto app metadata"
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

# One APK explicitly advertises both capabilities. Android Auto can therefore
# discover the CarAppService as T-Car and the MediaBrowserService as T-Car Media.
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

# Keep a sticky service if the base source ever loses its existing implementation.
if "override fun onStartCommand(" not in service:
    insert_at = service.find("    override fun onCreate() {")
    if insert_at < 0:
        raise RuntimeError("CarMediaBrowserService onCreate not found")
    method = '''    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

'''
    service = service[:insert_at] + method + service[insert_at:]

# Give the media session a stable phone-side activity for media cards/controls.
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

# Fail the transform immediately if a future source ZIP accidentally drops any
# declaration required for the two Android Auto launcher entries.
final_manifest = manifest_path.read_text(encoding="utf-8")
final_desc = desc_path.read_text(encoding="utf-8")
required_manifest = {
    "T-Car CarAppService": 'android:name="com.carhud.aaproxy.CarHudAutoService"',
    "T-Car navigation category": 'android:name="androidx.car.app.category.NAVIGATION"',
    "T-Car Media service": 'android:name="com.carhud.aaproxy.CarMediaBrowserService"',
    "T-Car Media label": 'android:label="T-Car Media"',
    "MediaBrowserService action": 'android:name="android.media.browse.MediaBrowserService"',
    "Android Auto descriptor metadata": 'android:name="com.google.android.gms.car.application"',
}
for label, needle in required_manifest.items():
    if needle not in final_manifest:
        raise RuntimeError(f"Android Auto declaration missing after patch: {label}")

for capability in ('<uses name="media"/>', '<uses name="template"/>'):
    if capability not in final_desc:
        raise RuntimeError(f"Android Auto capability missing after patch: {capability}")

required_service = (
    "class CarMediaBrowserService : MediaBrowserServiceCompat()",
    "sessionToken = session.sessionToken",
    "isActive = true",
    "override fun onGetRoot(",
    "override fun onLoadChildren(",
)
for needle in required_service:
    if needle not in service:
        raise RuntimeError(f"T-Car Media service contract missing: {needle}")

print("Verified single-APK Android Auto discovery: T-Car + T-Car Media")
