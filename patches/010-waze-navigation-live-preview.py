from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Waze navigation: prefer the maneuver Waze actually sends and keep numeric
# turn codes only as a compatibility fallback.
# ---------------------------------------------------------------------------
ws_path = ROOT / "app/src/main/java/com/carhud/aaproxy/WazeHlpWebSocketManager.kt"
ws = ws_path.read_text(encoding="utf-8")

old_action = '''            val rawTurnAction = firstString(json, "nextTurnAction", "turnAction", "turn_action", "maneuver", "action")
            val nextTurnAction = when (turnCode) {
                2, 9 -> "turn-left"
                3, 10 -> "turn-right"
                4, 12 -> "slight-left"
                5, 13 -> "slight-right"
                6, 7 -> "roundabout"
                8 -> "u-turn"
                11 -> "destination"
                else -> rawTurnAction ?: "straight"
            }
'''
new_action = '''            val rawTurnAction = firstString(
                json,
                "nextTurnAction", "turnAction", "turn_action", "maneuver", "nextManeuver",
                "next_maneuver", "navAction", "nav_action", "turnType", "turn_type", "action"
            )
            val normalizedWazeAction = rawTurnAction
                ?.lowercase()
                ?.trim()
                ?.replace('_', '-')
                ?.replace(' ', '-')
                ?.replace(Regex("-+"), "-")

            // Prefer Waze's own maneuver text. Numeric turn-code mapping is only
            // a fallback for HLP frames that do not contain an action string.
            val nextTurnAction = when {
                !normalizedWazeAction.isNullOrBlank() -> when {
                    normalizedWazeAction.contains("sharp-left") -> "sharp-left"
                    normalizedWazeAction.contains("sharp-right") -> "sharp-right"
                    normalizedWazeAction.contains("slight-left") || normalizedWazeAction.contains("keep-left") -> "slight-left"
                    normalizedWazeAction.contains("slight-right") || normalizedWazeAction.contains("keep-right") -> "slight-right"
                    normalizedWazeAction.contains("exit-left") -> "exit-left"
                    normalizedWazeAction.contains("exit-right") -> "exit-right"
                    normalizedWazeAction.contains("u-turn") || normalizedWazeAction.contains("uturn") -> "u-turn"
                    normalizedWazeAction.contains("roundabout") || normalizedWazeAction.contains("traffic-circle") -> "roundabout"
                    normalizedWazeAction.contains("destination") || normalizedWazeAction.contains("arrive") -> "destination"
                    normalizedWazeAction.contains("left") -> "turn-left"
                    normalizedWazeAction.contains("right") -> "turn-right"
                    normalizedWazeAction.contains("straight") || normalizedWazeAction.contains("continue") -> "straight"
                    else -> normalizedWazeAction
                }
                else -> when (turnCode) {
                    2, 9 -> "turn-left"
                    3, 10 -> "turn-right"
                    4, 12 -> "slight-left"
                    5, 13 -> "slight-right"
                    6, 7 -> "roundabout"
                    8 -> "u-turn"
                    11 -> "destination"
                    else -> "straight"
                }
            }
'''
ws = replace_once(ws, old_action, new_action, "Waze maneuver action priority")

# Parse either numeric Waze distances or strings such as "250 m" / "1.2 km".
helper_anchor = '''    private fun firstFloat(json: JSONObject, vararg keys: String): Float? {
        for (key in keys) {
            if (!json.has(key) || json.isNull(key)) continue
            val raw = json.opt(key)
            val value = when (raw) {
                is Number -> raw.toFloat()
                is String -> raw.trim().replace(',', '.').toFloatOrNull()
                else -> null
            }
            if (value != null) return value
        }
        return null
    }

'''
helper_block = helper_anchor + '''    private fun firstDistanceMeters(json: JSONObject, vararg keys: String): Int? {
        for (key in keys) {
            if (!json.has(key) || json.isNull(key)) continue
            val raw = json.opt(key)
            val meters = when (raw) {
                is Number -> raw.toDouble().toInt()
                is String -> {
                    val cleaned = raw.trim().lowercase().replace(',', '.')
                    val number = Regex("""(\\d+(?:\\.\\d+)?)""")
                        .find(cleaned)
                        ?.groupValues
                        ?.getOrNull(1)
                        ?.toDoubleOrNull()
                    when {
                        number == null -> null
                        cleaned.contains("km") -> (number * 1000.0).toInt()
                        else -> number.toInt()
                    }
                }
                else -> null
            }
            if (meters != null) return meters
        }
        return null
    }

'''
ws = replace_once(ws, helper_anchor, helper_block, "Waze distance parser helper")

