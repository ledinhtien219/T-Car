from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

manager_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarScreenProfileManager.kt"
manager_path.write_text(r'''package com.carhud.aaproxy

import android.content.Context
import kotlin.math.roundToInt

object CarScreenProfileManager {
    private const val PREFS = "carhud_screen_profile"
    private const val KEY_WIDTH = "last_width_px"
    private const val KEY_HEIGHT = "last_height_px"
    private const val KEY_DPI = "last_density_dpi"
    private const val KEY_PROFILE = "last_profile"
    private const val KEY_SEEN_AT = "last_seen_at"

    enum class Profile(
        val key: String,
        val label: String,
        val toolbarScale: Float
    ) {
        COMPACT("compact", "Compact", 0.82f),
        MEDIUM("medium", "Medium", 0.92f),
        LARGE("large", "Large", 1.00f),
        XL("xl", "XL", 1.08f),
        PORTRAIT("portrait", "Portrait", 0.90f),
        ULTRAWIDE("ultrawide", "Ultrawide", 0.94f);

        companion object {
            fun fromKey(key: String?): Profile? = values().firstOrNull { it.key == key }
        }
    }

    data class ScreenInfo(
        val widthPx: Int,
        val heightPx: Int,
        val densityDpi: Int,
        val widthDp: Int,
        val heightDp: Int,
        val aspectRatio: Float,
        val profile: Profile,
        val seenAt: Long = System.currentTimeMillis()
    ) {
        val isPortrait: Boolean get() = profile == Profile.PORTRAIT
        val isUltrawide: Boolean get() = profile == Profile.ULTRAWIDE

        fun detailText(): String =
            "${widthPx} × ${heightPx}px • ${densityDpi} DPI • aspect ${"%.2f".format(aspectRatio)} • ${widthDp} × ${heightDp}dp"
    }

    fun detect(widthPx: Int, heightPx: Int, densityDpi: Int): ScreenInfo {
        val w = widthPx.coerceAtLeast(1)
        val h = heightPx.coerceAtLeast(1)
        val dpi = densityDpi.takeIf { it in 80..1000 } ?: 160
        val aspect = w.toFloat() / h.toFloat()
        val widthDp = (w * 160f / dpi.toFloat()).roundToInt().coerceAtLeast(1)
        val heightDp = (h * 160f / dpi.toFloat()).roundToInt().coerceAtLeast(1)
        val shortDp = minOf(widthDp, heightDp)

        val profile = when {
            aspect < 0.95f -> Profile.PORTRAIT
            aspect >= 1.85f -> Profile.ULTRAWIDE
            shortDp < 340 -> Profile.COMPACT
            shortDp < 460 -> Profile.MEDIUM
            shortDp < 600 -> Profile.LARGE
            else -> Profile.XL
        }

        return ScreenInfo(
            widthPx = w,
            heightPx = h,
            densityDpi = dpi,
            widthDp = widthDp,
            heightDp = heightDp,
            aspectRatio = aspect,
            profile = profile
        )
    }

    fun detectAndSave(context: Context, widthPx: Int, heightPx: Int, densityDpi: Int): ScreenInfo {
        val info = detect(widthPx, heightPx, densityDpi)
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_WIDTH, info.widthPx)
            .putInt(KEY_HEIGHT, info.heightPx)
            .putInt(KEY_DPI, info.densityDpi)
            .putString(KEY_PROFILE, info.profile.key)
            .putLong(KEY_SEEN_AT, info.seenAt)
            .apply()
        return info
    }

    fun lastInfo(context: Context): ScreenInfo? {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val width = prefs.getInt(KEY_WIDTH, 0)
        val height = prefs.getInt(KEY_HEIGHT, 0)
        val dpi = prefs.getInt(KEY_DPI, 0)
        if (width <= 0 || height <= 0) return null

        val detected = detect(width, height, dpi)
        val savedProfile = Profile.fromKey(prefs.getString(KEY_PROFILE, null)) ?: detected.profile
        return detected.copy(
            profile = savedProfile,
            seenAt = prefs.getLong(KEY_SEEN_AT, 0L)
        )
    }
}
''', encoding="utf-8")

car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")

car = replace_once(
    car,
    '''    private var carDpi = 160
    private var phoneDpi = 160f
    private var aspectRatio = 1.777f
''',
    '''    private var carDpi = 160
    private var phoneDpi = 160f
    private var aspectRatio = 1.777f
    private var detectedScreenProfile = CarScreenProfileManager.Profile.MEDIUM
    private var autoScreenProfileEnabled = true
''',
    "CarPresentation screen profile fields"
)

