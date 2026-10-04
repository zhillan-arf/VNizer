# VNizer

VNizer converts PDF documents into narrated visual novel videos.
Sprint 001 is in progress. Runtime implementation is not complete.

- [Sprint brief](ops/001-zhil/sprint-001/brief.md)
- [Repository rules](AGENTS.md)
- [Task workflow](ops/README.md)
- [Original brief](docs/archive/sprint-001-original-brief.md)

## Development

Install Python 3.12, uv, and FFmpeg. Run `uv sync`.
Copy `.env.example` to `.env` and set the required values.
Run `uv run vnizer serve` to start the API on port 8080.
Run `scripts/check.sh -q` to check the implementation.
The conversion pipeline is implemented. The web pages and deployment package remain in progress.
Run `uv run vnizer worker` in a separate terminal to process queued documents.
See [avatar preparation](docs/product/avatar-preparation.md) for the initial character pack.
See [TTS setup](deploy/tts/README.md) for the prepared speech service.
