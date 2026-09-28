from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# 1) Dashboard artwork: keep IPTV/channel logos fully visible.
# ---------------------------------------------------------------------------
layout_path = ROOT / "app/src/main/res/layout/dashboard.xml"
layout = layout_path.read_text(encoding="utf-8")

old_image = '''                    <ImageView
                        android:id="@+id/mediaAlbumImageView"
                        android:layout_width="match_parent"
                        android:layout_height="match_parent"
                        android:contentDescription="@null"
                        android:scaleType="centerCrop"
                        android:visibility="gone"
                        tools:src="@android:drawable/ic_media_play"
                        tools:visibility="visible" />'''

new_image = '''                    <ImageView
                        android:id="@+id/mediaAlbumImageView"
                        android:layout_width="match_parent"
                        android:layout_height="match_parent"
                        android:contentDescription="@null"
                        android:padding="2dp"
                        android:scaleType="fitCenter"
                        android:visibility="gone"
                        tools:src="@android:drawable/ic_media_play"
                        tools:visibility="visible" />'''

layout = replace_once(layout, old_image, new_image, "dashboard media artwork ImageView")
layout_path.write_text(layout, encoding="utf-8")

dashboard_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarDashboardView.kt"
dashboard = dashboard_path.read_text(encoding="utf-8")

old_art = '''                if (track.artworkBitmap != null) {
                    mediaAlbumImageView.setImageBitmap(track.artworkBitmap)
                    mediaAlbumImageView.visibility = VISIBLE
                    mediaAlbumIcon.visibility = View.GONE
                } else {
                    mediaAlbumImageView.visibility = View.GONE
                    mediaAlbumIcon.visibility = View.VISIBLE
                }'''

new_art = '''                if (track.artworkBitmap != null) {
                    val youtubeArtwork = track.artworkUrl.contains("ytimg.com", ignoreCase = true) ||
                        track.artworkUrl.contains("youtube.com", ignoreCase = true)
                    mediaAlbumImageView.scaleType = if (youtubeArtwork) {
                        ImageView.ScaleType.CENTER_CROP
                    } else {
                        ImageView.ScaleType.FIT_CENTER
                    }
                    val artPadding = if (youtubeArtwork) 0 else dp(2)
                    mediaAlbumImageView.setPadding(artPadding, artPadding, artPadding, artPadding)
                    mediaAlbumImageView.setImageBitmap(track.artworkBitmap)
                    mediaAlbumImageView.visibility = VISIBLE
                    mediaAlbumIcon.visibility = View.GONE
                } else {
                    mediaAlbumImageView.visibility = View.GONE
                    mediaAlbumIcon.visibility = View.VISIBLE
                }'''

