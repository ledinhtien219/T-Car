from pathlib import Path
import os, shutil

ROOT = Path("/tmp/tcar")
WORKSPACE = Path(os.environ["GITHUB_WORKSPACE"])

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError("Missing expected source block: " + label)
    return text.replace(old, new, 1)

# Bundle the approved IPTV playlist as the built-in default.
playlist_src = WORKSPACE / "patches/default_channels.m3u"
playlist_dst = ROOT / "app/src/main/assets/default_channels.m3u"
playlist_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(playlist_src, playlist_dst)

# Make the bundled playlist the actual default source.
iptv_path = ROOT / "app/src/main/java/com/carhud/aaproxy/IptvModel.kt"
iptv = iptv_path.read_text(encoding="utf-8")
iptv = replace_once(
    iptv,
    '    const val DEFAULT_IPTV_URL = "https://raw.githubusercontent.com/khanh71/All-In-One-IPTV/main/http-iptv.m3u"\n',
    '    const val DEFAULT_IPTV_URL = "asset://default_channels.m3u"\n',
    "default IPTV URL"
)
old_fetch = '''                val targetUrl = getM3uUrl(context)
                try {
                    val url = URL(targetUrl)
                    val conn = (url.openConnection() as HttpURLConnection).apply {
                        connectTimeout = 8000
                        readTimeout = 12000
                        setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                        instanceFollowRedirects = true
                    }
                    val res = BufferedReader(InputStreamReader(conn.inputStream, "UTF-8")).use { parseM3uStream(it) }
                    if (res.isNotEmpty()) res else parseLocalOrDefault(context)
                } catch (ex: Exception) {
                    Log.w(TAG, "Network fetch failed, fallback to local/asset: ${ex.message}")
                    parseLocalOrDefault(context)
                }
'''
new_fetch = '''                val targetUrl = getM3uUrl(context)
                if (targetUrl == DEFAULT_IPTV_URL) {
                    parseLocalOrDefault(context)
                } else {
                    try {
                        val url = URL(targetUrl)
                        val conn = (url.openConnection() as HttpURLConnection).apply {
                            connectTimeout = 8000
                            readTimeout = 12000
                            setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
                            instanceFollowRedirects = true
                        }
                        val res = BufferedReader(InputStreamReader(conn.inputStream, "UTF-8")).use { parseM3uStream(it) }
                        if (res.isNotEmpty()) res else parseLocalOrDefault(context)
                    } catch (ex: Exception) {
                        Log.w(TAG, "Network fetch failed, fallback to local/asset: ${ex.message}")
                        parseLocalOrDefault(context)
                    }
                }
'''
iptv = replace_once(iptv, old_fetch, new_fetch, "IPTV default fetch")
iptv_path.write_text(iptv, encoding="utf-8")

# Dark mode is the default until the user explicitly changes it.
settings_path = ROOT / "app/src/main/java/com/carhud/aaproxy/SettingsActivity.kt"
settings = settings_path.read_text(encoding="utf-8")
settings = settings.replace(
    "prefs.getString(KEY_THEME_MODE, THEME_AUTO) ?: THEME_AUTO",
    "prefs.getString(KEY_THEME_MODE, THEME_NIGHT) ?: THEME_NIGHT"
)
settings = settings.replace(
    'prefs.getBoolean("settings_dark_mode", false)',
    'prefs.getBoolean("settings_dark_mode", true)'
)
settings = replace_once(
    settings,
    'content.addView(createSwitchRow("Nút Phóng to / Thu nhỏ (⤢)", "Chuyển nhanh TV / Toàn màn hình (Nút số 2)", KEY_SHOW_TV, false))',
    'content.addView(createSwitchRow("Nút Phóng to / Thu nhỏ (⤢)", "Chuyển nhanh TV / Toàn màn hình (Nút số 2)", KEY_SHOW_TV, true))',
    "TV navigation switch default"
)
voice_row = 'content.addView(createSwitchRow("Nút Tìm kiếm giọng nói (🎙️)", "Kích hoạt micro nói tên bài hát / kênh", KEY_SHOW_VOICE_SEARCH, true))'
if "KEY_SHOW_KEYBOARD_SEARCH, true))" not in settings:
    settings = replace_once(
        settings,
        voice_row,
        'content.addView(createSwitchRow("Nút Tìm kiếm bàn phím (🔎)", "Mở ô tìm kiếm trực tiếp trên màn hình xe", KEY_SHOW_KEYBOARD_SEARCH, true))\n                ' + voice_row,
        "keyboard navigation switch row"
    )
settings = replace_once(
    settings,
    "        super.onCreate(savedInstanceState)\n        val exitFilter = IntentFilter(CarAppShutdownManager.ACTION_FULL_EXIT)\n",
    "        super.onCreate(savedInstanceState)\n        TCarDefaults.apply(this)\n        val exitFilter = IntentFilter(CarAppShutdownManager.ACTION_FULL_EXIT)\n",
    "SettingsActivity defaults init"
)
settings_path.write_text(settings, encoding="utf-8")

