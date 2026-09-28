from pathlib import Path

path = Path("/tmp/tcar/app/src/main/java/com/carhud/aaproxy/CarPresentation.kt")
text = path.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global text
    if old not in text:
        raise RuntimeError("Missing expected source block: " + label)
    text = text.replace(old, new, 1)

# Keep a reference so the button can reflect App Grid open/closed state.
field_anchor = "    private var appGridOverlay: FrameLayout? = null\n"
if "private var appGridButton: ImageView? = null" not in text:
    replace_once(
        field_anchor,
        field_anchor + "    private var appGridButton: ImageView? = null\n",
        "app grid button field"
    )

# Grid button is neutral by default; the cyan circle is reserved for active state.
old_bg = '''            background = rounded(
                if (isDay) Color.parseColor("#E0F2FE") else Color.parseColor("#1E3B5A"),
                999f,
                if (isDay) Color.parseColor("#0284C7") else Color.parseColor("#00E5FF"),
                2
            )
'''
new_bg = '''            background = rounded(
                Color.TRANSPARENT,
                999f,
                Color.TRANSPARENT,
                0
            )
'''
replace_once(old_bg, new_bg, "grid default active background")

# Store the newly rebuilt button.
if "appGridButton = gridBtn" not in text:
    marker = "        toolbar.addView(gridBtn)\n"
    if marker not in text:
        # Fallback: insert just before the first app separator/addView after gridBtn.
        marker = "        // 2."
        pos = text.find(marker, text.find("val gridBtn = ImageView(context).apply"))
        if pos < 0:
            raise RuntimeError("Could not locate grid button insertion point")
        text = text[:pos] + "        appGridButton = gridBtn\n        updateAppGridButtonActive(appGridOverlay?.visibility == View.VISIBLE)\n\n" + text[pos:]
    else:
        text = text.replace(
            marker,
            "        appGridButton = gridBtn\n        updateAppGridButtonActive(appGridOverlay?.visibility == View.VISIBLE)\n        toolbar.addView(gridBtn)\n",
            1
        )

helper_anchor = '''    fun toggleAppGridOverlay() {
'''
if "private fun updateAppGridButtonActive(active: Boolean)" not in text:
    helper = '''    private fun updateAppGridButtonActive(active: Boolean) {
        val button = appGridButton ?: return
        val day = isDayMode()
        button.background = if (active) {
            rounded(
                if (day) Color.parseColor("#E0F2FE") else Color.parseColor("#1E3B5A"),
                999f,
                if (day) Color.parseColor("#0284C7") else Color.parseColor("#00E5FF"),
                2
            )
        } else {
            rounded(Color.TRANSPARENT, 999f, Color.TRANSPARENT, 0)
        }
    }

'''
    replace_once(helper_anchor, helper + helper_anchor, "grid active helper")

show_anchor = '''        rebuildAppGrid()
        appGridOverlay?.visibility = View.VISIBLE
'''
replace_once(
    show_anchor,
    '''        rebuildAppGrid()
        updateAppGridButtonActive(true)
        appGridOverlay?.visibility = View.VISIBLE
''',
    "grid active on show"
)

hide_anchor = '''    fun hideAppGridOverlay() {
        appGridOverlay?.animate()?.alpha(0f)?.setDuration(200)?.withEndAction {
'''
replace_once(
    hide_anchor,
    '''    fun hideAppGridOverlay() {
        updateAppGridButtonActive(false)
        appGridOverlay?.animate()?.alpha(0f)?.setDuration(200)?.withEndAction {
''',
    "grid inactive on hide"
)

path.write_text(text, encoding="utf-8")
print("App Grid active ring now appears only while the grid overlay is open")
