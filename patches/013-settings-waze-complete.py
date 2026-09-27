from pathlib import Path
import re

ROOT = Path("/tmp/tcar")

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError("Missing expected source block: " + label)
    return text.replace(old, new, 1)

# ===========================================================================
# SETTINGS: every visible setting must drive real behavior.
# ===========================================================================
settings_rel = "app/src/main/java/com/carhud/aaproxy/SettingsActivity.kt"
settings = read(settings_rel)

if 'const val KEY_SYNC_MEDIA_WIDGET = "pref_sync_media_widget"' not in settings:
    settings = replace_once(
        settings,
        '        const val KEY_DEFAULT_TO_DASHBOARD = "default_to_dashboard"\n',
        '        const val KEY_DEFAULT_TO_DASHBOARD = "default_to_dashboard"\n'
        '        const val KEY_SYNC_MEDIA_WIDGET = "pref_sync_media_widget"\n',
        "sync media setting constant"
    )

settings = settings.replace('key = "pref_sync_media_widget"', 'key = KEY_SYNC_MEDIA_WIDGET')

# Expose all toolbar controls that the actual car toolbar can render.
voice_row = '                content.addView(createSwitchRow("Nút Tìm kiếm giọng nói (🎙️)", "Kích hoạt micro nói tên bài hát / kênh", KEY_SHOW_VOICE_SEARCH, true))\n'
if 'Nút Play / Pause (▶/⏸)' not in settings:
    extra_nav = voice_row + (
        '                content.addView(createSwitchRow("Nút Play / Pause (▶/⏸)", "Phát hoặc tạm dừng nội dung đang nghe", KEY_SHOW_PLAY_PAUSE, true))\n'
        '                content.addView(createSwitchRow("Nút Chuyển bài (⏭)", "Chuyển nhanh sang bài/video tiếp theo", KEY_SHOW_NEXT, true))\n'
        '                content.addView(createSwitchRow("Nút Toàn màn hình (⛶)", "Bật/tắt toàn màn hình video", KEY_SHOW_FULLSCREEN, true))\n'
        '                content.addView(createSwitchRow("Nút Cài đặt (⚙)", "Mở nhanh cài đặt T-Car trên điện thoại", KEY_SHOW_SETTINGS, true))\n'
        '                content.addView(createSwitchRow("Hiện thời gian video", "Hiện vị trí / tổng thời lượng khi đang phát", KEY_SHOW_TIME_PILL, true))\n'
    )
    settings = replace_once(settings, voice_row, extra_nav, "toolbar switches")

# Make switch changes trigger behaviors that cannot wait for the next recreation.
old_switch = '''                setOnCheckedChangeListener { _, isChecked ->
                    prefs.edit().putBoolean(key, isChecked).apply()
                }
'''
new_switch = '''                setOnCheckedChangeListener { _, isChecked ->
                    prefs.edit().putBoolean(key, isChecked).apply()
                    when (key) {
                        KEY_SYNC_MEDIA_WIDGET -> CarMediaBrowserService.instance?.applyMediaWidgetSyncPreference()
                        KEY_AUDIO_DUCKING -> if (!isChecked) CarMediaManager.resetNavigationDucking()
                        KEY_BACKGROUND_AUDIO -> {
                            if (!isChecked && !CarMediaManager.isCarConnected) {
                                CarMediaManager.pausePlayback()
                            }
                        }
                    }
                }
'''
settings = replace_once(settings, old_switch, new_switch, "switch behavior hooks")

