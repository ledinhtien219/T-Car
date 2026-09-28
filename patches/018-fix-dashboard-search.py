from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# 1) Dashboard artwork: TV/channel logos must never be center-cropped.
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

# Keep YouTube thumbnails visually full-bleed, but fit IPTV/channel logos
# completely inside the square artwork box.
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
# 2) YouTube search field: newer YouTube DOM variants were escaping the old
# click selector. Capture pointer/touch/mouse/focus and open T-Car keyboard.
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
                    if (window.AndroidVoice && window.AndroidVoice.openSearchKeyboard) {
                        window.AndroidVoice.openSearchKeyboard();
                    }
                }
                return true;
            } catch(err) {
                return false;
            }
        }

        // YouTube changes the search control frequently. Capture the earliest
        // pointer/touch/mouse event so its own SPA handler cannot swallow it.
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
# 3) In-car search overlay: guarantee focus and IME Search/Enter submission.
# The custom T-Car keyboard remains visible even when Android Auto suppresses
# the platform IME. Submission always navigates directly to search results.
# ---------------------------------------------------------------------------
presentation_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
presentation = presentation_path.read_text(encoding="utf-8")

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
        searchOverlay.visibility = View.VISIBLE
        searchOverlay.bringToFront()

        // Clean UI: hide all background chrome & widgets so screen is 100% focused on keyboard
        hudOverlay?.visibility = View.GONE
        sidebarContainer?.visibility = View.GONE
        topToolbarContainer?.visibility = View.GONE

        searchInput.post {
            searchInput.requestFocus()
            searchInput.setSelection(searchInput.text?.length ?: 0)
            try {
                val displayCtx = context.createDisplayContext(display)
                val imm = displayCtx.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
                    ?: context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
                imm?.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT)
            } catch (_: Exception) {}
        }
        CarMediaManager.requestSearch(searchInput.text.toString())
    }'''

presentation = replace_once(presentation, old_show, new_show, "car search overlay focus")

# Make hardware/system keyboard Search/Enter perform the same immediate result
# navigation as the large T-Car search key. Avoid duplicating listeners if the
# source already gained them in a future source ZIP.
input_anchor = '''                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                imeOptions = EditorInfo.IME_ACTION_SEARCH
'''
if input_anchor in presentation and "executeSearch(searchInput.text.toString())" in presentation:
    listener = input_anchor + '''                setOnEditorActionListener { _, actionId, event ->
                    val submit = actionId == EditorInfo.IME_ACTION_SEARCH ||
                        actionId == EditorInfo.IME_ACTION_DONE ||
                        (event?.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)
                    if (submit) {
                        executeSearch(text.toString())
                        true
                    } else {
                        false
                    }
                }
'''
    # Only add if this exact input block does not already have an editor listener.
    probe_at = presentation.find(input_anchor)
    probe = presentation[probe_at:probe_at + 1400] if probe_at >= 0 else ""
    if "setOnEditorActionListener" not in probe:
        presentation = replace_once(presentation, input_anchor, listener, "car search editor action")

presentation_path.write_text(presentation, encoding="utf-8")

# Contract checks: fail immediately if a future source breaks the fixes.
final_layout = layout_path.read_text(encoding="utf-8")
final_dash = dashboard_path.read_text(encoding="utf-8")
final_yt = yt_path.read_text(encoding="utf-8")
final_pres = presentation_path.read_text(encoding="utf-8")

checks = [
    ("TV logo fitCenter", 'android:scaleType="fitCenter"' in final_layout),
    ("dynamic artwork scaling", "youtubeArtwork" in final_dash and "ImageView.ScaleType.FIT_CENTER" in final_dash),
    ("new YouTube search target detector", "carhudIsSearchTarget" in final_yt),
    ("pointer search bridge", "'pointerdown', 'touchstart', 'mousedown', 'click'" in final_yt),
    ("direct keyboard bridge", "window.AndroidVoice.openSearchKeyboard()" in final_yt),
    ("search overlay IME focus", "imm?.showSoftInput(searchInput, InputMethodManager.SHOW_IMPLICIT)" in final_pres),
    ("direct result search", "YouTubePlayerHelper.search(web, q)" in final_pres),
]
for label, ok in checks:
    if not ok:
        raise RuntimeError(f"Fix verification failed: {label}")

print("Fixed dashboard channel artwork + robust YouTube keyboard search")


# Temporary inspection for search-input bug diagnosis.
_s = presentation_path.read_text(encoding="utf-8")
for _needle in [
    "private fun buildSearchOverlay",
    "searchInput = EditText",
    "fun addChar",
    "private fun addChar",
    "setOnTouchListener",
    "showSearchOverlay()",
]:
    _i = _s.find(_needle)
    print("\n===== SEARCH DEBUG:", _needle, "=====")
    if _i >= 0:
        print(_s[max(0, _i - 2500): min(len(_s), _i + 8500)])
    else:
        print("MISSING")
