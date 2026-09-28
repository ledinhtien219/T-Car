from pathlib import Path

ROOT = Path("/tmp/tcar")

def around(rel, needle, radius=4500):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8", errors="replace")
    i = s.find(needle)
    print("\n===== INSPECT", rel, "::", needle, "=====")
    if i < 0:
        print("MISSING")
    else:
        print(s[max(0, i-radius): min(len(s), i+len(needle)+radius)])

around("app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt", "openSearchKeyboard", 9000)
around("app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt", "function inject", 9000)
around("app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt", "fun inject", 9000)
around("app/src/main/res/layout/dashboard.xml", "mediaAlbumImageView", 4000)
around("app/src/main/res/layout/dashboard.xml", "mediaAlbumArt", 5000)
around("app/src/main/java/com/carhud/aaproxy/CarDashboardView.kt", "lateinit var mediaAlbumImageView", 2500)
print("INSPECT_SEARCH_ART_ONLY")