ws = ws.replace(
    'val turnDistancePresent = hasAny(json, "distanceToTurnMeters", "dst", "distance_meters", "dist_m", "dist")',
    'val turnDistancePresent = hasAny(json, "distanceToTurnMeters", "distanceToTurn", "turnDistance", "turn_distance", "dst", "distance_meters", "dist_m", "dist")'
)
ws = ws.replace(
    'val distanceToTurnMeters = firstInt(json, "distanceToTurnMeters", "dst", "distance_meters", "dist_m", "dist")',
    'val distanceToTurnMeters = firstDistanceMeters(json, "distanceToTurnMeters", "distanceToTurn", "turnDistance", "turn_distance", "dst", "distance_meters", "dist_m", "dist")'
)
ws_path.write_text(ws, encoding="utf-8")

# ---------------------------------------------------------------------------
# HUD: use Waze action first, show distance directly below the arrow in every
# HUD style, and remove fake 60/65 preview telemetry.
# ---------------------------------------------------------------------------
hud_path = ROOT / "app/src/main/java/com/carhud/aaproxy/VietmapHudOverlay.kt"
hud = hud_path.read_text(encoding="utf-8")

# Do not seed style previews with fake speed-limit numbers.
hud = hud.replace('text = "60"', 'text = "--"')
hud = hud.replace('text = if (isPreviewMode) "60" else "--"', 'text = "--"')
hud = hud.replace(
    'speedLimitText?.text = if (isPreviewMode) "0" else "--"',
    'speedLimitText?.text = "--"'
)

old_secondary = '''        } else {
            if (activeStyleId == 2 || activeStyleId == 3 || activeStyleId == 4) {
                if (isPreviewMode) {
                    secondaryLimitText?.text = "--"
                    secondaryLimitBadge?.visibility = VISIBLE
                } else {
                    secondaryLimitBadge?.visibility = GONE
                }
            } else {
                secondaryLimitBadge?.visibility = GONE
            }
        }
'''
new_secondary = '''        } else {
            secondaryLimitBadge?.visibility = GONE
        }
'''
hud = replace_once(hud, old_secondary, new_secondary, "secondary preview limit")

# Style 1: change horizontal arrow/distance into arrow-over-distance.
s = hud.index("        // 4. Turn Cyan Box + Distance")
e = hud.index("        // 4.5 Active Alert Badge", s)
seg = hud[s:e]
seg = replace_once(seg, "            orientation = HORIZONTAL\n", "            orientation = VERTICAL\n", "style1 turn orientation")
seg = replace_once(seg, "            gravity = Gravity.CENTER_VERTICAL\n", "            gravity = Gravity.CENTER\n", "style1 turn gravity")
seg = replace_once(
    seg,
    "                layoutParams = LayoutParams(size, size).apply { marginEnd = dp(6) }\n",
    "                layoutParams = LayoutParams(size, size).apply { bottomMargin = dp(1) }\n",
    "style1 turn margin"
)
seg = replace_once(
    seg,
    '                setTextColor(Color.parseColor("#38BDF8"))\n            }\n',
    '                setTextColor(Color.parseColor("#38BDF8"))\n                gravity = Gravity.CENTER\n            }\n',
    "style1 distance gravity"
)
hud = hud[:s] + seg + hud[e:]

