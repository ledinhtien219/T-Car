from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"Missing start marker: {label}")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"Missing end marker: {label}")
    return text[:start] + replacement + text[end:]

# ---------------------------------------------------------------------------
# 1) Voice-search YouTube result: make autoplay deterministic.
#    Do not depend on an async sessionStorage write racing against loadUrl().
# ---------------------------------------------------------------------------
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

if "import android.util.Log\\n" not in yt:
    yt = replace_once(
        yt,
        "import android.view.View\\n",
        "import android.view.View\\nimport android.util.Log\\n",
        "YouTubePlayerHelper Log import"
    )

old_auto_block = r'''        if (window.location.pathname.indexOf('/results') === 0 && window.sessionStorage.getItem('carhud_auto_play') === 'true') {
            var attempts = 0;
            var intv = setInterval(function() {
                var firstVideo = document.querySelector('ytm-video-with-context-renderer a, ytm-compact-video-renderer a, a.media-item-thumbnail-container, a.compact-media-item-metadata-content');
                if (firstVideo && firstVideo.href) {
                    clearInterval(intv);
                    window.sessionStorage.removeItem('carhud_auto_play');
                    triggerSyntheticClick(firstVideo);
                    setTimeout(function() {
                        if (window.location.pathname.indexOf('/watch') === -1) {
                            try { firstVideo.click(); } catch(e) {}
                        }
                    }, 200);
                    setTimeout(function() {
                        if (window.location.pathname.indexOf('/watch') === -1 && firstVideo.href) {
                            window.location.href = firstVideo.href;
                        }
                    }, 500);
                }
                if (++attempts > 40) { clearInterval(intv); window.sessionStorage.removeItem('carhud_auto_play'); }
            }, 60);
        }
'''
new_auto_block = r'''        if (window.location.pathname.indexOf('/results') === 0) {
            var shouldAutoPlay = false;
            try {
                shouldAutoPlay =
                    new URLSearchParams(window.location.search).get('carhud_autoplay') === '1' ||
                    window.sessionStorage.getItem('carhud_auto_play') === 'true';
            } catch(e) {
                shouldAutoPlay = window.sessionStorage.getItem('carhud_auto_play') === 'true';
            }

            if (shouldAutoPlay && !window.__carhudAutoPlayDone) {
                var attempts = 0;
                var intv = setInterval(function() {
                    if (window.__carhudAutoPlayDone || window.location.pathname.indexOf('/results') !== 0) {
                        clearInterval(intv);
                        return;
                    }

                    // Support BOTH mobile YouTube (ytm-*) and desktop YouTube
                    // (ytd-*). Wide Android Auto screens can receive either UI.
                    var selectors = [
                        'ytd-video-renderer a#thumbnail[href*="/watch"]',
                        'ytd-video-renderer a#video-title[href*="/watch"]',
                        'ytm-video-with-context-renderer a[href*="/watch"]',
                        'ytm-compact-video-renderer a[href*="/watch"]',
                        'a.media-item-thumbnail-container[href*="/watch"]',
                        'a.compact-media-item-metadata-content[href*="/watch"]',
                        'a[href*="/watch?v="]'
                    ];
                    var firstVideo = null;
                    for (var i = 0; i < selectors.length && !firstVideo; i++) {
                        firstVideo = document.querySelector(selectors[i]);
                    }

                    var href = firstVideo && firstVideo.href ? firstVideo.href : '';
                    if (href && href.indexOf('/watch') !== -1) {
                        clearInterval(intv);
                        window.__carhudAutoPlayDone = true;
                        try { window.sessionStorage.removeItem('carhud_auto_play'); } catch(e) {}
                        // Direct navigation is more reliable than synthetic clicks
                        // across YouTube mobile/desktop DOM variants.
                        window.location.href = href;
                        return;
                    }

                    if (++attempts > 60) {
                        clearInterval(intv);
                    }
                }, 80);
            }
        }
'''
yt = replace_once(yt, old_auto_block, new_auto_block, "YouTube result autoplay JS")