# Factory reset really resets all user-facing settings, not just the main pref file.
old_reset = '''                                    prefs.edit().clear().apply()
                                    Toast.makeText(this@SettingsActivity, "Đã khôi phục toàn bộ cài đặt gốc", Toast.LENGTH_SHORT).show()
                                    recreate()
'''
new_reset = '''                                    prefs.edit().clear().apply()
                                    getSharedPreferences("waze_hud_settings_prefs", Context.MODE_PRIVATE).edit().clear().apply()
                                    getSharedPreferences("carhud_screen_profile", Context.MODE_PRIVATE).edit().clear().apply()
                                    getSharedPreferences("carhud_web_apps_prefs", Context.MODE_PRIVATE).edit().clear().apply()
                                    try { java.io.File(cacheDir, "iptv_channels.json").delete() } catch (_: Exception) {}
                                    TCarDefaults.apply(this@SettingsActivity)
                                    CarMediaBrowserService.instance?.applyMediaWidgetSyncPreference()
                                    Toast.makeText(this@SettingsActivity, "Đã khôi phục toàn bộ cài đặt gốc", Toast.LENGTH_SHORT).show()
                                    recreate()
'''
settings = replace_once(settings, old_reset, new_reset, "complete factory reset")
write(settings_rel, settings)

# ===========================================================================
# CAR PRESENTATION: toolbar toggles, fullscreen pref, steering-wheel prefs.
# ===========================================================================
car_rel = "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = read(car_rel)

car = car.replace(
    "        val showPlayPause = false\n        val showNext = false\n        val showFullscreen = false\n        val showSettings = false\n",
    "        val showPlayPause = prefs.getBoolean(SettingsActivity.KEY_SHOW_PLAY_PAUSE, true)\n"
    "        val showNext = prefs.getBoolean(SettingsActivity.KEY_SHOW_NEXT, true)\n"
    "        val showFullscreen = prefs.getBoolean(SettingsActivity.KEY_SHOW_FULLSCREEN, true)\n"
    "        val showSettings = prefs.getBoolean(SettingsActivity.KEY_SHOW_SETTINGS, true)\n"
)
car = car.replace(
    "        val showTimePill = true\n",
    "        val showTimePill = prefs.getBoolean(SettingsActivity.KEY_SHOW_TIME_PILL, true)\n"
)

# AndroidVoice must expose the fullscreen preference to YouTube JS.
auto_sig = '            fun isAuto(): Boolean = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)\n'
if 'fun isAutoFullscreenEnabled(): Boolean' not in car:
    car = replace_once(
        car,
        auto_sig,
        auto_sig +
        '\n            @JavascriptInterface\n'
        '            fun isAutoFullscreenEnabled(): Boolean =\n'
        '                prefs.getBoolean(SettingsActivity.KEY_AUTO_FULLSCREEN, true)\n',
        "car fullscreen bridge"
    )

old_voice_key = '''                KeyEvent.KEYCODE_VOICE_ASSIST,
                KeyEvent.KEYCODE_SEARCH -> {
                    startVoiceSearch()
                    return true
                }
'''
new_voice_key = '''                KeyEvent.KEYCODE_VOICE_ASSIST,
                KeyEvent.KEYCODE_SEARCH -> {
                    val steeringPrefs = context.getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
                    if (steeringPrefs.getBoolean(SettingsActivity.KEY_STEERING_VOICE_ENABLED, true)) {
                        startVoiceSearch()
                        return true
                    }
                    return super.dispatchKeyEvent(event)
                }
'''
car = replace_once(car, old_voice_key, new_voice_key, "direct steering voice setting")

old_prev = '''                KeyEvent.KEYCODE_MEDIA_PREVIOUS -> {
                    CarMediaManager.goBack()
                    return true
                }
'''
new_prev = '''                KeyEvent.KEYCODE_MEDIA_PREVIOUS -> {
                    val steeringPrefs = context.getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
                    val action = steeringPrefs.getString(SettingsActivity.KEY_STEERING_PREV_ACTION, "prev")
                    if (action == "voice" && steeringPrefs.getBoolean(SettingsActivity.KEY_STEERING_VOICE_ENABLED, true)) {
                        startVoiceSearch()
                    } else {
                        CarMediaManager.goBack()
                    }
                    return true
                }
'''
car = replace_once(car, old_prev, new_prev, "direct steering prev setting")
write(car_rel, car)

