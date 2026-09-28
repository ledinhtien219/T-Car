from pathlib import Path
import re

ROOT = Path("/tmp/tcar")

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def write(rel, data):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError("Missing expected source block: " + label)
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Main T-Car becomes template/navigation only. Keep its internal media service
# for playback/session state, but stop advertising it as the Android Auto media app.
# ---------------------------------------------------------------------------
settings_path = ROOT / "settings.gradle.kts"
settings = settings_path.read_text(encoding="utf-8")
if 'include(":mediaapp")' not in settings:
    settings = settings.rstrip() + '\ninclude(":mediaapp")\n'
settings_path.write_text(settings, encoding="utf-8")

auto_desc = ROOT / "app/src/main/res/xml/automotive_app_desc.xml"
desc = auto_desc.read_text(encoding="utf-8")
desc = desc.replace('    <uses name="media"/>\n', '')
auto_desc.write_text(desc, encoding="utf-8")

manifest_path = ROOT / "app/src/main/AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8")
service_pattern = re.compile(
    r'''        <!-- Android Auto MediaBrowserService -->\s*<service\s+android:name="com\.carhud\.aaproxy\.CarMediaBrowserService".*?</service>''',
    re.S
)
replacement = '''        <!-- Internal media/session service. Android Auto media discovery is
             provided by the separate com.carhud.media APK. -->
        <service
            android:name="com.carhud.aaproxy.CarMediaBrowserService"
            android:exported="true"
            android:label="T-Car Media Engine"
            android:foregroundServiceType="mediaPlayback"
            android:icon="@drawable/ic_carhud_media" />'''
manifest, count = service_pattern.subn(replacement, manifest, count=1)
if count != 1:
    raise RuntimeError("Could not replace main CarMediaBrowserService manifest block")
manifest_path.write_text(manifest, encoding="utf-8")

# ---------------------------------------------------------------------------
# Separate T-Car Media Android app.
# ---------------------------------------------------------------------------
media_gradle = r'''plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.carhud.media"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.carhud.media"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.0.0"
    }

    signingConfigs {
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

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (System.getenv("TCAR_KEYSTORE_PATH").isNullOrBlank()) {
                signingConfigs.getByName("debug")
            } else {
                signingConfigs.getByName("release")
            }
        }
        debug {
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.media:media:1.7.0")
    implementation(libs.androidx.core.ktx)
}
'''
write("mediaapp/build.gradle.kts", media_gradle)

media_manifest = r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <queries>
        <package android:name="com.carhud.app" />
    </queries>

    <application
        android:allowBackup="false"
        android:label="T-Car Media"
        android:icon="@drawable/ic_tcar_media"
        android:roundIcon="@drawable/ic_tcar_media"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">

        <meta-data
            android:name="com.google.android.gms.car.application"
            android:resource="@xml/automotive_app_desc" />

        <activity
            android:name=".MediaLauncherActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <service
            android:name=".TCarMediaService"
            android:exported="true"
            android:label="T-Car Media"
            android:icon="@drawable/ic_tcar_media"
            android:foregroundServiceType="mediaPlayback">
            <intent-filter>
                <action android:name="android.media.browse.MediaBrowserService" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.media.action.MEDIA_PLAY_FROM_SEARCH" />
                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
            <meta-data
                android:name="com.google.android.gms.car.notification.SmallIcon"
                android:resource="@drawable/ic_tcar_media_mono" />
        </service>

        <receiver
            android:name="androidx.media.session.MediaButtonReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MEDIA_BUTTON" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
'''
write("mediaapp/src/main/AndroidManifest.xml", media_manifest)
write("mediaapp/src/main/res/xml/automotive_app_desc.xml", '''<?xml version="1.0" encoding="utf-8"?>
<automotiveApp>
    <uses name="media"/>