old_metrics = '''        // Auto-detect car screen metrics and form-factor
        val metrics = android.util.DisplayMetrics()
        display.getRealMetrics(metrics)
        carWidth = if (metrics.widthPixels > 0) metrics.widthPixels else 800
        carHeight = if (metrics.heightPixels > 0) metrics.heightPixels else 480
        carDpi = if (metrics.densityDpi > 0) metrics.densityDpi else 160
        aspectRatio = if (carHeight > 0) carWidth.toFloat() / carHeight.toFloat() else 1.777f

        isUltrawide = (aspectRatio >= 1.85f)
        isPortrait = (aspectRatio < 0.95f)
'''
new_metrics = '''        // Read the real Android Auto projection surface and classify it by
        // usable viewport, not by car model name. This covers VF3/VF5/VF6/
        // VF7/VF8/VF9 and other head units even when Android Auto does not expose
        // a reliable vehicle model string.
        val metrics = android.util.DisplayMetrics()
        display.getRealMetrics(metrics)
        carWidth = if (metrics.widthPixels > 0) metrics.widthPixels else 800
        carHeight = if (metrics.heightPixels > 0) metrics.heightPixels else 480
        carDpi = if (metrics.densityDpi > 0) metrics.densityDpi else 160
        refreshScreenProfile(persist = true)
'''
car = replace_once(car, old_metrics, new_metrics, "CarPresentation initial screen metrics")

car = replace_once(
    car,
    '''            @JavascriptInterface
            fun isAuto(): Boolean = true
''',
    '''            @JavascriptInterface
            fun isAuto(): Boolean = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
''',
    "AndroidVoice isAuto"
)

anchor = '''    private fun applyDesktopMode(targetWeb: WebView) {
'''
helper = '''    private fun refreshScreenProfile(persist: Boolean) {
        val info = if (persist) {
            CarScreenProfileManager.detectAndSave(context, carWidth, carHeight, carDpi)
        } else {
            CarScreenProfileManager.detect(carWidth, carHeight, carDpi)
        }
        detectedScreenProfile = info.profile
        aspectRatio = info.aspectRatio
        autoScreenProfileEnabled = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        isUltrawide = autoScreenProfileEnabled && info.isUltrawide
        isPortrait = autoScreenProfileEnabled && info.isPortrait
    }

    private fun autoProfileScale(): Float =
        if (autoScreenProfileEnabled) detectedScreenProfile.toolbarScale else 1.0f

'''
car = replace_once(car, anchor, helper + anchor, "CarPresentation profile helper insertion")

old_scale = '''    fun applyWebScaleForUrl(url: String?) {
        val effectivePhoneDpi = if (phoneDpi > 0f) phoneDpi else 440f
        val effectiveCarDpi = if (carDpi > 0) carDpi.toFloat() else 160f
        val scalePercent = ((effectiveCarDpi / effectivePhoneDpi) * 100f).coerceIn(20f, 200f).toInt()
        if (scalePercent != lastAppliedScale) {
'''
new_scale = '''    fun applyWebScaleForUrl(url: String?) {
        val autoDetect = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        val effectivePhoneDpi = if (phoneDpi > 0f) phoneDpi else 440f
        val effectiveCarDpi = if (carDpi > 0) carDpi.toFloat() else 160f
        val scalePercent = if (autoDetect) {
            ((effectiveCarDpi / effectivePhoneDpi) * 100f).coerceIn(20f, 200f).toInt()
        } else {
            100
        }
        if (scalePercent != lastAppliedScale) {
'''
car = replace_once(car, old_scale, new_scale, "CarPresentation web scale toggle")

car = replace_once(
    car,
    '''        val scale = prefs.getInt(SettingsActivity.KEY_TOOLBAR_SCALE, 100)
        val iconSizeDp = ((56 * scale) / 100).coerceIn(38, 84)
''',
    '''        val scale = prefs.getInt(SettingsActivity.KEY_TOOLBAR_SCALE, 100)
        val profileScale = autoProfileScale()
        val iconSizeDp = (((56 * scale) / 100f) * profileScale).roundToInt().coerceIn(34, 84)
''',
    "sidebar profile scale"
)

car = replace_once(
    car,
    '''        val autoDetect = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        val configuredPos = prefs.getString(SettingsActivity.KEY_TOOLBAR_POSITION, "bottom") ?: "bottom"
        val positionKey = when {
            configuredPos == "auto" -> {
                if (isPortrait) "bottom" else "left"
            }
            else -> configuredPos
        }
''',
    '''        val autoDetect = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        val configuredPos = prefs.getString(SettingsActivity.KEY_TOOLBAR_POSITION, "bottom") ?: "bottom"
        val positionKey = when {
            configuredPos == "auto" && autoDetect -> {
                if (isPortrait || detectedScreenProfile == CarScreenProfileManager.Profile.COMPACT) "bottom" else "left"
            }
            configuredPos == "auto" -> "bottom"
            else -> configuredPos
        }
''',
    "sidebar auto detect position"
)

