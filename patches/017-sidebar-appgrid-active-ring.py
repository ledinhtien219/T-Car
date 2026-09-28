from pathlib import Path
p=Path("/tmp/tcar/app/src/main/java/com/carhud/aaproxy/CarPresentation.kt")
s=p.read_text(encoding="utf-8")
start=s.find("    private fun rebuildSidebar(")
if start < 0:
    start=s.find("    fun rebuildSidebar(")
if start < 0:
    raise RuntimeError("rebuildSidebar not found")
# find next top-level function after it
nexts=[]
for marker in ["\n    private fun ", "\n    fun ", "\n    override fun "]:
    pos=s.find(marker,start+10)
    if pos>start: nexts.append(pos)
end=min(nexts) if nexts else min(len(s), start+12000)
segment=s[start:end]
print("===== REBUILD_SIDEBAR_SOURCE =====")
print(segment)
print("===== END_REBUILD_SIDEBAR_SOURCE =====")
raise RuntimeError("DEBUG_ONLY_CAPTURE_REBUILD_SIDEBAR")
