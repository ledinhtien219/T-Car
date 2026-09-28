from pathlib import Path

ROOT = Path("/tmp/tcar")

def dump_hits(rel, needles, radius=1800):
    p = ROOT / rel
    print("\n===== INSPECT", rel, "=====")
    s = p.read_text(encoding="utf-8", errors="replace")
    seen = []
    for needle in needles:
        start = 0
        while True:
            i = s.find(needle, start)
            if i < 0:
                break
            a = max(0, i - radius)
            b = min(len(s), i + len(needle) + radius)
            key = (a, b)
            if all(abs(a-x[0]) > 800 for x in seen):
                seen.append(key)
                print("\n--- HIT", needle, "@", i, "---")
                print(s[a:b])
            start = i + len(needle)
    if not seen:
        print("NO HITS")

dump_hits(
    "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt",
    [
        "KEY_SHOW_KEYBOARD_SEARCH",
        "searchRequestListener",
        "openSearchKeyboard",
        "PhoneSearchActivity",
        "showSearch",
        "YouTubePlayerHelper.search(",
        "startGlobalVoiceSearch",
    ],
    2400,
)

dump_hits(
    "app/src/main/java/com/carhud/aaproxy/MainActivity.kt",
    [
        "searchRequestListener",
        "PhoneSearchActivity",
        "showSearchOverlay",
        "YouTubePlayerHelper.search(",
        "EditText",
        "InputMethodManager",
    ],
    2400,
)

dump_hits(
    "app/src/main/java/com/carhud/aaproxy/PhoneSearchActivity.kt",
    [
        "class PhoneSearchActivity",
        "EditText",
        "setOnEditorActionListener",
        "InputMethodManager",
        "search",
    ],
    3200,
)

dump_hits(
    "app/src/main/java/com/carhud/aaproxy/CarDashboardView.kt",
    [
        "mediaAlbumArt",
        "mediaAlbumIcon",
        "trackState",
        "currentArtwork",
        "artwork",
        "Iptv",
        "VTV",
    ],
    3000,
)

dump_hits(
    "app/src/main/java/com/carhud/aaproxy/CarMediaManager.kt",
    [
        "currentArtwork",
        "updateTrack",
        "trackState",
        "Iptv",
        "channel",
        "logo",
        "artwork",
    ],
    3000,
)

print("INSPECT_UI_SEARCH_ONLY")