dashboard = replace_once(dashboard, old_art, new_art, "dashboard artwork rendering")
dashboard_path.write_text(dashboard, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Catch YouTube's changing search DOM and route search input to T-Car.
# ---------------------------------------------------------------------------
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

old_search_hook = '''        document.addEventListener('click', function(e) {
            var target = e.target;
            if (!target) return;
            
            var mic = target.closest('button[aria-label*="giọng nói"], button[aria-label*="voice"], button[aria-label*="mic"], .search-box-mic, ytm-search-box-mic, [class*="voice-search"]');
            if (mic) {
                e.preventDefault();
                e.stopPropagation();
                if (window.AndroidVoice && window.AndroidVoice.startListening) {
                    window.AndroidVoice.startListening();
                }
                return;
            }

            var search = target.closest('ytm-searchbox, .searchbox-input, input[name="search_query"], input.searchbox-input, .searchbox-input-wrapper, button[aria-label*="Search"], button[aria-label*="Tìm kiếm"], [aria-label*="search"], [aria-label*="Tìm kiếm"], .header-bar-icon[aria-label*="Tìm"], ytm-search-box');
            if (search) {
                e.preventDefault();
                e.stopPropagation();
                if (target.tagName === 'INPUT') target.blur();
                if (window.AndroidVoice && window.AndroidVoice.openSearchKeyboard) {
                    window.AndroidVoice.openSearchKeyboard();
                }
            }
        }, true);

        document.addEventListener('focusin', function(e) {
            var target = e.target;
            if (!target) return;
            if (target.tagName === 'INPUT' && (target.name === 'search_query' || target.classList.contains('searchbox-input') || target.closest('ytm-searchbox'))) {
                target.blur();
                if (window.AndroidVoice && window.AndroidVoice.openSearchKeyboard) {
                    window.AndroidVoice.openSearchKeyboard();
                }
            }
        }, true);'''

new_search_hook = '''        function carhudClosestElement(target) {
            if (!target) return null;
            if (target.nodeType === 1) return target;
            return target.parentElement || null;
        }

        function carhudIsMicTarget(target) {
            var el = carhudClosestElement(target);
            if (!el || !el.closest) return false;
            return !!el.closest(
                'button[aria-label*="giọng nói" i], button[aria-label*="voice" i], ' +
                'button[aria-label*="mic" i], .search-box-mic, ytm-search-box-mic, ' +
                '[class*="voice-search"], [class*="voiceSearch"]'
            );
        }

        function carhudIsSearchTarget(target) {
            var el = carhudClosestElement(target);
            var depth = 0;
            while (el && depth < 7) {
                try {
                    var tag = (el.tagName || '').toLowerCase();
                    var name = (el.getAttribute && el.getAttribute('name') || '').toLowerCase();
                    var role = (el.getAttribute && el.getAttribute('role') || '').toLowerCase();
                    var aria = (el.getAttribute && el.getAttribute('aria-label') || '').toLowerCase();
                    var placeholder = (el.getAttribute && el.getAttribute('placeholder') || '').toLowerCase();
                    var title = (el.getAttribute && el.getAttribute('title') || '').toLowerCase();
                    var cls = (typeof el.className === 'string' ? el.className : '').toLowerCase();
                    var id = (el.id || '').toLowerCase();
                    var text = ((el.textContent || '').trim()).toLowerCase();
                    var hint = aria + ' ' + placeholder + ' ' + title + ' ' + text;

                    if (name === 'search_query' || id === 'search' || id.indexOf('searchbox') >= 0) return true;
                    if (tag === 'ytm-searchbox' || tag === 'yt-searchbox' || tag === 'ytm-search-box') return true;
                    if (cls.indexOf('searchbox') >= 0 || cls.indexOf('search-box') >= 0 || cls.indexOf('searchfield') >= 0) return true;
                    if ((tag === 'input' || role === 'search' || role === 'searchbox' || tag === 'button') &&
                        (hint.indexOf('search') >= 0 || hint.indexOf('tìm') >= 0)) return true;
                    if (hint.indexOf('tìm trên youtube') >= 0 || hint.indexOf('search youtube') >= 0) return true;
                } catch(err) {}
                el = el.parentElement;
                depth++;
            }
            return false;
        }

        var __carhudSearchBridgeAt = 0;
        function carhudOpenKeyboardFromYouTube(e) {
            try {
                var target = e && e.target;
                if (!target || carhudIsMicTarget(target) || !carhudIsSearchTarget(target)) return false;

                var bridgeAvailable = !!(window.AndroidVoice && window.AndroidVoice.openSearchKeyboard);
                if (!bridgeAvailable) {
                    // Never dead-lock the real YouTube field if the native bridge is unavailable.
                    return false;
                }

                if (e) {
                    if (e.cancelable) e.preventDefault();
                    e.stopPropagation();
                    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                }

                try {
                    var active = document.activeElement;
                    if (active && active.blur) active.blur();
                } catch(err) {}

                var now = Date.now();
                if (now - __carhudSearchBridgeAt > 350) {
                    __carhudSearchBridgeAt = now;
                    window.AndroidVoice.openSearchKeyboard();
                }
                return true;
            } catch(err) {
                return false;
            }
        }

        ['pointerdown', 'touchstart', 'mousedown', 'click'].forEach(function(eventName) {
            document.addEventListener(eventName, function(e) {
                if (eventName === 'click' && carhudIsMicTarget(e.target)) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (e.stopImmediatePropagation) e.stopImmediatePropagation();
                    if (window.AndroidVoice && window.AndroidVoice.startListening) {
                        window.AndroidVoice.startListening();
                    }
                    return;
                }
                carhudOpenKeyboardFromYouTube(e);
            }, true);
        });

        document.addEventListener('focusin', function(e) {
            carhudOpenKeyboardFromYouTube(e);
        }, true);'''

yt = replace_once(yt, old_search_hook, new_search_hook, "YouTube search bridge")
yt_path.write_text(yt, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3) CAR SEARCH: do NOT try to show Android IME on the Presentation/virtual
# display. Android Auto/HUR owns the keyboard. Route all car search entry
# points to SearchTemplate, which reliably opens the host keyboard.
# ---------------------------------------------------------------------------
presentation_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
presentation = presentation_path.read_text(encoding="utf-8")

old_bridge = '''            @JavascriptInterface
            fun openSearchKeyboard() {
                mainHandler.post {
                    showSearchOverlay()
                }
            }'''

new_bridge = '''            @JavascriptInterface
            fun openSearchKeyboard() {
                mainHandler.post {
                    CarMediaManager.requestCarNativeSearch("")
                }
            }'''

presentation = replace_once(presentation, old_bridge, new_bridge, "car YouTube search JS bridge")

old_show = '''    fun showSearchOverlay() {
        searchOverlay.visibility = View.VISIBLE
        searchOverlay.bringToFront()

        // Clean UI: hide all background chrome & widgets so screen is 100% focused on keyboard
        hudOverlay?.visibility = View.GONE
        sidebarContainer?.visibility = View.GONE
        topToolbarContainer?.visibility = View.GONE

        searchInput.requestFocus()
        CarMediaManager.requestSearch(searchInput.text.toString())
    }'''

new_show = '''    fun showSearchOverlay() {
        // Search input on Android Auto must be owned by the host. EditText/IME on
        // the secondary Presentation display can receive focus but cannot reliably
        // receive keyboard input. SearchTemplate fixes that at the platform level.
        val initial = if (::searchInput.isInitialized) searchInput.text?.toString().orEmpty() else ""
        CarMediaManager.requestCarNativeSearch(initial)
    }'''

presentation = replace_once(presentation, old_show, new_show, "car search overlay routing")
presentation_path.write_text(presentation, encoding="utf-8")


manager_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarMediaManager.kt"
manager = manager_path.read_text(encoding="utf-8")
manager = replace_once(
    manager,
    '''    private val carNativeSearchListeners = java.util.concurrent.CopyOnWriteArraySet<(String) -> Unit>()''',
    '''    private val carNativeSearchListeners = java.util.concurrent.CopyOnWriteArraySet<(String) -> Unit>()
    @Volatile private var pendingCarSearchQuery: String? = null

    fun queuePendingCarSearch(query: String) {
        val q = query.trim()
        if (q.isNotEmpty()) {
            pendingCarSearchQuery = q
        }
    }

    fun peekPendingCarSearch(): String? = pendingCarSearchQuery

    fun consumePendingCarSearch(): String? {
        val q = pendingCarSearchQuery
        pendingCarSearchQuery = null
        return q
    }''',
    "pending car search queue"
)

# Do not auto-play the first result for typed search. Voice search already has
# its own carhud_autoplay=1 retry logic in YouTubePlayerHelper.searchAndPlay().
old_results_autoplay = '''                    if (url.contains("watch")) {
                        if (userWantsPlayback || autoResume) {
                            userWantsPlayback = true
                            ensureAudioFocus()
                            acquireWakeLock(appCtx)
                            view.postDelayed({
                                if (!isPlaying) {
                                    YouTubePlayerHelper.resumePlayback(view)
                                }
                            }, 500L)
                        }
                    } else if (userWantsPlayback || autoResume) {
                        ensureAudioFocus()
                        view.postDelayed({
                            if (!isPlaying) {
                                YouTubePlayerHelper.playFirstAvailableVideo(view)
                            }
                        }, 500L)
                    }'''
new_results_autoplay = '''                    if (url.contains("watch")) {
                        if (userWantsPlayback || autoResume) {
                            userWantsPlayback = true
                            ensureAudioFocus()
                            acquireWakeLock(appCtx)
                            view.postDelayed({
                                if (!isPlaying) {
                                    YouTubePlayerHelper.resumePlayback(view)
                                }
                            }, 500L)
                        }
                    } else if (url.contains("/results")) {
                        // Typed search must remain on the result list.
                        // Voice autoplay is handled separately by searchAndPlay().
                    } else if (userWantsPlayback || autoResume) {
                        ensureAudioFocus()
                        view.postDelayed({
                            if (!isPlaying) {
                                YouTubePlayerHelper.playFirstAvailableVideo(view)
                            }
                        }, 500L)
                    }'''
manager = replace_once(manager, old_results_autoplay, new_results_autoplay, "typed search no-autoplay")
manager_path.write_text(manager, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4) Native Android Auto SearchTemplate: queue the query until the projection
# surface/WebView is reattached, then show YouTube results.
# ---------------------------------------------------------------------------
native_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarSearchScreen.kt"
native = native_path.read_text(encoding="utf-8")

old_submit = '''            override fun onSearchSubmitted(searchTerm: String) {
                if (searchTerm.isNotBlank()) {
                    CarMediaManager.submitSearchQuery(searchTerm)
                    screenManager.pop()
                }
            }'''

new_submit = '''            override fun onSearchSubmitted(searchTerm: String) {
                val query = searchTerm.trim()
                if (query.isNotEmpty()) {
                    // SearchTemplate temporarily replaces the projection surface.
                    // Queue the query first; CarHudAutoScreen applies it only after
                    // the T-Car surface/WebView has been reattached.
                    CarMediaManager.queuePendingCarSearch(query)
                    CarMediaManager.updateSearchText(query)
                    screenManager.pop()
                }
            }'''

native = replace_once(native, old_submit, new_submit, "native Android Auto search submit")
native_path.write_text(native, encoding="utf-8")


# Apply a queued typed-search only after the projection surface and persistent
# WebView are back. This prevents CarPresentation recreation from resetting
# YouTube to Home after SearchTemplate closes.
screen_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarHudAutoScreen.kt"
screen = screen_path.read_text(encoding="utf-8")
old_surface_ready = '''            val pres = CarPresentation(carContext, vd.display, persistentWeb)
            pres.show()
            presentation = pres

            CarMediaManager.setCarConnectionState(true)'''
new_surface_ready = '''            val pres = CarPresentation(carContext, vd.display, persistentWeb)
            pres.show()
            presentation = pres

            CarMediaManager.setCarConnectionState(true)

            val pendingSearch = CarMediaManager.consumePendingCarSearch()
            if (!pendingSearch.isNullOrBlank()) {
                persistentWeb.postDelayed({
                    YouTubePlayerHelper.search(persistentWeb, pendingSearch)
                }, 250L)
            }'''
screen = replace_once(screen, old_surface_ready, new_surface_ready, "apply pending search after surface restore")
screen_path.write_text(screen, encoding="utf-8")

# ---------------------------------------------------------------------------
# Contract checks.
# ---------------------------------------------------------------------------
final_layout = layout_path.read_text(encoding="utf-8")
final_dash = dashboard_path.read_text(encoding="utf-8")
final_yt = yt_path.read_text(encoding="utf-8")
final_pres = presentation_path.read_text(encoding="utf-8")
final_native = native_path.read_text(encoding="utf-8")
final_manager = manager_path.read_text(encoding="utf-8")
final_screen = screen_path.read_text(encoding="utf-8")

checks = [
    ("TV logo fitCenter", 'android:scaleType="fitCenter"' in final_layout),
    ("dynamic artwork scaling", "youtubeArtwork" in final_dash and "ImageView.ScaleType.FIT_CENTER" in final_dash),
    ("YouTube search detector", "carhudIsSearchTarget" in final_yt),
    ("search fallback safety", "bridgeAvailable" in final_yt),
    ("car bridge uses native AA search", 'CarMediaManager.requestCarNativeSearch("")' in final_pres),
    ("car search no longer relies on IME overlay", "SearchTemplate fixes that at the platform level" in final_pres),
    ("native keyboard defaults open", ".setShowKeyboardByDefault(true)" in final_native),
    ("native submit queues result navigation", "CarMediaManager.queuePendingCarSearch(query)" in final_native),
    ("pending query storage", "pendingCarSearchQuery" in final_manager),
    ("typed results stay on list", 'url.contains("/results")' in final_manager),
    ("pending search applied after surface restore", "consumePendingCarSearch()" in final_screen and "YouTubePlayerHelper.search(persistentWeb, pendingSearch)" in final_screen),
]
for label, ok in checks:
    if not ok:
        raise RuntimeError(f"Fix verification failed: {label}")

print("Fixed search input with Android Auto native keyboard + immediate YouTube results")




# TEMP RESULT LAYOUT DEBUG
_s = yt_path.read_text(encoding="utf-8", errors="replace")
for _needle in ["fun inject(", "createElement('style')", "carhud-style", "ytm-video-with-context-renderer", "grid", "result"]:
    _i = _s.find(_needle)
    print("\n===== RESULT LAYOUT DEBUG", _needle, "=====")
    if _i >= 0:
        print(_s[max(0, _i-3500):min(len(_s), _i+14000)])
    else:
        print("MISSING")