search_start = "    fun search(view: WebView?, query: String) {"
search_end = "    fun setDuckingVolume(view: WebView?, volume: Float) {"
new_search = r'''    fun search(view: WebView?, query: String) {
        if (view == null) return
        val cleanQuery = query.trim()
        if (cleanQuery.isEmpty()) return

        view.post {
            try {
                val encoded = URLEncoder.encode(cleanQuery, "UTF-8")
                val host = if (view.url?.contains("www.youtube.com") == true) {
                    "https://www.youtube.com"
                } else {
                    "https://m.youtube.com"
                }

                // Put the autoplay request IN THE URL. This survives app switches,
                // origin changes and WebView navigation, unlike the previous async
                // sessionStorage write which could lose the flag before loadUrl().
                val targetUrl = "$host/results?search_query=$encoded&carhud_autoplay=1"
                view.loadUrl(targetUrl)

                // Native retry bridge: YouTube sometimes renders results after
                // onPageFinished. All retries are idempotent and navigate at most once.
                longArrayOf(450L, 900L, 1600L, 2600L).forEach { delayMs ->
                    view.postDelayed({
                        tryAutoPlaySearchResult(view)
                    }, delayMs)
                }
            } catch (e: Exception) {
                Log.e("YouTubePlayerHelper", "Voice search navigation failed", e)
            }
        }
    }

    private fun tryAutoPlaySearchResult(view: WebView) {
        try {
            view.evaluateJavascript(
                """
                (function() {
                    try {
                        if (window.location.pathname.indexOf('/results') !== 0) return 'not-results';
                        if (window.__carhudAutoPlayDone) return 'done';

                        var enabled = false;
                        try {
                            enabled =
                                new URLSearchParams(window.location.search).get('carhud_autoplay') === '1' ||
                                window.sessionStorage.getItem('carhud_auto_play') === 'true';
                        } catch(e) {}
                        if (!enabled) return 'disabled';

                        var selectors = [
                            'ytd-video-renderer a#thumbnail[href*="/watch"]',
                            'ytd-video-renderer a#video-title[href*="/watch"]',
                            'ytm-video-with-context-renderer a[href*="/watch"]',
                            'ytm-compact-video-renderer a[href*="/watch"]',
                            'a.media-item-thumbnail-container[href*="/watch"]',
                            'a.compact-media-item-metadata-content[href*="/watch"]',
                            'a[href*="/watch?v="]'
                        ];

                        var first = null;
                        for (var i = 0; i < selectors.length && !first; i++) {
                            first = document.querySelector(selectors[i]);
                        }

                        var href = first && first.href ? first.href : '';
                        if (!href || href.indexOf('/watch') === -1) return 'waiting';

                        window.__carhudAutoPlayDone = true;
                        try { window.sessionStorage.removeItem('carhud_auto_play'); } catch(e) {}
                        window.location.href = href;
                        return 'opened';
                    } catch(e) {
                        return 'error';
                    }
                })();
                """.trimIndent(),
                null
            )
        } catch (_: Exception) {
        }
    }

'''
yt = replace_between(yt, search_start, search_end, new_search, "YouTube search function")
yt_path.write_text(yt, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) SpeechRecognizer lifecycle: fully release old recognizers/listeners.
# ---------------------------------------------------------------------------
voice_path = ROOT / "app/src/main/java/com/carhud/aaproxy/VoiceSearchManager.kt"
voice = voice_path.read_text(encoding="utf-8")

voice = replace_once(
    voice,
    '''    private var retryCount = 0

''',
    '''    private var retryCount = 0
    @Volatile private var released = false

''',
    "VoiceSearchManager release flag"
)

voice = replace_once(
    voice,
    '''    fun prewarm() {
        if (Looper.myLooper() == Looper.getMainLooper()) {
''',
    '''    fun prewarm() {
        if (released) return
        if (Looper.myLooper() == Looper.getMainLooper()) {
''',
    "VoiceSearchManager prewarm guard"
)

voice = replace_once(
    voice,
    '''    private fun dispatchSuccess(query: String) {
        if (hasDispatchedResult) return
''',
    '''    private fun dispatchSuccess(query: String) {
        if (released || hasDispatchedResult) return
''',
    "VoiceSearchManager dispatch guard"
)

voice = replace_once(
    voice,
    '''    fun startListening() {
        val action = Runnable {
''',
    '''    fun startListening() {
        if (released) return
        val action = Runnable {
            if (released) return@Runnable
''',
    "VoiceSearchManager start guard"
)

stop_marker = '''    fun stop() {
        val action = Runnable {
'''
release_method = r'''    fun release() {
        released = true
        val action = Runnable {
            handler.removeCallbacksAndMessages(null)
            cleanupRecognizer()
            lastRecognizedText = null
            hasDispatchedResult = true
            isListeningActive = false
        }
        if (Looper.myLooper() == Looper.getMainLooper()) {
            action.run()
        } else {
            handler.post(action)
        }
    }

'''
voice = replace_once(voice, stop_marker, release_method + stop_marker, "VoiceSearchManager release method")
voice_path.write_text(voice, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) Android Auto Presentation lifecycle: release listeners on dismiss.
#    The old code only released them in destroyWeb(), but normal AA surface
#    replacement dismisses Presentation without destroying the persistent WebView.
# ---------------------------------------------------------------------------
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")

car = replace_once(
    car,
    '''    private val mainHandler = Handler(Looper.getMainLooper())
''',
    '''    private val mainHandler = Handler(Looper.getMainLooper())
    @Volatile private var presentationResourcesReleased = false
''',
    "CarPresentation release flag"
)

