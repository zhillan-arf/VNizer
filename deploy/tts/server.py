"""Serve local Qwen custom voice inference through a bounded HTTP interface."""

import asyncio
import io
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

MOOD_INSTRUCTIONS = {
    "neutral": "Read clearly with a calm, neutral tone.",
    "explaining": "Read clearly with a patient, explanatory tone.",
    "curious": "Read clearly with a gently curious tone.",
    "positive": "Read clearly with a warm, positive tone.",
    "serious": "Read clearly with a calm, serious tone.",
}


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=512)
    mood: str = "neutral"
    speaker: str = "Ryan"
    language: str = "English"


def create_app(loader=None):
    def load_model():
        import torch
        from qwen_tts import Qwen3TTSModel
        return Qwen3TTSModel.from_pretrained(
            os.environ.get("MODEL_PATH", "/models/Qwen3-TTS-12Hz-1.7B-CustomVoice"),
            device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa",
        )

    @asynccontextmanager
    async def lifespan(app):
        app.state.model = await asyncio.to_thread(loader or load_model)
        app.state.lock = asyncio.Lock()
        yield
        app.state.model = None

    app = FastAPI(title="VNizer TTS", lifespan=lifespan)

    def authorize(authorization):
        key = os.environ.get("TTS_API_KEY", "")
        if key and not secrets.compare_digest((authorization or "").encode(), ("Bearer " + key).encode()):
            raise HTTPException(401, "Invalid service credentials.")

    @app.get("/health")
    def health(authorization: str | None = Header(default=None)):
        authorize(authorization)
        return {"status": "ready", "speakers": app.state.model.get_supported_speakers(),
                "languages": app.state.model.get_supported_languages()}

    @app.post("/speech")
    async def speech(body: Speech, authorization: str | None = Header(default=None)):
        authorize(authorization)
        if not body.text.strip():
            raise HTTPException(422, "Speech text must not be empty.")
        speakers = app.state.model.get_supported_speakers()
        languages = app.state.model.get_supported_languages()
        if body.speaker.lower() not in [s.lower() for s in speakers]:
            raise HTTPException(422, "The selected speaker is unavailable.")
        if body.language.lower() not in [s.lower() for s in languages]:
            raise HTTPException(422, "The selected language is unavailable.")
        if app.state.lock.locked():
            raise HTTPException(429, "Speech generation is busy. Retry later.")

        def generate():
            import soundfile
            waves, sample_rate = app.state.model.generate_custom_voice(
                text=body.text, language=body.language, speaker=body.speaker,
                instruct=MOOD_INSTRUCTIONS.get(body.mood, MOOD_INSTRUCTIONS["neutral"]),
                max_new_tokens=2048,
            )
            output = io.BytesIO()
            soundfile.write(output, waves[0], sample_rate, format="WAV", subtype="PCM_16")
            return output.getvalue()

        async with app.state.lock:
            # Keep the lock until generation ends, even when a client disconnects.
            task = asyncio.create_task(asyncio.to_thread(generate))
            try:
                audio = await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise
        return Response(audio, media_type="audio/wav")

    return app


app = create_app()
