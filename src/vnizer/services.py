import asyncio
import base64
import io

import httpx
from PIL import Image

from .tts import api_base, service_type


def ftt_base(url):
    base = url.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def headers(key):
    return {"Authorization": f"Bearer {key}"} if key else {}


async def check_services(settings):
    async def check_ftt(client):
        response = await client.get(ftt_base(settings["ftt_url"]) + "/models",
                                    headers=headers(settings.get("ftt_api_key")))
        response.raise_for_status()
        models = [item["id"] for item in response.json()["data"]]
        model = settings.get("ftt_model")
        if not models or (model and model not in models):
            raise ValueError("The configured FTT model is unavailable.")
        model = model or models[0]
        probe = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(probe, format="PNG")
        response = await client.post(ftt_base(settings["ftt_url"]) + "/chat/completions",
                                     headers=headers(settings.get("ftt_api_key")), json={
            "model": model, "max_tokens": 8,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Reply OK."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," +
                    base64.b64encode(probe.getvalue()).decode()}},
            ]}],
        })
        response.raise_for_status()
        if not response.json().get("choices"):
            raise ValueError("The FTT image check returned no result.")
        return model

    async def check_tts(client):
        if service_type(settings) == "supertonic":
            response = await client.get(api_base(settings["tts_url"]) + "/audio/voices",
                                        headers=headers(settings.get("tts_api_key")))
            response.raise_for_status()
            voices = [voice["id"] for voice in response.json()["voices"]]
            if settings["speaker"] not in voices:
                raise ValueError("The selected TTS voice is unavailable.")
            return True
        response = await client.get(settings["tts_url"].rstrip("/") + "/health",
                                    headers=headers(settings.get("tts_api_key")))
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "ready":
            raise ValueError("The TTS model is not ready.")
        languages = body.get("languages", [])
        speakers = body.get("speakers", [])
        if languages and settings["language"].lower() not in [s.lower() for s in languages]:
            raise ValueError("The selected TTS language is unavailable.")
        if speakers and settings["speaker"].lower() not in [s.lower() for s in speakers]:
            raise ValueError("The selected TTS speaker is unavailable.")
        return True

    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        results = await asyncio.gather(check_ftt(client), check_tts(client), return_exceptions=True)
    failures = []
    for name, value in zip(("FTT", "TTS"), results):
        if isinstance(value, Exception):
            failures.append(f"{name} service is unavailable. Check its settings and return later.")
    if failures:
        return {"ready": False, "errors": failures}
    return {"ready": True, "ftt_model": results[0], "errors": []}
