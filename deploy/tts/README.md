# Local Qwen TTS service

The service loads `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` from local files.
It exposes `GET /health` and `POST /speech` on port 1813.
A speech request returns PCM16 WAV audio.
Only one generation request runs at a time. A concurrent request receives HTTP 429.

## Model files

Run this command before deployment:

```sh
python scripts/download_models.py
```

The default destination is `/data-model/zhillan/VNizer`.
The script verifies upstream file hashes and saves `vnizer-inventory.json` for each repository.
It skips existing files only when their hashes match the requested revision.

## Container configuration

Build from the repository root with `deploy/tts/Dockerfile`.
Mount the model root at `/models` as read-only storage.
Give the container access to an NVIDIA GPU through the NVIDIA Container Toolkit.
The image uses Python 3.12 and the official `qwen-tts` package.
Model loading uses CUDA, bfloat16, and SDPA attention.
The offline environment prevents an unexpected model download during startup.

Set `TTS_API_KEY` to require bearer authentication.
Set the same key in VNizer's TTS service settings.
The service is ready only after model loading finishes.
Use one Uvicorn worker to avoid duplicate model allocation.

## Verification boundary

HTTP contract tests pass with a model fixture.
Real GPU inference has not run because the host GPU is reserved for another project.
The user will deploy this service and check the resulting voice with real PDF input.
