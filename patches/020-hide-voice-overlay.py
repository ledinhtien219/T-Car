from pathlib import Path
import re

ROOT = Path("/tmp/tcar")

# Hide only the floating voice/search banner on the car screen.
# Recognition and search still run normally in the background.
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarPresentation.kt"
car = car_path.read_text(encoding="utf-8")

car = re.sub(
    r'(searchOverlay\.visibility\s*=\s*)View\.VISIBLE',
    r'\1View.GONE',
    car
)

marker = 'addView(searchOverlay)'
if marker in car and 'searchOverlay.visibility = View.GONE // hidden on car' not in car:
    car = car.replace(
        marker,
        marker + '\n        searchOverlay.visibility = View.GONE // hidden on car',
        1
    )

car_path.write_text(car, encoding="utf-8")
print("Kept voice search functional while hiding the floating car overlay")