# ===========================================================================
# DEFAULT DASHBOARD: honor only on a fresh Android Auto connection.
# Surface recreation while switching AA apps keeps the user's current view.
# ===========================================================================
screen_rel = "app/src/main/java/com/carhud/aaproxy/CarHudAutoScreen.kt"
screen = read(screen_rel)

old_pres = '''            val persistentWeb = CarMediaManager.getPersistentCarWebView(carContext)
            val pres = CarPresentation(carContext, vd.display, persistentWeb)
            pres.show()
            presentation = pres

            CarMediaManager.setCarConnectionState(true)
'''
new_pres = '''            val persistentWeb = CarMediaManager.getPersistentCarWebView(carContext)

            // Apply the startup-view preference only once per physical AA connection.
            // Recreating a headless projection surface must preserve the current view.
            if (!CarMediaManager.isCarConnected) {
                val settingsPrefs = carContext.getSharedPreferences(SettingsActivity.PREFS, CarContext.MODE_PRIVATE)
                val defaultDashboard = settingsPrefs.getBoolean(SettingsActivity.KEY_DEFAULT_TO_DASHBOARD, true)
                CarMediaManager.isWebShowingFullscreen = !defaultDashboard
                CarMediaManager.isEmbeddedAppShowing = defaultDashboard
            }

            val pres = CarPresentation(carContext, vd.display, persistentWeb)
            pres.show()
            presentation = pres

            CarMediaManager.setCarConnectionState(true)
'''
screen = replace_once(screen, old_pres, new_pres, "default dashboard on fresh connection")

# Background-audio OFF now pauses when the AA projection goes to the background.
surface_anchor = '''                carSurface = null
                virtualDisplay?.setSurface(null)
'''
surface_new = '''                val settingsPrefs = carContext.getSharedPreferences(SettingsActivity.PREFS, CarContext.MODE_PRIVATE)
                if (!settingsPrefs.getBoolean(SettingsActivity.KEY_BACKGROUND_AUDIO, true)) {
                    CarMediaManager.pausePlayback()
                }
                carSurface = null
                virtualDisplay?.setSurface(null)
'''
screen = replace_once(screen, surface_anchor, surface_new, "background audio AA surface")
write(screen_rel, screen)

# ===========================================================================
# MAIN ACTIVITY + MEDIA MANAGER: background audio and navigation ducking.
# ===========================================================================
main_rel = "app/src/main/java/com/carhud/aaproxy/MainActivity.kt"
main = read(main_rel)

old_pause = '''        if (prefs.getBoolean(SettingsActivity.KEY_BACKGROUND_AUDIO, true) && ::web.isInitialized) {
            web.onResume()
            web.resumeTimers()
        }
'''
new_pause = '''        if (::web.isInitialized) {
            if (prefs.getBoolean(SettingsActivity.KEY_BACKGROUND_AUDIO, true)) {
                web.onResume()
                web.resumeTimers()
            } else if (!CarMediaManager.isCarConnected) {
                web.onPause()
                web.pauseTimers()
                CarMediaManager.pausePlayback()
            }
        }
'''
# onPause + onStop both use the same source block.
if main.count(old_pause) < 2:
    raise RuntimeError("Expected two MainActivity background blocks")
main = main.replace(old_pause, new_pause, 2)
write(main_rel, main)

manager_rel = "app/src/main/java/com/carhud/aaproxy/CarMediaManager.kt"
manager = read(manager_rel)

old_disconnect = '''                } else {
                    phoneWebView?.onResume()
                    phoneWebView?.resumeTimers()
                }
'''
new_disconnect = '''                } else {
                    val phone = phoneWebView
                    val backgroundEnabled = phone?.context
                        ?.getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
                        ?.getBoolean(SettingsActivity.KEY_BACKGROUND_AUDIO, true) ?: true
                    if (backgroundEnabled) {
                        phone?.onResume()
                        phone?.resumeTimers()
                    } else {
                        phone?.onPause()
                        phone?.pauseTimers()
                    }
                }
'''
manager = replace_once(manager, old_disconnect, new_disconnect, "phone background audio behavior")

