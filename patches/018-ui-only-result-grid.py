from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# UI ONLY.
# Search, voice, result-click and playback behavior are intentionally left
# exactly as they were in v0.8.164 (patches 001..015).
# ---------------------------------------------------------------------------

# 1) Keep TV/IPTV channel artwork fully visible in the dashboard.
layout_path = ROOT / "app/src/main/res/layout/dashboard.xml"
layout = layout_path.read_text(encoding="utf-8")
layout = replace_once(
    layout,
    '''                    <ImageView
                        android:id="@+id/mediaAlbumImageView"
                        android:layout_width="match_parent"
                        android:layout_height="match_parent"
                        android:contentDescription="@null"
                        android:scaleType="centerCrop"
                        android:visibility="gone"
                        tools:src="@android:drawable/ic_media_play"
                        tools:visibility="visible" />''',
    '''                    <ImageView
                        android:id="@+id/mediaAlbumImageView"
                        android:layout_width="match_parent"
                        android:layout_height="match_parent"
                        android:contentDescription="@null"
                        android:padding="2dp"
                        android:scaleType="fitCenter"
                        android:visibility="gone"
                        tools:src="@android:drawable/ic_media_play"
                        tools:visibility="visible" />''',
    "dashboard media artwork ImageView",
)
layout_path.write_text(layout, encoding="utf-8")

dashboard_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarDashboardView.kt"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = replace_once(
    dashboard,
    '''                if (track.artworkBitmap != null) {
                    mediaAlbumImageView.setImageBitmap(track.artworkBitmap)
                    mediaAlbumImageView.visibility = VISIBLE
                    mediaAlbumIcon.visibility = View.GONE
                } else {
                    mediaAlbumImageView.visibility = View.GONE
                    mediaAlbumIcon.visibility = View.VISIBLE
                }''',
    '''                if (track.artworkBitmap != null) {
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
                }''',
    "dashboard artwork rendering",
)
dashboard_path.write_text(dashboard, encoding="utf-8")

# 2) Results-page presentation only: 3 columns on wide car screens.
# No click/focus/touch listeners are added here.
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

old_result_style = '''            // Make fallback result lists readable on wide head units. This only
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
            } catch(e) {}'''

new_result_style = '''            // Presentation only: 3-column search result grid on landscape displays.
            try {
                var style = document.getElementById('carhud-search-results-style');
                if (!style) {
                    style = document.createElement('style');
                    style.id = 'carhud-search-results-style';
                    style.textContent = [
                        'ytm-item-section-renderer > lazy-list,ytm-section-list-renderer > lazy-list,.rich-grid-renderer-contents{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:12px!important;padding:10px!important;box-sizing:border-box!important;width:100%!important;}',
                        'ytm-video-with-context-renderer,ytm-compact-video-renderer,ytm-rich-item-renderer,.media-item{display:flex!important;flex-direction:column!important;width:100%!important;min-width:0!important;margin:0!important;padding:0!important;}',
                        '.media-item-thumbnail-container,ytm-thumbnail-cover,.video-thumbnail-container-compact{width:100%!important;max-width:100%!important;aspect-ratio:16/9!important;border-radius:10px!important;overflow:hidden!important;}',
                        '.media-item-thumbnail-container img,ytm-thumbnail-cover img,.video-thumbnail-container-compact img{width:100%!important;height:100%!important;object-fit:cover!important;}',
                        '.compact-media-item-headline,.media-item-headline,.video-title,h3.title{font-size:16px!important;line-height:1.25!important;font-weight:650!important;max-height:2.5em!important;-webkit-line-clamp:2!important;display:-webkit-box!important;-webkit-box-orient:vertical!important;overflow:hidden!important;margin-top:6px!important;}',
                        'ytd-search ytd-item-section-renderer > #contents{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:12px!important;padding:10px!important;box-sizing:border-box!important;}',
                        'ytd-search ytd-video-renderer{display:block!important;width:100%!important;min-width:0!important;margin:0!important;}',
                        'ytd-search ytd-video-renderer #dismissible{display:flex!important;flex-direction:column!important;width:100%!important;}',
                        'ytd-search ytd-video-renderer ytd-thumbnail,ytd-search ytd-video-renderer #thumbnail{width:100%!important;min-width:0!important;max-width:100%!important;aspect-ratio:16/9!important;border-radius:10px!important;overflow:hidden!important;}',
                        'ytd-search ytd-video-renderer #meta{width:100%!important;margin:0!important;padding:6px 3px 10px!important;box-sizing:border-box!important;}',
                        'ytd-search ytd-video-renderer #video-title{font-size:16px!important;line-height:1.25!important;font-weight:650!important;}'
                    ].join('');
                    (document.head || document.documentElement).appendChild(style);
                }
                document.documentElement.style.zoom = '1';
            } catch(e) {}'''

yt = replace_once(yt, old_result_style, new_result_style, "three-column results UI")
yt_path.write_text(yt, encoding="utf-8")

# Guardrails: this patch must stay UI-only.
final_yt = yt_path.read_text(encoding="utf-8")
for forbidden in (
    "carhudFindVideoLink",
    "__carhudSuppressSearchUntil",
    "requestCarNativeSearch",
    "queuePendingCarSearch",
):
    if forbidden in final_yt:
        raise RuntimeError(f"Unexpected post-164 search override found in YouTube helper: {forbidden}")

print("Applied UI-only dashboard/logo + 3-column results; v0.8.164 search behavior preserved")
