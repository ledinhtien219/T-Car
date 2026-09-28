from pathlib import Path
ROOT=Path("/tmp/tcar")

def show(path, max_chars=24000):
    p=ROOT/path
    print("\n===== "+path+" =====")
    if not p.exists():
        print("MISSING")
        return
    s=p.read_text(encoding="utf-8", errors="replace")
    print(s[:max_chars])

show("settings.gradle.kts", 12000)
show("build.gradle.kts", 12000)
show("app/build.gradle.kts", 24000)
show("app/src/main/AndroidManifest.xml", 30000)
show("app/src/main/res/xml/automotive_app_desc.xml", 12000)
show("app/src/main/java/com/carhud/aaproxy/CarMediaBrowserService.kt", 30000)
show("app/src/main/java/com/carhud/aaproxy/CarMediaManager.kt", 18000)
raise RuntimeError("INSPECT_MEDIA_SPLIT_ONLY")
