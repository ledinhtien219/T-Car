from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# 1) Remove the four unneeded trailing toolbar buttons and their Settings rows.
#    Keep Search/Mic and the rest of the car controls.
# ---------------------------------------------------------------------------
settings_path = ROOT / "app/src/main/java/com/carhud/aaproxy/SettingsActivity.kt"
settings = settings_path.read_text(encoding="utf-8")

for row in (
    '                content.addView(createSwitchRow("Nút Play / Pause (▶/⏸)", "Phát hoặc tạm dừng nội dung đang nghe", KEY_SHOW_PLAY_PAUSE, true))\n',
    '                content.addView(createSwitchRow("Nút Chuyển bài (⏭)", "Chuyển nhanh sang bài/video tiếp theo", KEY_SHOW_NEXT, true))\n',
    '                content.addView(createSwitchRow("Nút Toàn màn hình (⛶)", "Bật/tắt toàn màn hình video", KEY_SHOW_FULLSCREEN, true))\n',
    '                content.addView(createSwitchRow("Nút Cài đặt (⚙)", "Mở nhanh cài đặt T-Car trên điện thoại", KEY_SHOW_SETTINGS, true))\n',
):
    settings = settings.replace(row, "")

settings_path.write_text(settings, encoding="utf-8")

car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")

car = replace_once(
    car,
    '''        val showPlayPause = prefs.getBoolean(SettingsActivity.KEY_SHOW_PLAY_PAUSE, true)
        val showNext = prefs.getBoolean(SettingsActivity.KEY_SHOW_NEXT, true)
        val showFullscreen = prefs.getBoolean(SettingsActivity.KEY_SHOW_FULLSCREEN, true)
        val showSettings = prefs.getBoolean(SettingsActivity.KEY_SHOW_SETTINGS, true)
''',
    '''        // Simplified toolbar: these four trailing controls are intentionally removed.
        val showPlayPause = false
        val showNext = false
        val showFullscreen = false
        val showSettings = false
''',
    "remove four trailing toolbar buttons"
)
car_path.write_text(car, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Voice YouTube search: mobile-first results, larger cards, faster response.
# ---------------------------------------------------------------------------
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

old_host = '''                val host = if (view.url?.contains("www.youtube.com") == true) {
                    "https://www.youtube.com"
                } else {
                    "https://m.youtube.com"
                }
'''
yt = replace_once(
    yt,
    old_host,
    '''                // Voice search always opens the mobile result page. On a car
                // screen the desktop result grid is too small to read/tap safely.
                val host = "https://m.youtube.com"
''',
    "mobile voice search host"
)

yt = replace_once(
    yt,
    '                longArrayOf(450L, 900L, 1600L, 2600L).forEach { delayMs ->',
    '                longArrayOf(180L, 360L, 650L, 1000L).forEach { delayMs ->',
    "faster native autoplay retries"
)

results_anchor = '''        if (window.location.pathname.indexOf('/results') === 0) {
            var shouldAutoPlay = false;
'''
results_new = '''        if (window.location.pathname.indexOf('/results') === 0) {
            // Make fallback result lists readable on wide head units. This only
            // affects the search page and disappears automatically after navigation.
            try {
                var style = document.getElementById('carhud-search-results-style');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'carhud-search-results-style';
                    style.textContent = [
                        'ytd-video-renderer{min-height:170px!important;margin-bottom:14px!important;}',
                        'ytd-video-renderer #thumbnail{min-width:300px!important;width:300px!important;}',
                        'ytd-video-renderer #video-title{font-size:21px!important;line-height:1.28!important;}',
                        'ytm-video-with-context-renderer,ytm-compact-video-renderer{margin-bottom:16px!important;}',
                        'ytm-video-with-context-renderer .media-item-headline,ytm-compact-video-renderer .media-item-headline{font-size:19px!important;line-height:1.28!important;}'
                    ].join('');
                    (document.head || document.documentElement).appendChild(style);
                }
                var vw = window.innerWidth || 0;
                document.documentElement.style.zoom = vw >= 1200 ? '1.28' : (vw >= 850 ? '1.18' : '1.08');
            } catch(e) {}

            var shouldAutoPlay = false;
'''
yt = replace_once(yt, results_anchor, results_new, "larger voice search results")

old_interval = '''                    if (++attempts > 60) {
                        clearInterval(intv);
                    }
                }, 80);
'''
new_interval = '''                    if (++attempts > 26) {
                        clearInterval(intv);
                    }
                }, 60);
'''
yt = replace_once(yt, old_interval, new_interval, "faster JS autoplay polling")
yt_path.write_text(yt, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) Speech recognition: modest latency reduction without cutting off phrases.
# ---------------------------------------------------------------------------
voice_path = ROOT / "app/src/main/java/com/carhud/aaproxy/VoiceSearchManager.kt"
voice = voice_path.read_text(encoding="utf-8")
voice = voice.replace("handler.postDelayed(autoCommitRunnable, 400L)", "handler.postDelayed(autoCommitRunnable, 300L)")
voice = voice.replace("RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 500L", "RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 400L")
voice = voice.replace("RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 350L", "RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 250L")
voice_path.write_text(voice, encoding="utf-8")

print("Applied v0.8.164 larger/faster voice results and simplified toolbar")
