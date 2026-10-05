# Deployment and operations

## Prepared release

The application image contains the API, web pages, worker, FFmpeg, and narration fonts.
The optional TTS image contains the Qwen service wrapper.
The user starts all Docker services. Development checks do not deploy them.

The following local assets are prepared:

- `/data-model/zhillan/VNizer/Qwen3-TTS-12Hz-1.7B-CustomVoice`
- `/data-model/zhillan/VNizer/Qwen3-TTS-Tokenizer-12Hz`
- `/data-model/zhillan/VNizer/avatars/ene`
- `data/avatars/`: imported Ene clips and portable fallback assets.

The database and document artifacts stay on the repository disk under `data/`.
The Compose file mounts this directory into the web and worker containers.
Do not put the SQLite database on the shared model filesystem.

## Local development

Install Python 3.12, uv, FFmpeg, and DejaVu or Noto CJK fonts.

```sh
uv sync --frozen
cp .env.example .env
uv run playwright install chromium
scripts/check.sh -q
uv run vnizer serve
```

In another terminal:

```sh
uv run vnizer worker
```

Open `http://127.0.0.1:8080`.
Leave both credential fields empty for the Enter workflow.
For authentication, set both credentials and a session secret of at least 32 characters.
Generate a secret with `python -c 'import secrets; print(secrets.token_hex(32))'`.
Set `VNIZER_SECURE_COOKIE=true` when an HTTPS proxy serves the app.
The proxy must preserve the original host and scheme for the origin check.

## Docker deployment

Run these commands from the repository root. Docker Compose reads `deploy/.env`.
A prepared file exists locally. For a new checkout, create it from the example:

```sh
test -f deploy/.env || cp deploy/.env.example deploy/.env
docker compose --env-file deploy/.env -f deploy/compose.yaml config
./deploy/manage.sh start
```

Use `./deploy/manage.sh status` to show container status.
Use `./deploy/manage.sh logs` to follow logs from the running services.
Use `./deploy/manage.sh restart` to rebuild and replace the web and worker containers.
Use `./deploy/manage.sh stop` to stop all VNizer services.
The stop command keeps application data under `data/`.

The default bind address is `0.0.0.0`, and the default host port is `8080`.
Set `VNIZER_PORT` in `deploy/.env` to select another host port.
Set `VNIZER_BIND_ADDRESS=127.0.0.1` to allow local access only.
For example, port 5301 opens at `http://<server-address>:5301`.
The mapping `0.0.0.0:5301->8080/tcp` maps host port 5301 to container port 8080.
Port 8080 on the host is separate and can serve another application.
Set credentials and API keys in this file when needed. Keep it outside Git.
The tracked `deploy/.env.example` contains the same initial defaults.

The default TTS type is `supertonic`, at `http://10.12.1.249:5001`.
It uses voice `F1` and English narration. The adapter sends the language code `en`.
Supertonic returns mono PCM16 at 24,000 Hz. VNizer converts each response to WAV.
The API does not accept mood instructions. Avatar moods still work.
The connection check verifies access and the selected voice. It does not generate speech or verify language support.
Check voice quality and source language with a short document before processing long documents.

For the supplied local Qwen service, set these values in `deploy/.env`:

```dotenv
VNIZER_TTS_TYPE=qwen
VNIZER_TTS_URL=http://tts:1813
VNIZER_SPEAKER=Ryan
VNIZER_LANGUAGE=English
```

Install the NVIDIA Container Toolkit and prepare the model files before starting Qwen.
Then run:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml --profile tts up -d --build tts
./deploy/manage.sh start
```

The local TTS host port is `127.0.0.1:1813`. Its model volume is read-only.
The container does not download weights at startup.

Service settings are saved in SQLite after first initialization.
Environment changes do not overwrite saved settings.
The prepared local database now selects Supertonic, voice F1, and English.
For other existing databases, open Admin → Services and save the type, URL, speaker, and language.
Use Check saved connections before uploading PDFs.
Changes apply to new processes and retries. Running attempts keep their saved settings.
Switching the TTS type invalidates incompatible speech checkpoints.

The default FTT endpoint on port 5003 advertises `Qwen3.6-35B-A3B-FP8`.
It accepts image input and returns VNizer page structures.
VNizer checks this condition before it creates a conversion process.

## Service settings API

Use a signed-in session when authentication is enabled.
The following example applies when authentication is bypassed:

```sh
curl -X POST http://127.0.0.1:8080/api/settings \
  -H 'Content-Type: application/json' \
  -d '{"ftt_url":"http://10.12.1.193:5003","ftt_model":"","tts_type":"supertonic","tts_url":"http://10.12.1.249:5001","speaker":"F1","language":"English"}'