</automotiveApp>
''')

# Rich navy/cyan media icon with play mark + equalizer, distinct from T-Car.
icon = r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#07111F"
        android:pathData="M54,4 A50,50 0,1 1,53.99,4 Z"/>
    <path
        android:fillColor="#10243B"
        android:strokeColor="#16D9FF"
        android:strokeWidth="3"
        android:pathData="M54,10 A44,44 0,1 1,53.99,10 Z"/>
    <path android:fillColor="#18D7FF" android:pathData="M26,50 L31,50 L31,68 L26,68 Z"/>
    <path android:fillColor="#33A8FF" android:pathData="M35,42 L40,42 L40,76 L35,76 Z"/>
    <path android:fillColor="#8A6CFF" android:pathData="M44,47 L49,47 L49,71 L44,71 Z"/>
    <path android:fillColor="#18D7FF" android:pathData="M58,39 L63,39 L63,79 L58,79 Z"/>
    <path android:fillColor="#33A8FF" android:pathData="M67,45 L72,45 L72,73 L67,73 Z"/>
    <path android:fillColor="#8A6CFF" android:pathData="M76,51 L81,51 L81,67 L76,67 Z"/>
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M47,34 L47,50 L61,42 Z"/>
    <path
        android:fillColor="#BDF6FF"
        android:pathData="M54,88 A4,4 0,1 1,53.99,88 Z"/>
</vector>
'''
write("mediaapp/src/main/res/drawable/ic_tcar_media.xml", icon)

mono = r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF"
        android:pathData="M4,9h2v7H4zM8,6h2v13H8zM12,8h2v9h-2zM16,5h2v15h-2zM20,10h2v5h-2z"/>
</vector>
'''
write("mediaapp/src/main/res/drawable/ic_tcar_media_mono.xml", mono)

launcher = r'''package com.carhud.media

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.widget.TextView

class MediaLauncherActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val launch = packageManager.getLaunchIntentForPackage("com.carhud.app")
        if (launch != null) {
            launch.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(launch)
            finish()
            return
        }

        setContentView(TextView(this).apply {
            text = "T-Car Media\n\nHãy cài T-Car chính để phát YouTube / IPTV."
            textSize = 20f
            gravity = Gravity.CENTER
            setPadding(40, 40, 40, 40)
        })
    }
}
'''
write("mediaapp/src/main/java/com/carhud/media/MediaLauncherActivity.kt", launcher)

service = r'''package com.carhud.media

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.support.v4.media.MediaBrowserCompat
import android.support.v4.media.MediaDescriptionCompat
import android.support.v4.media.MediaMetadataCompat
import android.support.v4.media.session.MediaControllerCompat
import android.support.v4.media.session.MediaSessionCompat
import android.support.v4.media.session.PlaybackStateCompat
import androidx.core.app.NotificationCompat
import androidx.media.MediaBrowserServiceCompat
import androidx.media.app.NotificationCompat.MediaStyle

class TCarMediaService : MediaBrowserServiceCompat() {
    companion object {
        private const val ROOT_ID = "tcar_media_root"
        private const val CHANNEL_ID = "tcar_media_proxy"
        private const val NOTIFICATION_ID = 2401
        private val MAIN_COMPONENT = ComponentName(
            "com.carhud.app",
            "com.carhud.aaproxy.CarMediaBrowserService"
        )
    }

