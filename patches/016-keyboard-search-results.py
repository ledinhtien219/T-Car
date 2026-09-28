from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Split keyboard search from voice autoplay.
# Keyboard search must only show results immediately.
# Voice search may still auto-open the first result.
# ---------------------------------------------------------------------------
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

old_sig = "    fun search(view: WebView?, query: String) {\n"
if old_sig not in yt:
    raise RuntimeError("YouTubePlayerHelper.search() not found")

# Keep the existing autoplay implementation, but give it a voice-specific name.
yt = yt.replace(old_sig, "    fun searchAndPlay(view: WebView?, query: String) {\n", 1)

search_only = r'''    fun search(view: WebView?, query: String) {
        if (view == null) return
        val cleanQuery = query.trim()
        if (cleanQuery.isEmpty()) return

        view.post {
            try {
                val encoded = URLEncoder.encode(cleanQuery, "UTF-8")
                // Text/keyboard search should never wait for autoplay probing.
                // Open a plain mobile YouTube result page immediately.
                val targetUrl = "https://m.youtube.com/results?search_query=$encoded"
                if (view.url != targetUrl) {
                    view.loadUrl(targetUrl)
                } else {
                    view.reload()
                }
            } catch (e: Exception) {
                Log.e("YouTubePlayerHelper", "Text search navigation failed", e)
            }
        }
    }

'''

marker = "    fun searchAndPlay(view: WebView?, query: String) {\n"
yt = replace_once(yt, marker, search_only + marker, "insert text search function")
yt_path.write_text(yt, encoding="utf-8")

# ---------------------------------------------------------------------------
# The two result handlers below are voice-recognition paths. Point only those
# to searchAndPlay(); all existing keyboard/text calls keep using search().
# ---------------------------------------------------------------------------
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")
def replace_voice_search_call(text: str, hint: str, label: str) -> str:
    needle = "YouTubePlayerHelper.search(web, query)"
    positions = []
    start = 0
    while True:
        pos = text.find(needle, start)
        if pos < 0:
            break
        positions.append(pos)
        start = pos + len(needle)

    if not positions:
        raise RuntimeError(f"No search(web, query) call found: {label}")

    # Prefer the occurrence inside the voice-result handler.
    for pos in positions:
        nearby = text[max(0, pos - 900): min(len(text), pos + 900)]
        if hint in nearby:
            return text[:pos] + "YouTubePlayerHelper.searchAndPlay(web, query)" + text[pos + len(needle):]

    # If this file has only one query-call, it is the voice result path.
    if len(positions) == 1:
        pos = positions[0]
        return text[:pos] + "YouTubePlayerHelper.searchAndPlay(web, query)" + text[pos + len(needle):]

    raise RuntimeError(f"Could not identify voice search call: {label}; count={len(positions)}")

car = replace_voice_search_call(
    car,
    "dispatchSuccess",
    "CarPresentation voice search call"
)
car_path.write_text(car, encoding="utf-8")

main_path = ROOT / "app/src/main/java/com/carhud/aaproxy/MainActivity.kt"
main = main_path.read_text(encoding="utf-8")
main = replace_voice_search_call(
    main,
    "VoiceSearchManager already emitted SUCCESS",
    "MainActivity voice search call"
)
main_path.write_text(main, encoding="utf-8")

print("Applied v0.8.165 split keyboard search from voice autoplay")
