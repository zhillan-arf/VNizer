# VNizer

VNizer converts PDF documents into narrated visual novel videos.
Each PDF produces a transcript, an audio-only MP4, and an H.264/AAC MP4 video.

The application includes authentication, multiple-file upload, saved progress, stage retries, downloads, and administration.
Admin controls service settings, conversion processes, files, and mood-based character assets.

## Start locally

Install Python 3.12, uv, FFmpeg, and Noto CJK or DejaVu fonts.

```sh
uv sync --frozen
cp .env.example .env
uv run vnizer serve
```

In another terminal, run `uv run vnizer worker`.
Open `http://127.0.0.1:8080`.
Leave both credential fields empty to enter without a password.

Use [the deployment guide](deploy/README.md) for Docker, configuration, backup, restore, and live PDF acceptance.
The default FTT endpoint accepts image input on port 5003.
Docker defaults use the external Supertonic service. Local Qwen remains available.
Set the app port, TTS type, and TTS URL in `deploy/.env`.
See [the external TTS experiment](docs/verification/p08.md) for results and limits.

## Prepared assets

The TTS model and tokenizer are verified under `/data-model/zhillan/VNizer`.
Five animated Ene mood clips are prepared locally and selected in `data/`.
Portable fallback characters are included in the repository.

- [TTS service](deploy/tts/README.md)
- [Avatar preparation](docs/product/avatar-preparation.md)
- [Release requirement audit](docs/verification/release-audit.md)

## Checks

```sh
uv run playwright install chromium
scripts/check.sh -q
```

The checks include real browser workflows and a complete worker run with local HTTP fixtures and real FFmpeg output.
They do not load the TTS model or claim live-model validation.

## Project records

- [Sprint 001 brief](ops/001-zhil/sprint-001/brief.md)
- [Product requirements](docs/product/sprint-001.md)
- [Design](docs/product/design.md)
- [Repository rules](AGENTS.md)
- [Task workflow](ops/README.md)
- [Original brief](docs/archive/sprint-001-original-brief.md)
