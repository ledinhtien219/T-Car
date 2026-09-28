from pathlib import Path
p=Path("/tmp/tcar/app/src/main/java/com/carhud/aaproxy/CarPresentation.kt")
s=p.read_text(encoding="utf-8")
needles=["webAppPos","rebuildTopToolbar","WebApp","appGrid","app grid","grid","dock","ic_bar_apps","ic_apps","showApp","App Grid"]
for n in needles:
    print("\n===== NEEDLE:", n, "=====")
    start=0
    hits=0
    while True:
        i=s.find(n,start)
        if i<0: break
        hits+=1
        print(s[max(0,i-1200):min(len(s),i+2400)])
        start=i+len(n)
        if hits>=6: break
raise RuntimeError("INSPECT_APP_GRID_ONLY")