# Add reference-counted media ducking used by Waze alert tone/TTS.
duck_anchor = '''    private var audioManager: CarAudioManager? = null

'''
if "fun beginNavigationDucking()" not in manager:
    duck_code = '''    private var audioManager: CarAudioManager? = null
    private var navigationDuckCount = 0

    fun beginNavigationDucking() {
        mainHandler.post {
            val web = getActiveWebView() ?: return@post
            val enabled = web.context
                .getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
                .getBoolean(SettingsActivity.KEY_AUDIO_DUCKING, true)
            if (!enabled) {
                navigationDuckCount = 0
                YouTubePlayerHelper.setDuckingVolume(web, 1.0f)
                return@post
            }
            navigationDuckCount += 1
            YouTubePlayerHelper.setDuckingVolume(web, 0.35f)
        }
    }

    fun endNavigationDucking() {
        mainHandler.post {
            navigationDuckCount = (navigationDuckCount - 1).coerceAtLeast(0)
            if (navigationDuckCount == 0) {
                getActiveWebView()?.let { YouTubePlayerHelper.setDuckingVolume(it, 1.0f) }
            }
        }
    }

    fun resetNavigationDucking() {
        mainHandler.post {
            navigationDuckCount = 0
            getActiveWebView()?.let { YouTubePlayerHelper.setDuckingVolume(it, 1.0f) }
        }
    }

'''
    manager = replace_once(manager, duck_anchor, duck_code, "navigation duck manager")
write(manager_rel, manager)

# ===========================================================================
# MEDIA WIDGET SYNC: keep steering/media session controls, but honor metadata sync.
# ===========================================================================
service_rel = "app/src/main/java/com/carhud/aaproxy/CarMediaBrowserService.kt"
service = read(service_rel)

field_anchor = '''    private var currentDurationSec = 0

'''
if "fun applyMediaWidgetSyncPreference()" not in service:
    widget_code = '''    private var currentDurationSec = 0

    private fun isMediaWidgetSyncEnabled(): Boolean =
        getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
            .getBoolean(SettingsActivity.KEY_SYNC_MEDIA_WIDGET, true)

    fun applyMediaWidgetSyncPreference() {
        val session = mediaSession ?: return
        try {
            val state = if (isPlayingState) PlaybackStateCompat.STATE_PLAYING else PlaybackStateCompat.STATE_PAUSED
            session.setPlaybackState(buildPlaybackState(state, currentPositionSec * 1000L).build())
            if (isMediaWidgetSyncEnabled()) {
                session.setMetadata(buildMetadata(currentTitle, currentArtist, currentDurationSec * 1000L).build())
            } else {
                session.setMetadata(
                    MediaMetadataCompat.Builder()
                        .putString(MediaMetadataCompat.METADATA_KEY_TITLE, "T-Car")
                        .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, "Media controls")
                        .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_TITLE, "T-Car")
                        .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_SUBTITLE, "Media controls")
                        .build()
                )
            }
            val notifTitle = if (isMediaWidgetSyncEnabled()) currentTitle else "T-Car"
            val notifArtist = if (isMediaWidgetSyncEnabled()) currentArtist else "Media controls"
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(NOTIFICATION_ID, buildNotification(isPlayingState, notifTitle, notifArtist))
            notifyChildrenChanged(ROOT_ID)
        } catch (_: Exception) {
        }
    }

'''
    service = replace_once(service, field_anchor, widget_code, "media widget sync helper")

# Artwork: retain internal cache but don't push dynamic metadata when disabled.
art_anchor = '''        val session = mediaSession ?: return
        try {
            val metaBuilder = buildMetadata(currentTitle, currentArtist, currentDurationSec * 1000L)
'''
art_new = '''        val session = mediaSession ?: return
        if (!isMediaWidgetSyncEnabled()) {
            applyMediaWidgetSyncPreference()
            return
        }
        try {
            val metaBuilder = buildMetadata(currentTitle, currentArtist, currentDurationSec * 1000L)
'''
service = replace_once(service, art_anchor, art_new, "artwork widget sync")