car = replace_once(
    car,
    '''        val autoDetect = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        val configuredPos = prefs.getString(SettingsActivity.KEY_TOOLBAR_POSITION, "bottom") ?: "bottom"
        val isHorizontal = (configuredPos == "bottom" || isPortrait)
''',
    '''        val autoDetect = prefs.getBoolean(SettingsActivity.KEY_AUTO_DETECT_SCREEN, true)
        val configuredPos = prefs.getString(SettingsActivity.KEY_TOOLBAR_POSITION, "bottom") ?: "bottom"
        val isHorizontal = configuredPos == "bottom" || (autoDetect && isPortrait)
''',
    "top toolbar auto orientation"
)

car = replace_once(
    car,
    '''        val vBtnSize = ((56 * dockScale) / 100).coerceIn(38, 84)
        val hBtnSize = ((50 * dockScale) / 100).coerceIn(32, 76)
''',
    '''        val profileScale = autoProfileScale()
        val vBtnSize = (((56 * dockScale) / 100f) * profileScale).roundToInt().coerceIn(34, 84)
        val hBtnSize = (((50 * dockScale) / 100f) * profileScale).roundToInt().coerceIn(30, 76)
''',
    "top toolbar profile scale"
)

old_listener = '''            if (key == SettingsActivity.KEY_THEME_MODE || key == "carhud_day_mode") {
                applyCurrentTheme(isDayMode())
            } else {
                rebuildSidebar()
                rebuildTopToolbar()
            }
'''
new_listener = '''            if (key == SettingsActivity.KEY_AUTO_DETECT_SCREEN) {
                refreshScreenProfile(persist = true)
                lastAppliedScale = -1
                applyWebScaleForUrl(web.url)
                YouTubePlayerHelper.inject(
                    web, isUltrawide, isPortrait, carWidth, carHeight, carDpi,
                    phoneDpi.toInt(), aspectRatio
                )
                rebuildSidebar()
                rebuildTopToolbar()
            } else if (key == SettingsActivity.KEY_THEME_MODE || key == "carhud_day_mode") {
                applyCurrentTheme(isDayMode())
            } else {
                rebuildSidebar()
                rebuildTopToolbar()
            }
'''
car = replace_once(car, old_listener, new_listener, "CarPresentation preference listener")
car_path.write_text(car, encoding="utf-8")

settings_path = ROOT / "app/src/main/java/com/carhud/aaproxy/SettingsActivity.kt"
settings = settings_path.read_text(encoding="utf-8")

old_switch = '''                content.addView(
                    createSwitchRow(
                        title = "Tự động nhận diện màn hình xe",
                        subtitle = "Tối ưu giao diện theo màn hình Ngang, Dọc hoặc Siêu rộng",
                        key = KEY_AUTO_DETECT_SCREEN,
                        default = true
                    )
                )

'''
new_switch = '''                content.addView(
                    createSwitchRow(
                        title = "Tự động nhận diện màn hình xe",
                        subtitle = "Tự phân loại Compact / Medium / Large / XL / Portrait / Ultrawide theo W×H, DPI và aspect thật",
                        key = KEY_AUTO_DETECT_SCREEN,
                        default = true
                    )
                )

                val lastScreenInfo = CarScreenProfileManager.lastInfo(this@SettingsActivity)
                val screenInfoSubtitle = lastScreenInfo?.detailText()
                    ?: "Chưa có dữ liệu • Kết nối Android Auto một lần để app ghi nhận màn hình xe"
                val screenProfileBadge = lastScreenInfo?.profile?.label ?: "Chưa nhận"
                content.addView(
                    settingCard(
                        title = "THÔNG TIN MÀN HÌNH XE",
                        subtitle = screenInfoSubtitle,
                        badgeText = screenProfileBadge,
                        onClick = {
                            val message = lastScreenInfo?.let {
                                "Profile: ${it.profile.label}\\n${it.detailText()}\\nAuto nhận diện: ${if (prefs.getBoolean(KEY_AUTO_DETECT_SCREEN, true)) "BẬT" else "TẮT"}"
                            } ?: "Chưa có dữ liệu màn hình xe. Hãy kết nối Android Auto rồi mở lại Cài đặt."
                            Toast.makeText(this@SettingsActivity, message, Toast.LENGTH_LONG).show()
                        }
                    )
                )

'''
settings = replace_once(settings, old_switch, new_switch, "Settings screen auto-detect section")
settings_path.write_text(settings, encoding="utf-8")

print("Applied v0.8.160 car screen auto-profile + diagnostics")