# Style 2: arrow above distance; ETA remains below the maneuver block.
s = hud.index("        // 5. Nav Info: Turn arrow + Distance, ETA + Distance")
e = hud.index("        // 5.5 Active Alert Badge", s)
seg = hud[s:e]
seg = replace_once(seg, "                orientation = HORIZONTAL\n", "                orientation = VERTICAL\n", "style2 turn orientation")
seg = replace_once(seg, "                gravity = Gravity.CENTER_VERTICAL\n", "                gravity = Gravity.CENTER\n", "style2 turn gravity")
seg = replace_once(
    seg,
    "                    setPadding(0, 0, dp(3), 0)\n",
    "                    gravity = Gravity.CENTER\n                    setPadding(0, 0, 0, dp(1))\n",
    "style2 icon layout"
)
seg = replace_once(
    seg,
    '                    setTextColor(Color.parseColor("#38BDF8"))\n                }\n',
    '                    setTextColor(Color.parseColor("#38BDF8"))\n                    gravity = Gravity.CENTER\n                }\n',
    "style2 distance gravity"
)
hud = hud[:s] + seg + hud[e:]

# Style 5 had no maneuver at all. Add a compact Waze arrow + distance column.
style5_anchor = '''        // 4. Vertical Divider
        addView(createVerticalDivider())

        // 5. Lock / Unlock Button
'''
style5_nav = '''        // 4. Vertical Divider
        addView(createVerticalDivider())

        // 5. Waze maneuver: arrow with distance directly underneath
        val compactTurn = LinearLayout(context).apply {
            orientation = VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(5), 0, dp(5), 0)

            turnIcon = TextView(context).apply {
                text = "↑"
                textSize = 20f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#38BDF8"))
                gravity = Gravity.CENTER
            }
            addView(turnIcon)

            turnDistanceText = TextView(context).apply {
                text = ""
                textSize = 10.5f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.parseColor("#38BDF8"))
                gravity = Gravity.CENTER
            }
            addView(turnDistanceText)
        }
        turnContainer = compactTurn
        addView(compactTurn)

        addView(createVerticalDivider())

        // 6. Lock / Unlock Button
'''
hud = replace_once(hud, style5_anchor, style5_nav, "style5 Waze maneuver")

old_arrow = '''        // 3. Turn Arrow & Distance (QCVN 41:2019/BGTVT traffic standards)
        val arrowStr = when {
            data.turnCode in listOf(2, 9) || data.turnAction in listOf("turn-left", "sharp-left", "left") -> "↰"
            data.turnCode in listOf(3, 10) || data.turnAction in listOf("turn-right", "sharp-right", "right") -> "↱"
            data.turnCode in listOf(4, 12) || data.turnAction in listOf("slight-left", "keep-left", "exit-left") -> "↖"
            data.turnCode in listOf(5, 13) || data.turnAction in listOf("slight-right", "keep-right", "exit-right") -> "↗"
            data.turnCode == 8 || data.turnAction in listOf("u-turn", "uturn") -> "↩"
            data.turnCode in listOf(6, 7) || data.turnAction == "roundabout" -> "🔄"
            data.turnCode == 11 || data.turnAction == "destination" -> "🏁"
            else -> "↑"
        }
        turnIcon?.text = arrowStr
'''
new_arrow = '''        // 3. Turn Arrow & Distance. Waze maneuver text is primary because it
        // distinguishes keep/exit/sharp turns better than a coarse numeric code.
        val wazeManeuver = listOfNotNull(data.turnAction, data.turnDescription)
            .joinToString(" ")
            .lowercase(Locale.ROOT)
            .replace('_', '-')
        val arrowStr = when {
            wazeManeuver.contains("sharp-left") || wazeManeuver.contains("rẽ gắt sang trái") -> "↶"
            wazeManeuver.contains("sharp-right") || wazeManeuver.contains("rẽ gắt sang phải") -> "↷"
            wazeManeuver.contains("exit-left") || wazeManeuver.contains("slight-left") ||
                wazeManeuver.contains("keep-left") || wazeManeuver.contains("chếch sang trái") -> "↖"
            wazeManeuver.contains("exit-right") || wazeManeuver.contains("slight-right") ||
                wazeManeuver.contains("keep-right") || wazeManeuver.contains("chếch sang phải") -> "↗"
            wazeManeuver.contains("u-turn") || wazeManeuver.contains("uturn") ||
                wazeManeuver.contains("quay đầu") -> "↩"
            wazeManeuver.contains("roundabout") || wazeManeuver.contains("traffic-circle") ||
                wazeManeuver.contains("vòng xuyến") || wazeManeuver.contains("bùng binh") ->
                if (data.turnCode == 7) "⟲" else "⟳"
            wazeManeuver.contains("destination") || wazeManeuver.contains("arrive") ||
                wazeManeuver.contains("đến nơi") -> "🏁"
            wazeManeuver.contains("turn-left") || wazeManeuver.contains("rẽ trái") ||
                data.turnCode in listOf(2, 9) -> "↰"
            wazeManeuver.contains("turn-right") || wazeManeuver.contains("rẽ phải") ||
                data.turnCode in listOf(3, 10) -> "↱"
            data.turnCode in listOf(4, 12) -> "↖"
            data.turnCode in listOf(5, 13) -> "↗"
            data.turnCode == 8 -> "↩"
            data.turnCode in listOf(6, 7) -> if (data.turnCode == 7) "⟲" else "⟳"
            data.turnCode == 11 -> "🏁"
            else -> "↑"
        }
        turnIcon?.text = arrowStr
'''
hud = replace_once(hud, old_arrow, new_arrow, "Waze-driven arrow")