progress_anchor = '''        val session = mediaSession ?: return
        try {
            val shouldSync = durationChanged || lastReportedSec < 0 || Math.abs(curSec - lastReportedSec) >= 5
'''
progress_new = '''        val session = mediaSession ?: return
        if (!isMediaWidgetSyncEnabled()) {
            return
        }
        try {
            val shouldSync = durationChanged || lastReportedSec < 0 || Math.abs(curSec - lastReportedSec) >= 5
'''
service = replace_once(service, progress_anchor, progress_new, "progress widget sync")

state_anchor = '''        val session = mediaSession ?: return

        try {
            val stateBuilder = buildPlaybackState(state, currentPositionSec * 1000L)
'''
state_new = '''        val session = mediaSession ?: return

        if (!isMediaWidgetSyncEnabled()) {
            try {
                session.setPlaybackState(buildPlaybackState(state, currentPositionSec * 1000L).build())
                session.setMetadata(
                    MediaMetadataCompat.Builder()
                        .putString(MediaMetadataCompat.METADATA_KEY_TITLE, "T-Car")
                        .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, "Media controls")
                        .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_TITLE, "T-Car")
                        .putString(MediaMetadataCompat.METADATA_KEY_DISPLAY_SUBTITLE, "Media controls")
                        .build()
                )
                val notif = buildNotification(isPlayingState, "T-Car", "Media controls")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    startForeground(NOTIFICATION_ID, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK)
                } else {
                    startForeground(NOTIFICATION_ID, notif)
                }
            } catch (_: Exception) {}
            return
        }

        try {
            val stateBuilder = buildPlaybackState(state, currentPositionSec * 1000L)
'''
service = replace_once(service, state_anchor, state_new, "state widget sync")

# Direct media-button voice behavior also respects the master steering-voice toggle.
old_prev_service = '''                                        if (action == "voice") {
                                            CarMediaManager.startGlobalVoiceSearch(this@CarMediaBrowserService)
                                        } else {
                                            CarMediaManager.goBack()
                                        }
'''
new_prev_service = '''                                        if (action == "voice" && prefs.getBoolean(SettingsActivity.KEY_STEERING_VOICE_ENABLED, true)) {
                                            CarMediaManager.startGlobalVoiceSearch(this@CarMediaBrowserService)
                                        } else {
                                            CarMediaManager.goBack()
                                        }
'''
# There are two previous-action paths (media event + callback).
service = service.replace(old_prev_service, new_prev_service)

write(service_rel, service)

# ===========================================================================
# AUTO FULLSCREEN: YouTube watch pages obey the switch instead of forcing CSS.
# ===========================================================================
yt_rel = "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = read(yt_rel)

old_force = '''                if (isWatch) {
                    if (!document.documentElement.classList.contains('carhud-force-fullscreen')) {
                        document.documentElement.classList.add('carhud-force-fullscreen');
                    }
                    if (!document.body.classList.contains('carhud-force-fullscreen')) {
                        document.body.classList.add('carhud-force-fullscreen');
                    }

                    var currentUrl = currentHref;
'''
new_force = '''                if (isWatch) {
                    var autoFullscreenEnabled = true;
                    try {
                        if (window.AndroidVoice && window.AndroidVoice.isAutoFullscreenEnabled) {
                            autoFullscreenEnabled = !!window.AndroidVoice.isAutoFullscreenEnabled();
                        }
                    } catch(e) {}

                    if (autoFullscreenEnabled) {
                        if (!document.documentElement.classList.contains('carhud-force-fullscreen')) {
                            document.documentElement.classList.add('carhud-force-fullscreen');
                        }
                        if (!document.body.classList.contains('carhud-force-fullscreen')) {
                            document.body.classList.add('carhud-force-fullscreen');
                        }
                    } else {
                        document.documentElement.classList.remove('carhud-force-fullscreen');
                        document.body.classList.remove('carhud-force-fullscreen');
                    }

                    var currentUrl = currentHref;
'''
yt = replace_once(yt, old_force, new_force, "auto fullscreen JS")
write(yt_rel, yt)