# HUD warning bubble starts locked.
hud_path = ROOT / "app/src/main/java/com/carhud/aaproxy/WazeHudManager.kt"
hud = hud_path.read_text(encoding="utf-8")
hud = hud.replace(
    'const val KEY_HUD_LOCKED = "key_hud_is_locked" // default false (allows drag until locked)',
    'const val KEY_HUD_LOCKED = "key_hud_is_locked" // default true (locked until user unlocks)'
)
hud = replace_once(
    hud,
    "return getPrefs(context).getBoolean(KEY_HUD_LOCKED, false)",
    "return getPrefs(context).getBoolean(KEY_HUD_LOCKED, true)",
    "HUD lock default"
)
hud_path.write_text(hud, encoding="utf-8")

# Car navigation switches: default ON.
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")
car = car.replace(
    "prefs.getString(SettingsActivity.KEY_THEME_MODE, SettingsActivity.THEME_AUTO) ?: SettingsActivity.THEME_AUTO",
    "prefs.getString(SettingsActivity.KEY_THEME_MODE, SettingsActivity.THEME_NIGHT) ?: SettingsActivity.THEME_NIGHT"
)
car = replace_once(
    car,
    "val showTv = prefs.getBoolean(SettingsActivity.KEY_SHOW_TV, false)",
    "val showTv = prefs.getBoolean(SettingsActivity.KEY_SHOW_TV, true)",
    "car TV toolbar default"
)
car = replace_once(
    car,
    "val showSearch = prefs.getBoolean(SettingsActivity.KEY_SHOW_KEYBOARD_SEARCH, false)",
    "val showSearch = prefs.getBoolean(SettingsActivity.KEY_SHOW_KEYBOARD_SEARCH, true)",
    "car search toolbar default"
)
car = replace_once(
    car,
    "        super.onCreate(savedInstanceState)\n        CarMediaManager.activeVoiceManager = voiceManager\n",
    "        super.onCreate(savedInstanceState)\n        TCarDefaults.apply(context)\n        CarMediaManager.activeVoiceManager = voiceManager\n",
    "CarPresentation defaults init"
)
car_path.write_text(car, encoding="utf-8")

# Apply migration before MainActivity reads theme/navigation prefs.
main_path = ROOT / "app/src/main/java/com/carhud/aaproxy/MainActivity.kt"
main = main_path.read_text(encoding="utf-8")
main = replace_once(
    main,
    "        super.onCreate(savedInstanceState)\n        AppCrashHandler.init(this)\n",
    "        super.onCreate(savedInstanceState)\n        TCarDefaults.apply(this)\n        AppCrashHandler.init(this)\n",
    "MainActivity defaults init"
)
main_path.write_text(main, encoding="utf-8")

# One-time migration so upgrades also receive these defaults once.
defaults_path = ROOT / "app/src/main/java/com/carhud/aaproxy/TCarDefaults.kt"
defaults_path.write_text(r'''package com.carhud.aaproxy

import android.content.Context
import java.io.File

object TCarDefaults {
    private const val MIGRATION_KEY = "defaults_0_8_158_applied"
    private const val OLD_DEFAULT_IPTV_URL = "https://raw.githubusercontent.com/khanh71/All-In-One-IPTV/main/http-iptv.m3u"

    fun apply(context: Context) {
        val appContext = context.applicationContext ?: context
        val prefs = appContext.getSharedPreferences(SettingsActivity.PREFS, Context.MODE_PRIVATE)
        if (prefs.getBoolean(MIGRATION_KEY, false)) return

        val currentIptvUrl = prefs.getString(IptvManager.PREF_IPTV_URL, null)
        val usingLocalIptv = prefs.getBoolean(IptvManager.PREF_IPTV_IS_FILE, false)

        val editor = prefs.edit()
            .putString(SettingsActivity.KEY_THEME_MODE, SettingsActivity.THEME_NIGHT)
            .putBoolean("settings_dark_mode", true)
            .putBoolean(SettingsActivity.KEY_SHOW_BACK, true)
            .putBoolean(SettingsActivity.KEY_SHOW_HOME, true)
            .putBoolean(SettingsActivity.KEY_SHOW_TV, true)
            .putBoolean(SettingsActivity.KEY_SHOW_DAY_NIGHT, true)
            .putBoolean(SettingsActivity.KEY_SHOW_KEYBOARD_SEARCH, true)
            .putBoolean(SettingsActivity.KEY_SHOW_VOICE_SEARCH, true)
            .putBoolean(SettingsActivity.KEY_SHOW_TIME_PILL, true)
            .putBoolean(MIGRATION_KEY, true)

        if (!usingLocalIptv && (currentIptvUrl.isNullOrBlank() || currentIptvUrl == OLD_DEFAULT_IPTV_URL)) {
            editor.remove(IptvManager.PREF_IPTV_URL)
            try { File(appContext.cacheDir, "iptv_channels.json").delete() } catch (_: Exception) {}
        }

        editor.apply()
        WazeHudManager.setLocked(appContext, true)
    }
}
''', encoding="utf-8")

print("Applied v0.8.158 defaults: bundled IPTV, night mode, locked HUD, nav switches ON")