    private lateinit var mediaSession: MediaSessionCompat
    private var mainBrowser: MediaBrowserCompat? = null
    private var mainController: MediaControllerCompat? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private var currentMetadata: MediaMetadataCompat? = null
    private var currentState: PlaybackStateCompat? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        mediaSession = MediaSessionCompat(this, "TCarMediaProxy").apply {
            setFlags(
                MediaSessionCompat.FLAG_HANDLES_MEDIA_BUTTONS or
                    MediaSessionCompat.FLAG_HANDLES_TRANSPORT_CONTROLS
            )
            setCallback(object : MediaSessionCompat.Callback() {
                override fun onPlay() = forward { it.play() }
                override fun onPause() = forward { it.pause() }
                override fun onSkipToNext() = forward { it.skipToNext() }
                override fun onSkipToPrevious() = forward { it.skipToPrevious() }
                override fun onSeekTo(pos: Long) = forward { it.seekTo(pos) }

                override fun onPlayFromSearch(query: String?, extras: Bundle?) {
                    if (!query.isNullOrBlank()) {
                        forward { it.playFromSearch(query, extras) }
                    }
                }

                override fun onPlayFromMediaId(mediaId: String?, extras: Bundle?) {
                    when (mediaId) {
                        "media_now" -> forward { it.play() }
                        "media_home", "media_open_carhud", "media_next", "media_prev", "media_reload" ->
                            forward { it.playFromMediaId(mediaId, extras) }
                        else -> forward { it.play() }
                    }
                }
            })
            isActive = true
        }
        sessionToken = mediaSession.sessionToken
        setDisconnectedState()
        connectToMain()
    }

    private fun connectToMain() {
        try {
            mainBrowser?.disconnect()
        } catch (_: Exception) {}

        val browser = MediaBrowserCompat(
            this,
            MAIN_COMPONENT,
            object : MediaBrowserCompat.ConnectionCallback() {
                override fun onConnected() {
                    try {
                        val b = mainBrowser ?: return
                        val controller = MediaControllerCompat(this@TCarMediaService, b.sessionToken)
                        mainController = controller
                        controller.registerCallback(controllerCallback)
                        syncFromMain(controller)
                    } catch (_: Exception) {
                        setDisconnectedState()
                    }
                }

                override fun onConnectionSuspended() {
                    mainController = null
                    setDisconnectedState()
                    scheduleReconnect()
                }

                override fun onConnectionFailed() {
                    mainController = null
                    setDisconnectedState()
                    scheduleReconnect()
                }
            },
            null
        )
        mainBrowser = browser
        try {
            browser.connect()
        } catch (_: Exception) {
            scheduleReconnect()
        }
    }

    private fun scheduleReconnect() {
        mainHandler.removeCallbacksAndMessages(null)
        mainHandler.postDelayed({ connectToMain() }, 1500L)
    }

    private val controllerCallback = object : MediaControllerCompat.Callback() {
        override fun onMetadataChanged(metadata: MediaMetadataCompat?) {
            currentMetadata = metadata
            metadata?.let { mediaSession.setMetadata(it) }
            notifyChildrenChanged(ROOT_ID)
            updateNotification()
        }

        override fun onPlaybackStateChanged(state: PlaybackStateCompat?) {
            currentState = state
            state?.let { mediaSession.setPlaybackState(it) }
            updateNotification()
        }

        override fun onSessionDestroyed() {
            mainController = null
            setDisconnectedState()
            scheduleReconnect()
        }
    }

    private fun syncFromMain(controller: MediaControllerCompat) {
        currentMetadata = controller.metadata
        currentState = controller.playbackState
        currentMetadata?.let { mediaSession.setMetadata(it) }
        currentState?.let { mediaSession.setPlaybackState(it) }
        notifyChildrenChanged(ROOT_ID)
        updateNotification()
    }

    private inline fun forward(block: (MediaControllerCompat.TransportControls) -> Unit) {
        val controls = mainController?.transportControls
        if (controls != null) {
            try { block(controls) } catch (_: Exception) {}
        } else {
            connectToMain()
        }
    }

    private fun setDisconnectedState() {
        currentState = PlaybackStateCompat.Builder()
            .setActions(
                PlaybackStateCompat.ACTION_PLAY or
                    PlaybackStateCompat.ACTION_PLAY_PAUSE or
                    PlaybackStateCompat.ACTION_PLAY_FROM_MEDIA_ID or
                    PlaybackStateCompat.ACTION_PLAY_FROM_SEARCH
            )
            .setState(PlaybackStateCompat.STATE_PAUSED, 0L, 0f)
            .build()
        currentMetadata = MediaMetadataCompat.Builder()
            .putString(MediaMetadataCompat.METADATA_KEY_TITLE, "T-Car Media")
            .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, "Mở T-Car để bắt đầu phát")
            .build()
        mediaSession.setPlaybackState(currentState)
        mediaSession.setMetadata(currentMetadata)
        notifyChildrenChanged(ROOT_ID)
    }

    override fun onGetRoot(
        clientPackageName: String,
        clientUid: Int,
        rootHints: Bundle?
    ): BrowserRoot = BrowserRoot(ROOT_ID, null)

    override fun onLoadChildren(
        parentId: String,
        result: Result<MutableList<MediaBrowserCompat.MediaItem>>
    ) {
        if (parentId != ROOT_ID) {
            result.sendResult(mutableListOf())
            return
        }

        val title = currentMetadata?.getString(MediaMetadataCompat.METADATA_KEY_TITLE)
            ?.takeIf { it.isNotBlank() } ?: "Đang phát"
        val artist = currentMetadata?.getString(MediaMetadataCompat.METADATA_KEY_ARTIST)
            ?.takeIf { it.isNotBlank() } ?: "T-Car"

        val now = MediaDescriptionCompat.Builder()
            .setMediaId("media_now")
            .setTitle(title)
            .setSubtitle(artist)
            .build()

        val youtube = MediaDescriptionCompat.Builder()
            .setMediaId("media_home")
            .setTitle("YouTube")
            .setSubtitle("Mở YouTube trong T-Car")
            .build()

        val open = MediaDescriptionCompat.Builder()
            .setMediaId("media_open_carhud")
            .setTitle("Mở T-Car")
            .setSubtitle("Dashboard • YouTube • IPTV")
            .build()

        result.sendResult(
            mutableListOf(
                MediaBrowserCompat.MediaItem(now, MediaBrowserCompat.MediaItem.FLAG_PLAYABLE),
                MediaBrowserCompat.MediaItem(youtube, MediaBrowserCompat.MediaItem.FLAG_PLAYABLE),
                MediaBrowserCompat.MediaItem(open, MediaBrowserCompat.MediaItem.FLAG_PLAYABLE)
            )
        )
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "T-Car Media",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
    }

    private fun updateNotification() {
        val title = currentMetadata?.getString(MediaMetadataCompat.METADATA_KEY_TITLE)
            ?.takeIf { it.isNotBlank() } ?: "T-Car Media"
        val artist = currentMetadata?.getString(MediaMetadataCompat.METADATA_KEY_ARTIST)
            ?.takeIf { it.isNotBlank() } ?: "Media controls"
        val playing = currentState?.state == PlaybackStateCompat.STATE_PLAYING

        val launchIntent = Intent(this, MediaLauncherActivity::class.java)
        val pending = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(com.carhud.media.R.drawable.ic_tcar_media_mono)
            .setContentTitle(title)
            .setContentText(artist)
            .setContentIntent(pending)
            .setOnlyAlertOnce(true)
            .setOngoing(playing)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setStyle(MediaStyle().setMediaSession(mediaSession.sessionToken))
            .build()

        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (playing) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } else {
            stopForeground(STOP_FOREGROUND_DETACH)
            nm.notify(NOTIFICATION_ID, notification)
        }
    }

    override fun onDestroy() {
        mainHandler.removeCallbacksAndMessages(null)
        try { mainController?.unregisterCallback(controllerCallback) } catch (_: Exception) {}
        try { mainBrowser?.disconnect() } catch (_: Exception) {}
        try { mediaSession.release() } catch (_: Exception) {}
        super.onDestroy()
    }
}
'''
write("mediaapp/src/main/java/com/carhud/media/TCarMediaService.kt", service)

print("Split Android Auto media identity into separate com.carhud.media application")