# ===========================================================================
# LANE GUIDANCE: the HUD switch now actually shows/hides Waze lane data.
# ===========================================================================
hud_rel = "app/src/main/java/com/carhud/aaproxy/VietmapHudOverlay.kt"
hud = read(hud_rel)

old_road = '''        roadNameText?.text = road
        roadNameText?.visibility = if (road.isBlank()) GONE else VISIBLE
'''
new_road = '''        val laneGuidance = if (isPreviewMode || WazeHudManager.isLaneGuidanceEnabled(context)) {
            data.laneGuidance
                ?.replace("[", "")
                ?.replace("]", "")
                ?.replace(34.toChar().toString(), "")
                ?.trim()
                ?.takeIf { it.isNotBlank() }
        } else null

        val roadAndLane = buildList {
            if (road.isNotBlank()) add(road)
            if (!laneGuidance.isNullOrBlank()) add("Làn: $laneGuidance")
        }.joinToString(" • ")

        roadNameText?.text = roadAndLane
        roadNameText?.visibility = if (roadAndLane.isBlank()) GONE else VISIBLE
'''
hud = replace_once(hud, old_road, new_road, "lane guidance visibility")
write(hud_rel, hud)

# ===========================================================================
# WAZE ALERT PIPELINE: accept richer real Waze payloads and keep them fresh.
# ===========================================================================
waze_rel = "app/src/main/java/com/carhud/aaproxy/WazeHlpWebSocketManager.kt"
waze = read(waze_rel)

if "private fun firstObject(" not in waze:
    array_helper = '''    private fun firstArray(json: JSONObject, vararg keys: String): JSONArray? {
        for (key in keys) {
            val arr = json.optJSONArray(key)
            if (arr != null) return arr
        }
        return null
    }

'''
    object_helper = array_helper + '''    private fun firstObject(json: JSONObject, vararg keys: String): JSONObject? {
        for (key in keys) {
            val obj = json.optJSONObject(key)
            if (obj != null) return obj
        }
        return null
    }

'''
    waze = replace_once(waze, array_helper, object_helper, "Waze object helper")

# Alert distance must understand "250 m" / "1.2 km", not just bare integers.
waze = re.sub(
    r'var alertDistanceMeters = firstInt\(json, "alertDistanceMeters", "alert_distance_meters", "alertDistance", "alert_distance", "alrD", "alrDst", "alertDist"\)\s*\n\s*\.takeIf \{ it >= 0 \}',
    'var alertDistanceMeters = firstDistanceMeters(json, "alertDistanceMeters", "alert_distance_meters", "alertDistance", "alert_distance", "alrD", "alrDst", "alertDist", "reportDistance", "report_distance", "aheadDistance", "ahead_distance")\\n                ?.takeIf { it >= 0 }',
    waze,
    count=1
)

