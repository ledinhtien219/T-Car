from pathlib import Path

ROOT = Path("/tmp/tcar")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected source block: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# 1) Replace ToneGenerator with deterministic PCM AudioTrack warning sounds.
# ---------------------------------------------------------------------------
car_path = ROOT / "app/src/main/java/com/carhud/aaproxy/CarTtsManager.kt"
car = car_path.read_text(encoding="utf-8")

car = replace_once(
    car,
    "import android.media.AudioAttributes\nimport android.media.AudioManager\nimport android.media.ToneGenerator\n",
    "import android.media.AudioAttributes\nimport android.media.AudioFormat\nimport android.media.AudioManager\nimport android.media.AudioTrack\n",
    "CarTtsManager audio imports",
)

if "import kotlin.math.PI" not in car:
    car = replace_once(
        car,
        "import java.util.Locale\n",
        "import java.util.Locale\nimport kotlin.math.PI\nimport kotlin.math.sin\n",
        "CarTtsManager math imports",
    )

car = replace_once(
    car,
    "    private var tts: TextToSpeech? = null\n    private var toneGenerator: ToneGenerator? = null\n    private var toneSequenceJob: Job? = null\n",
    "    private var tts: TextToSpeech? = null\n    @Volatile private var alertAudioTrack: AudioTrack? = null\n    private var toneSequenceJob: Job? = null\n",
    "CarTtsManager audio fields",
)

start = car.find("    fun playAlertTone(isPriority: Boolean = false) {")
end = car.find("    fun speakAlert(text: String, isPriority: Boolean = false) {", start)
if start < 0 or end < 0:
    raise RuntimeError("Could not locate playAlertTone/speakAlert boundary")

new_alert_engine = r'''    fun playAlertTone(isPriority: Boolean = false) {
        val now = System.currentTimeMillis()
        if (!isPriority && now - lastToneTime < TONE_COOLDOWN_MS) return
        lastToneTime = now

        val ctx = appContext
        val toneStyle = ctx?.let { WazeHudManager.getAlertToneStyle(it) }
            ?: WazeHudManager.ALERT_TONE_BEEP

        toneSequenceJob?.cancel()
        releaseAlertAudioTrack()

        toneSequenceJob = scope.launch(Dispatchers.Default) {
            var localTrack: AudioTrack? = null
            try {
                // Generate our own PCM instead of ToneGenerator presets. Several
                // phones/head units map TONE_PROP_* presets to nearly identical
                // sounds. These patterns differ in BOTH pitch and rhythm.
                //
                // Every style uses the same peak amplitude. Critical alerts bypass
                // the cooldown but do not get louder, so media volume does not pump.
                val segments: List<Triple<Double, Int, Int>> = when (toneStyle) {
                    WazeHudManager.ALERT_TONE_DOUBLE_BEEP -> listOf(
                        Triple(740.0, 95, 80),
                        Triple(1120.0, 95, 0)
                    )
                    WazeHudManager.ALERT_TONE_ACK -> listOf(
                        Triple(1280.0, 70, 55),
                        Triple(960.0, 70, 55),
                        Triple(1280.0, 105, 0)
                    )
                    WazeHudManager.ALERT_TONE_PROMPT -> listOf(
                        Triple(620.0, 260, 90),
                        Triple(1080.0, 90, 0)
                    )
                    WazeHudManager.ALERT_TONE_STRONG -> listOf(
                        Triple(520.0, 120, 75),
                        Triple(760.0, 120, 75),
                        Triple(980.0, 300, 0)
                    )
                    else -> listOf(
                        Triple(960.0, 120, 0)
                    )
                }

                val sampleRate = 44_100
                val peakAmplitude = 0.24
                val totalSamples = segments.sumOf { segment ->
                    (segment.second + segment.third) * sampleRate / 1000
                }.coerceAtLeast(1)

                val pcm = ShortArray(totalSamples)
                var cursor = 0

                for ((frequencyHz, durationMs, gapMs) in segments) {
                    val toneSamples = (durationMs * sampleRate / 1000).coerceAtLeast(1)
                    val fadeSamples = minOf(sampleRate / 200, toneSamples / 4).coerceAtLeast(1)

                    for (i in 0 until toneSamples) {
                        val envelope = when {
                            i < fadeSamples -> i.toDouble() / fadeSamples.toDouble()
                            i >= toneSamples - fadeSamples ->
                                (toneSamples - i - 1).coerceAtLeast(0).toDouble() / fadeSamples.toDouble()
                            else -> 1.0
                        }
                        val wave = sin(
                            2.0 * PI * frequencyHz * i.toDouble() / sampleRate.toDouble()
                        )
                        val value = (wave * Short.MAX_VALUE * peakAmplitude * envelope)
                            .toInt()
                            .coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt())

                        if (cursor < pcm.size) {
                            pcm[cursor++] = value.toShort()
                        }
                    }

                    val silenceSamples = gapMs * sampleRate / 1000
                    cursor = (cursor + silenceSamples).coerceAtMost(pcm.size)
                }

                val track = AudioTrack.Builder()
                    .setAudioAttributes(
                        AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build()
                    )
                    .setAudioFormat(
                        AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(sampleRate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build()
                    )
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .setBufferSizeInBytes(pcm.size * 2)
                    .build()

                localTrack = track
                alertAudioTrack = track

                val written = track.write(
                    pcm,
                    0,
                    pcm.size,
                    AudioTrack.WRITE_BLOCKING
                )
                if (written <= 0) {
                    Log.w(TAG, "Alert PCM write failed: $written")
                    return@launch
                }

                track.play()
                val totalDurationMs = segments.sumOf { it.second + it.third }.toLong()
                delay(totalDurationMs + 80L)
                Log.i(TAG, "Car alert PCM pattern: $toneStyle")
            } catch (e: Exception) {
                Log.e(TAG, "Alert tone failed", e)
            } finally {
                localTrack?.let { track ->
                    try { track.stop() } catch (_: Exception) {}
                    try { track.flush() } catch (_: Exception) {}
                    try { track.release() } catch (_: Exception) {}
                    if (alertAudioTrack === track) {
                        alertAudioTrack = null
                    }
                }
            }
        }
    }

    private fun releaseAlertAudioTrack() {
        val track = alertAudioTrack ?: return
        alertAudioTrack = null
        try { track.stop() } catch (_: Exception) {}
        try { track.flush() } catch (_: Exception) {}
        try { track.release() } catch (_: Exception) {}
    }

'''
car = car[:start] + new_alert_engine + car[end:]
car = car.replace("            toneGenerator?.release()\n", "            releaseAlertAudioTrack()\n")
car = car.replace("            toneGenerator = null\n", "            alertAudioTrack = null\n")

