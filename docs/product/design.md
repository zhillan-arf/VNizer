# Sprint 001 design

## Components

Use FastAPI for HTTP routes and server-rendered page shells.
Use plain JavaScript and CSS for uploads, progress polling, and admin controls.
Use SQLite in WAL mode for process state and configuration.
Use a separate Python worker for the conversion queue. Run one worker per database.
Use PyMuPDF to validate PDFs and render page images at 200 DPI.
Use HTTPX for bounded service requests and FFmpeg for media encoding.

The database stays under `data/` on the repository disk by default.
Model weights stay under `/data-model/zhillan/VNizer`.
Store artifact paths relative to the data root. Never accept paths from download clients.

## Records and files

A process contains one or more documents and a service configuration snapshot.
A document records its source name, stage, page count, progress, attempt, and error.
Artifacts have opaque IDs, document IDs, kinds, relative paths, and byte sizes.
Configuration and avatars have separate records.

Use these artifact groups:

- `processes/{id}/{document_id}/source.pdf`
- `pages/{page_number}.json`: response, extracted blocks, source page, and warnings.
- `chunks/{index}.txt` and `chunks.json`: narration text, mood, and page references.
- `speech/{index}.wav`: completed speech checkpoints.
- `transcript.txt`, `audio.mp4`, and `video.mp4`: user downloads.

Write files to temporary siblings. Rename them only after successful validation.
Register only complete artifacts. Never expose partial MP4 files as downloads.

## State and recovery

Document states are queued, parsing, parsed, rendering, completed, failed, and canceled.
Record the failed stage separately as transcription or media.
Write progress after each successful page and speech chunk.
On worker startup, return interrupted documents to the queue.
A process is complete when all documents are complete. Partial failures remain visible.

Cancellation terminates the local document subprocess and its FFmpeg children.
Cancel remote requests by closing the connection; remote computation can continue until its service timeout.
Do not imply control over another service's scheduler.
Persist cancellation before termination. Recheck state before publishing output.
Delete running processes only after the worker has stopped them.
Reject individual artifact deletion while its document runs.

Retries keep successful pages and speech chunks when their input identity remains compatible.
A media retry must not repeat transcription.
Configuration changes affect new processes and explicit retries. Active attempts retain their snapshot.
Snapshot avatar files per attempt so admin changes cannot break running renders.

## Service contracts

FTT uses an OpenAI-compatible `/v1/models` probe and `/v1/chat/completions` request.
The preflight also sends a small image request to detect disabled image input.
Normalize URLs with or without `/v1`.
Resolve the advertised model when no model is configured. Preserve explicit model choices.
The supplied default endpoint is `http://10.12.1.193:1812`.
Reject truncated, empty, malformed, or structurally invalid responses.
Save raw responses before conversion so failed normalization can be inspected.
Bound timeouts and retries. Do not silently fall back to partial plain-text extraction.

TTS uses `GET /health` and `POST /speech`.
A speech request has text, mood, speaker, and language. It returns WAV audio.
The service uses Qwen's `generate_custom_voice` method with local weights.
Serialize GPU generation. Report healthy only after the model loads.
The app verifies response size and decodes WAV before saving a checkpoint.

## HTTP interface

- `POST /api/login`, `POST /api/logout`, `GET /api/session`.
- `GET /api/processes`, `POST /api/processes`, `GET /api/processes/{id}`.
- `POST /api/processes/{id}/cancel`, `DELETE /api/processes/{id}`.
- `POST /api/documents/{id}/retry` with a requested stage.
- `GET /api/artifacts/{id}`, `DELETE /api/artifacts/{id}`.
- `GET /api/processes/{id}/download` for an archive.
- `GET /api/settings`, `POST /api/settings`, `POST /api/health-check`.
- `GET /api/avatars`, `POST /api/avatars`, `DELETE /api/avatars/{id}`.
- `POST /api/avatars/{id}/select`.

Use signed, HTTP-only session cookies. Protect mutation requests against cross-origin submissions.
Credentials and signing secrets come from `.env` or environment variables.
Do not return service API keys in ordinary configuration responses.
The admin page has no extra role or password.

## Video composition

Place the avatar beside a large narration panel on a quiet background.
Show the document title, page number, mood, and current chunk.
Split long displayed chunks into readable panels while retaining their speech timing.
Loop animated avatar media for the chunk duration. Remove avatar audio.
Use the speech duration as the timing authority. Concatenate normalized segments.
Generate audio-only MP4 from the same speech checkpoints.

Prepare local Ene mood clips from the VModel source, as requested in the source brief.
Reuse its portrait framing, expression mappings, and short loop approach.
Keep the source model and rendered media outside Git. Preserve source credits with the local asset pack.
Provide an original vector character as a portable fallback.
The user can supply other character media through the admin page.

## Storage migration

Keep database operations in a storage module. Keep file operations under one artifact root.
Back up SQLite with its backup API, then copy artifacts while the worker is stopped.
Export records and relative paths before a later PostgreSQL or object-storage migration.
Cloud scheduling and distributed workers are outside Sprint 001.