onstop_marker = '''    override fun onStop() {
'''
release_resources = r'''    private fun releasePresentationResources() {
        if (presentationResourcesReleased) return
        presentationResourcesReleased = true

        try { autoHideHandler.removeCallbacksAndMessages(null) } catch (_: Exception) {}
        try {
            pendingSteeringNextRunnable?.let(mainHandler::removeCallbacks)
            pendingSteeringNextRunnable = null
        } catch (_: Exception) {}
        try { mainHandler.removeCallbacksAndMessages(null) } catch (_: Exception) {}

        try { hudPrefs.unregisterOnSharedPreferenceChangeListener(hudPrefsListener) } catch (_: Exception) {}
        try { prefs.unregisterOnSharedPreferenceChangeListener(this) } catch (_: Exception) {}

        try { CarMediaManager.unregisterVoiceListener(voiceListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterSearchQueryListener(searchQueryListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterSearchDismissListener(searchDismissListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterSearchLiveTextListener(searchLiveTextListener) } catch (_: Exception) {}

        try { voiceManager.release() } catch (_: Exception) {}
        if (CarMediaManager.activeVoiceManager === voiceManager) {
            CarMediaManager.activeVoiceManager = null
        }
    }

'''
car = replace_once(car, onstop_marker, release_resources + onstop_marker, "CarPresentation resource release helper")

old_dismiss = '''    override fun dismiss() {
        try {
            (web.parent as? ViewGroup)?.removeView(web)
        } catch(e: Exception) {}
        super.dismiss()
    }
'''
new_dismiss = '''    override fun dismiss() {
        releasePresentationResources()
        try {
            (web.parent as? ViewGroup)?.removeView(web)
        } catch(e: Exception) {}
        try {
            super.dismiss()
        } catch (e: Exception) {
            AppCrashHandler.logError(e, "CarPresentationDismiss")
        }
    }
'''
car = replace_once(car, old_dismiss, new_dismiss, "CarPresentation dismiss cleanup")

car = replace_once(
    car,
    '''    fun destroyWeb() {
        try {
''',
    '''    fun destroyWeb() {
        releasePresentationResources()
        try {
''',
    "CarPresentation destroy cleanup"
)
car_path.write_text(car, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4) MainActivity lifecycle: unregister the exact voice listener and destroy
#    SpeechRecognizer instead of leaking an Activity through global sets.
# ---------------------------------------------------------------------------
main_path = ROOT / "app/src/main/java/com/carhud/aaproxy/MainActivity.kt"
main = main_path.read_text(encoding="utf-8")

listener_anchor = '''    private val searchDismissListener: () -> Unit = {
        mainHandler.post {
            hideSearchOverlay(notifyCar = false)
        }
    }

'''
named_listener = listener_anchor + '''    private val carMediaVoiceListener: (VoiceSearchManager.State, String) -> Unit = { state, text ->
        mainHandler.post {
            if (!isFinishing && !isDestroyed) {
                updateVoiceBanner(state, text)
            }
        }
    }

'''
main = replace_once(main, listener_anchor, named_listener, "MainActivity named voice listener")

old_register = '''        CarMediaManager.registerVoiceListener { state, text ->
            mainHandler.post {
                updateVoiceBanner(state, text)
            }
        }
'''
main = replace_once(
    main,
    old_register,
    '''        CarMediaManager.registerVoiceListener(carMediaVoiceListener)
''',
    "MainActivity voice listener registration"
)

old_destroy = '''    override fun onDestroy() {
        try { unregisterReceiver(exitReceiver) } catch (e: Exception) {}
        super.onDestroy()
        prefs.unregisterOnSharedPreferenceChangeListener(prefChangeListener)
        CarMediaManager.unregisterSearchRequestListener(searchRequestListener)
        CarMediaManager.unregisterSearchDismissListener(searchDismissListener)
        autoHideHandler.removeCallbacks(hideFloatingBarRunnable)
        if (::web.isInitialized) {
            CarMediaManager.unregisterPhoneWebView(web)
        }
        if (CarMediaManager.mainActivityRoot == rootLayout) {
            CarMediaManager.mainActivityRoot = null
        }
    }
'''
new_destroy = '''    override fun onDestroy() {
        try { unregisterReceiver(exitReceiver) } catch (_: Exception) {}
        try { prefs.unregisterOnSharedPreferenceChangeListener(prefChangeListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterVoiceListener(carMediaVoiceListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterSearchRequestListener(searchRequestListener) } catch (_: Exception) {}
        try { CarMediaManager.unregisterSearchDismissListener(searchDismissListener) } catch (_: Exception) {}
        try { autoHideHandler.removeCallbacksAndMessages(null) } catch (_: Exception) {}
        try { voiceManager.release() } catch (_: Exception) {}

        if (CarMediaManager.activeVoiceManager === voiceManager) {
            CarMediaManager.activeVoiceManager = null
        }

        if (::web.isInitialized) {
            try { CarMediaManager.unregisterPhoneWebView(web) } catch (_: Exception) {}
        }
        if (::rootLayout.isInitialized && CarMediaManager.mainActivityRoot == rootLayout) {
            CarMediaManager.mainActivityRoot = null
        }
        super.onDestroy()
    }
'''
main = replace_once(main, old_destroy, new_destroy, "MainActivity lifecycle cleanup")
main_path.write_text(main, encoding="utf-8")

print("Applied v0.8.161 voice autoplay + lifecycle stability fixes")
