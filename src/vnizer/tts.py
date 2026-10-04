"""Adapt the local Qwen and external Supertonic speech contracts."""

import io
import wave


def api_base(url):
    base = url.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def service_type(settings):
    value = settings.get("tts_type", "qwen")
    if value not in ("qwen", "supertonic"):
        raise ValueError("Select qwen or supertonic as the TTS type.")
    return value


def language_code(language):
    names = {
        "english": "en", "indonesian": "id", "spanish": "es", "french": "fr",
        "portuguese": "pt", "korean": "ko", "german": "de", "italian": "it",
        "japanese": "ja", "chinese": "zh", "russian": "ru",
    }
    return names.get(language.lower(), language.lower())


def speech_request(settings, chunk):
    if service_type(settings) == "supertonic":
        return api_base(settings["tts_url"]) + "/audio/speech", {
            "text": chunk["text"], "voice": settings["speaker"],
            "lang": language_code(settings["language"]),
        }
    return settings["tts_url"].rstrip("/") + "/speech", {
        "text": chunk["text"], "mood": chunk["mood"],
        "speaker": settings["speaker"], "language": settings["language"],
    }


def pcm_to_wav(data, sample_rate):
    if sample_rate != "24000":
        raise ValueError("Supertonic must return PCM at 24000 Hz.")
    if not data or len(data) % 2 or len(data) > 24000 * 2 * 180:
        raise ValueError("Supertonic must return complete PCM16 samples of at most 180 seconds.")
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(data)
    return output.getvalue()