curl -X POST http://127.0.0.1:8080/api/health-check
```

New processes use the new settings. Running attempts keep their saved configuration.
Retry adopts current settings and keeps compatible page or speech checkpoints.
An empty FTT model field selects the model advertised by the service.
The page preflight also checks that the model accepts an image.

## Stop, inspect, and recover

Use the process page or Admin to stop a conversion.
The worker terminates its local document process and FFmpeg children.
A remote service can continue computation until its request timeout.
Use Retry on the failed or canceled stage after correcting the cause.
A media retry keeps the completed transcript.

The worker restores interrupted work when it starts.
Only one worker can use a data directory.
A Linux parent-death signal stops child processes after an unexpected worker exit.

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml logs --tail 100 web worker
docker compose --env-file deploy/.env -f deploy/compose.yaml --profile tts logs --tail 100 tts
```

Admin lists source files, outputs, page records, speech checkpoints, and temporary work files.
Open All artifacts for a document to inspect or download them.
Stop a document before deleting any of its files.
Deleting required source or checkpoint files can prevent a later retry.
Delete the whole process to remove all its document files.

## Backup and restore

Stop both web and worker services before backup. Keep them stopped until backup finishes.
The backup command refuses a running worker, but it does not stop the web service.
The TTS service can stay running because it does not modify document storage.

```sh
docker compose --env-file deploy/.env -f deploy/compose.yaml stop web worker
uv run vnizer backup --destination /path/to/new-backup
uv run vnizer restore --source /path/to/new-backup --destination /path/to/new-data
```

Use new destination directories. The tools do not replace existing data.
The backup uses the SQLite backup API and copies artifact and avatar files.
It includes a SHA-256 manifest and `records.json` with portable table records.
Restore checks file hashes, database integrity, and record references.
Copy `deploy/.env` separately. The backup contains service keys stored in SQLite, so protect the backup directory.

To use restored data, move it to `data/` while services remain stopped.
Keep the previous data directory until the restored application passes acceptance checks.
For native execution, set `VNIZER_DATA_ROOT` to the restored directory instead.

A later cloud migration can import `records.json` and upload files by relative path.
Keep process, document, and artifact IDs unchanged.
Replace SQLite operations and local file access before adding distributed workers.
Cloud deployment is outside Sprint 001.

## Live acceptance with the prepared PDFs

1. Check the external TTS service, or deploy local Qwen when the GPU is available.
2. Confirm that the FTT service accepts image input.
3. Save the correct service URLs, speaker, and source language in Admin.
4. Check both service connections.
5. Upload two short PDFs, including a table, figure, and equation.
6. Start conversion and save the process URL.
7. Close the browser, then reopen the saved URL.
8. Confirm that progress continues and both documents finish.
9. Download each transcript, audio-only MP4, and video MP4.
10. Download the ZIP and confirm that it contains six outputs.
11. Compare the transcript with the PDFs, including units, signs, rows, and qualifications.
12. Listen for missing words, incorrect pronunciation, and unintended translation.
13. Inspect text timing, character framing, mood changes, and the final video duration.
14. Stop a longer conversion, then retry its canceled stage.
15. Change the TTS URL temporarily and confirm that Convert reports service unavailability.
16. Restore the working URL and retry the failed stage.
17. Test a backup and restore before deleting valuable source files.

The external service passed a short speech and MP4 experiment. See `docs/verification/p08.md`.
Local Qwen voice quality and the owner's PDF content remain deployment acceptance checks.
The automated release tests use local HTTP fixtures and real FFmpeg encoding.
They do not claim that simulated audio validates the Qwen model.