alert_road_anchor = '''            var alertRoad: String? = null

'''
if "val alertObject = firstObject(" not in waze:
    nested_alert = '''            var alertRoad: String? = null

            // Real Waze/Waze-Mod builds may send the warning as a nested report
            // object instead of flat alr/alrD fields. Prefer the actual Waze
            // payload and preserve its subtype/title/distance.
            val alertObject = firstObject(
                json,
                "alertData", "alert_data", "warningData", "warning_data",
                "report", "hazardData", "hazard_data", "event"
            ) ?: (json.opt("alert") as? JSONObject)

            if (alertObject != null) {
                val objectCode = firstInt(alertObject, "code", "alr", "alertCode", "alert_code", "typeCode", "type_code") ?: 0
                val objectType = firstString(
                    alertObject,
                    "type", "kind", "category", "reportType", "report_type",
                    "subtype", "subType", "reportSubtype", "report_subtype", "hazardType", "hazard_type"
                )
                val objectTitle = firstString(
                    alertObject,
                    "title", "label", "description", "text", "message",
                    "warning", "alertTitle", "alert_title"
                )
                val objectDistance = firstDistanceMeters(
                    alertObject,
                    "distance", "distanceMeters", "distance_meters", "dist", "dst",
                    "alertDistance", "alert_distance", "reportDistance", "report_distance",
                    "aheadDistance", "ahead_distance"
                )?.takeIf { it >= 0 }
                val objectRoad = firstString(alertObject, "road", "street", "roadName", "road_name")

                if (alertCode <= 0 && objectCode > 0) alertCode = objectCode
                if (rawAlertStr.isNullOrBlank() || rawAlertStr?.trim()?.startsWith("{") == true) rawAlertStr = objectType
                if (rawCandidate.isNullOrBlank()) rawCandidate = objectTitle
                if (alertDistanceMeters == null) alertDistanceMeters = objectDistance
                if (alertRoad.isNullOrBlank()) alertRoad = objectRoad
            }

'''
    waze = replace_once(waze, alert_road_anchor, nested_alert, "nested Waze alert object")

waze = waze.replace(
    'val alertArray = firstArray(json, "alerts", "warnings", "alertList", "alert_list", "alrs")',
    'val alertArray = firstArray(json, "alerts", "warnings", "alertList", "alert_list", "alrs", "reports", "hazards", "events", "upcomingAlerts", "upcoming_alerts")'
)

old_item = '''                    val itemTitle = firstString(item, "title", "label", "description", "text", "alert", "warning")
                    val itemType = firstString(item, "type", "kind", "category")
                    val itemDist = firstInt(item, "distance", "distanceMeters", "distance_meters", "dist", "dst")?.takeIf { it >= 0 }
                    val itemRoad = firstString(item, "road", "street", "roadName", "road_name")
'''
new_item = '''                    val itemTitle = firstString(item, "title", "label", "description", "text", "message", "alert", "warning")
                    val itemType = firstString(item, "type", "kind", "category", "reportType", "report_type")
                    val itemSubtype = firstString(item, "subtype", "subType", "reportSubtype", "report_subtype", "hazardType", "hazard_type")
                    val itemIcon = firstString(item, "icon", "iconName", "icon_name")
                    val itemDist = firstDistanceMeters(item, "distance", "distanceMeters", "distance_meters", "dist", "dst", "reportDistance", "report_distance", "aheadDistance", "ahead_distance")?.takeIf { it >= 0 }
                    val itemRoad = firstString(item, "road", "street", "roadName", "road_name")
'''
waze = replace_once(waze, old_item, new_item, "Waze alert array fields")
waze = waze.replace(
    'else -> mapWarningType(itemTitle, itemType)',
    'else -> mapWarningType(itemTitle, itemType, itemSubtype, itemIcon)'
)

# An explicitly empty Waze alerts list is a real clear signal.
old_clear = '''            val isClearExplicit = clearFlag || explicitClearText ||
                (alertCodePresent && alertCode == 0 && !alertTextFieldPresent && alertArray == null)
'''
new_clear = '''            val emptyAlertListClear = alertArray != null && alertArray.length() == 0 &&
                hasAny(json, "alerts", "warnings", "alertList", "alert_list", "alrs", "reports", "hazards", "events", "upcomingAlerts", "upcoming_alerts")
            val isClearExplicit = clearFlag || explicitClearText || emptyAlertListClear ||
                (alertCodePresent && alertCode == 0 && !alertTextFieldPresent && alertArray == null)
'''
waze = replace_once(waze, old_clear, new_clear, "empty Waze alert list clear")
write(waze_rel, waze)

# Waze notifications are a fallback real-Waze source when HLP doesn't expose an
# alert. Classify all Waze warning text, not only camera keywords.
notif_rel = "app/src/main/java/com/carhud/aaproxy/VietmapNotificationListenerService.kt"
notif = read(notif_rel)