old_has_maneuver = '''        val hasManeuver = data.turnCode > 0 ||
            data.distanceToTurnMeters > 0 ||
            !data.turnDescription.isNullOrBlank() ||
            !data.nextRoadName.isNullOrBlank()
'''
new_has_maneuver = '''        val hasManeuver = data.turnCode > 0 ||
            data.distanceToTurnMeters > 0 ||
            (!data.turnAction.isBlank() && data.turnAction != "straight") ||
            !data.turnDescription.isNullOrBlank() ||
            !data.nextRoadName.isNullOrBlank()
'''
hud = replace_once(hud, old_has_maneuver, new_has_maneuver, "maneuver visibility")

old_preview = '''        val testData = VietmapAlertData(
            isConnected = true,
            currentSpeed = 65,
            speedLimit = 60,
            secondarySpeedLimit = 50,
            distanceText = "250m",
            distanceToTurnMeters = 250,
            turnAction = "straight",
            turnDescription = "Đi thẳng",
            warningType = VietmapWarningType.RESIDENTIAL_START,
            alertTitle = "Bắt đầu khu dân cư",
            roadName = "Quốc lộ 1A",
            etaTime = "14:25",
            remainingDistanceKm = 12.0f,
            isOverSpeed = true
        )
'''
new_preview = '''        val live = VietmapStateRepository.alertState.value
        val testData = VietmapAlertData(
            isConnected = live.isConnected,
            currentSpeed = live.currentSpeed,
            speedLimit = live.speedLimit,
            secondarySpeedLimit = live.secondarySpeedLimit,
            turnCode = live.turnCode,
            turnAction = live.turnAction,
            turnDescription = live.turnDescription,
            distanceToTurnMeters = live.distanceToTurnMeters,
            distanceText = "250m",
            distanceMeters = 250,
            warningType = VietmapWarningType.RESIDENTIAL_START,
            alertTitle = "Bắt đầu khu dân cư",
            roadName = live.roadName,
            nextRoadName = live.nextRoadName,
            etaTime = live.etaTime,
            remainingDistanceKm = live.remainingDistanceKm,
            isOverSpeed = live.speedLimit?.let { live.currentSpeed > it } ?: false
        )
'''
hud = replace_once(hud, old_preview, new_preview, "live HUD preview")
hud_path.write_text(hud, encoding="utf-8")

# ---------------------------------------------------------------------------
# Manual alert tests must not overwrite live Waze speed/limit with 65/60.
# Overspeed's dedicated test case still has its own explicit test speed.
# ---------------------------------------------------------------------------
settings_path = ROOT / "app/src/main/java/com/carhud/aaproxy/SettingsActivity.kt"
settings = settings_path.read_text(encoding="utf-8")
settings = replace_once(
    settings,
    '''                                    distanceText = tc.distText,
                                    distanceMeters = tc.distMeters,
                                    speed = 65,
                                    limit = 60,
                                    source = "MANUAL_TEST"
''',
    '''                                    distanceText = tc.distText,
                                    distanceMeters = tc.distMeters,
                                    source = "MANUAL_TEST"
''',
    "manual test fake 65/60"
)
settings_path.write_text(settings, encoding="utf-8")

print("Applied Waze-live maneuver arrows, below-arrow distance, and live HUD test telemetry")