if "ToneGenerator" in car:
    raise RuntimeError("ToneGenerator reference remained after PCM conversion")

car_path.write_text(car, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2) Keep YouTube media volume consistent with the current ducking target.
#    Playback helpers previously forced volume=1.0 and could fight the voice
#    state callback, causing audible loud/quiet jumps.
# ---------------------------------------------------------------------------
yt_path = ROOT / "app/src/main/java/com/carhud/aaproxy/YouTubePlayerHelper.kt"
yt = yt_path.read_text(encoding="utf-8")

volume_replacements = [
    (
        "                        if (video.volume < 0.5) video.volume = 1.0;",
        "                        var targetVol = window.__carhudDuckingVolume !== undefined ? window.__carhudDuckingVolume : 1.0;\n"
        "                        if (Math.abs(video.volume - targetVol) > 0.05) video.volume = targetVol;",
        "aggressive play volume",
    ),
    (
        "                                    if (video.volume < 0.5) video.volume = 1.0;",
        "                                    var targetVol = window.__carhudDuckingVolume !== undefined ? window.__carhudDuckingVolume : 1.0;\n"
        "                                    if (Math.abs(video.volume - targetVol) > 0.05) video.volume = targetVol;",
        "resume volume",
    ),
    (
        "                                if (v.volume < 0.5) v.volume = 1.0;",
        "                                var targetVol = window.__carhudDuckingVolume !== undefined ? window.__carhudDuckingVolume : 1.0;\n"
        "                                if (Math.abs(v.volume - targetVol) > 0.05) v.volume = targetVol;",
        "first video volume",
    ),
    (
        "                            if (video.volume < 0.5) video.volume = 1.0;",
        "                            var targetVol = window.__carhudDuckingVolume !== undefined ? window.__carhudDuckingVolume : 1.0;\n"
        "                            if (Math.abs(video.volume - targetVol) > 0.05) video.volume = targetVol;",
        "safePlay volume",
    ),
    (
        "                        v.volume = 1.0;",
        "                        var targetVol = window.__carhudDuckingVolume !== undefined ? window.__carhudDuckingVolume : 1.0;\n"
        "                        if (Math.abs(v.volume - targetVol) > 0.05) v.volume = targetVol;",
        "next video volume",
    ),
]

for old, new, label in volume_replacements:
    yt = replace_once(yt, old, new, label)

yt = replace_once(
    yt,
    '''    fun setDuckingVolume(view: WebView?, volume: Float) {
        try {
            view?.evaluateJavascript(
                "try { window.__carhudDuckingVolume = $volume; var v = document.querySelector('video'); if (v) { v.volume = $volume; } } catch(e) {}",
''',
    '''    fun setDuckingVolume(view: WebView?, volume: Float) {
        val safeVolume = volume.coerceIn(0f, 1f)
        try {
            view?.evaluateJavascript(
                "try { var t = $safeVolume; window.__carhudDuckingVolume = t; var v = document.querySelector('video'); if (v && Math.abs(v.volume - t) > 0.02) { v.volume = t; } } catch(e) {}",
''',
    "setDuckingVolume",
)

yt_path.write_text(yt, encoding="utf-8")
print("Applied deterministic 5-tone PCM engine and stable WebView media volume")