old_classify = '''        parsedWarningType = VietmapIconClassifier.classifyFromText(combined)
        if (parsedWarningType != VietmapWarningType.NONE) {
            parsedAlertTitle = parsedWarningType.label
        } else {
            val lower = combined.lowercase()
            if (lower.contains("bắn tốc độ") || lower.contains("camera") || lower.contains("phạt nguội")) {
                parsedWarningType = VietmapWarningType.SPEED_CAMERA
                parsedAlertTitle = "Camera đo tốc độ"
            }
        }
'''
new_classify = '''        parsedWarningType = VietmapIconClassifier.classifyFromText(combined)
        if (parsedWarningType == VietmapWarningType.NONE) {
            parsedWarningType = WazeHlpWebSocketManager.mapWarningType(combined)
        }
        if (parsedWarningType != VietmapWarningType.NONE) {
            val candidates = listOf(title, text, bigText, subText, infoText, tickerText)
                .map { it.trim() }
                .filter { it.isNotBlank() && !isIgnoredNotificationText(it) }
            parsedAlertTitle = candidates.firstOrNull {
                WazeHlpWebSocketManager.mapWarningType(it) == parsedWarningType ||
                    VietmapIconClassifier.classifyFromText(it) == parsedWarningType
            } ?: parsedWarningType.label
        }
'''
notif = replace_once(notif, old_classify, new_classify, "Waze notification full classification")
write(notif_rel, notif)

# ===========================================================================
# TTS/TONE: Audio Ducking setting now lowers media while Waze alerts sound.
# ===========================================================================
tts_rel = "app/src/main/java/com/carhud/aaproxy/CarTtsManager.kt"
tts = read(tts_rel)

if "import android.speech.tts.UtteranceProgressListener" not in tts:
    tts = tts.replace(
        "import android.speech.tts.TextToSpeech\n",
        "import android.speech.tts.TextToSpeech\nimport android.speech.tts.UtteranceProgressListener\n",
        1
    )

# Tone engine comes from patch 008. Duck exactly for the tone lifetime.
play_line = '''                track.play()
                val totalDurationMs = segments.sumOf { it.second + it.third }.toLong()
'''
if "CarMediaManager.beginNavigationDucking()" not in tts:
    tts = replace_once(
        tts,
        play_line,
        '''                CarMediaManager.beginNavigationDucking()
                track.play()
                val totalDurationMs = segments.sumOf { it.second + it.third }.toLong()
''',
        "tone duck start"
    )
    final_release = '''                    if (alertAudioTrack === track) {
                        alertAudioTrack = null
                    }
'''
    tts = replace_once(
        tts,
        final_release,
        '''                    if (alertAudioTrack === track) {
                        alertAudioTrack = null
                    }
                    CarMediaManager.endNavigationDucking()
''',
        "tone duck end"
    )

# TTS listener restores ducking exactly when speech finishes/errors.
if "setOnUtteranceProgressListener" not in tts:
    init_marker = '''            isInitialized = true
            pendingSpeakText?.let {
'''
    listener_code = '''            try {
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        if (utteranceId?.startsWith("alert_") == true) {
                            CarMediaManager.beginNavigationDucking()
                        }
                    }

                    override fun onDone(utteranceId: String?) {
                        if (utteranceId?.startsWith("alert_") == true) {
                            CarMediaManager.endNavigationDucking()
                        }
                    }

                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {
                        if (utteranceId?.startsWith("alert_") == true) {
                            CarMediaManager.endNavigationDucking()
                        }
                    }
                })
            } catch (_: Exception) {}

            isInitialized = true
            pendingSpeakText?.let {
'''
    tts = replace_once(tts, init_marker, listener_code, "TTS duck listener")

# Always restore media if TTS is shut down.
shutdown_anchor = '''        } finally {
            tts = null
'''
shutdown_new = '''        } finally {
            CarMediaManager.resetNavigationDucking()
            tts = null
'''
tts = replace_once(tts, shutdown_anchor, shutdown_new, "TTS duck reset")
write(tts_rel, tts)

print("Applied v0.8.162 full settings wiring + real Waze alert pipeline")
