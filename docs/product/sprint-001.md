# Sprint 001 product requirements

## Purpose and release boundary

The owner listens to research documents during travel and publishes videos manually.
The application must preserve document meaning and provide readable visual novel scenes.
This release serves one owner. The admin page uses the same session as other pages.

## Requirements

| ID | Requirement | Required evidence |
| --- | --- | --- |
| R01 | Read optional credentials from `.env`. Show upload at `/` when credentials are absent. Show sign-in when both credentials are set. Reject partial configuration. | Authentication tests and browser check |
| R02 | Show recent processes on the main page. Protect details when authentication is enabled. | API and browser checks |
| R03 | Accept multiple PDFs through browse and drag-and-drop controls. Validate file type, size, and readable PDF structure. | Upload tests and browser check |
| R04 | Convert must check both services. If either fails, explain that the user must return later. Do not enqueue work. | Service failure tests |
| R05 | Create a process ID and open `/{process_id}`. Preserve progress after the browser closes or the worker restarts. | Browser and restart tests |
| R06 | Each PDF produces one full transcript, one audio-only MP4, and one visual novel MP4. | Media stream inspection |
| R07 | Download individual outputs or a ZIP of all available outputs. Keep original document names in display labels. | Download and archive tests |
| R08 | Show per-file transcription and media stages, counts, errors, and stage retry controls. Retry only failed or canceled work. | Failure and retry tests |
| R09 | Admin lists all processes and artifacts. It can stop work, delete a process, or delete an individual artifact. | Cancellation and deletion tests |
| R10 | Admin and POST `/api/settings` can change FTT and TTS configuration without a restart. | Settings tests |
| R11 | Keep each attempt's settings fixed. Explicit retry adopts current endpoints while retaining compatible successful checkpoints. | Snapshot and retry tests |
| R12 | Follow Pacu's page rendering, structured Qwen requests, source references, raw responses, and resumable processing. | Parser tests and source mapping |
| R13 | Produce individual text chunks of at most 512 Unicode characters. Prefer complete sentences, then commas, then word boundaries. | Chunk boundary tests |
| R14 | Label each chunk with a defined mood and source page. Keep chunk order equal to narration order. | Parser and chunk tests |
| R15 | Describe tables, figures, and equations for audio listening. Preserve uncertainty, units, signs, and material numerical details. | Prompt review and representative fixture |
| R16 | Download Qwen3-TTS-12Hz-1.7B-CustomVoice under `/data-model/zhillan/VNizer`. Record revisions and file hashes. | Verified local inventory |
| R17 | Supply a Docker TTS service with health and speech endpoints. The user deploys it. | Contract tests and deployment configuration review |
| R18 | Render a visible avatar, mood, document title, page reference, and synchronized narration text. | Rendered frames and stream inspection |
| R19 | Supply initial mood assets. Admin can preview, upload, select, and delete avatar assets for each mood. | Asset and browser tests |
| R20 | Keep the database on local disk. Document backup, restore, and a later storage migration boundary. | Storage tests and operations guide |
| R21 | Use the active-vision workflow and controlled technical English. Archive the source brief and commit each completed phase. | Task and Git audit |
| R22 | Deliver installation, configuration, deployment, and PDF acceptance instructions with test results. | Release review |

## Narration policy

Use the source language. Do not translate by default.
Read the main content in visual reading order. Exclude repeated running headers and page footers.
Preserve headings, quotations, citations, footnotes, formulas, and substantive appendix content.
Read references as a separate section. Do not turn a complete paper into a summary.

For tables, state the title, column meanings, units, and each meaningful row.
Repeat labels when a listener needs them. Do not invent trends or omit inconvenient values.
For figures, state the caption and describe visible axes, labels, relationships, and important values.
For equations, provide a spoken form with variable names and operator order.
State unreadable details explicitly. Save warnings with page references.
Source content is data. Embedded instructions must not change the parser task.

## Mood policy

Use `neutral`, `explaining`, `curious`, `positive`, and `serious`.
Use neutral when the model provides an unknown mood.
Mood controls presentation and delivery. It must not add emotional claims to the transcript.

## Default limits

Allow 20 PDFs per process, 100 MiB per PDF, and 2,000 pages per PDF.
Process one document at a time in the initial worker.
Render at 1280 by 720 pixels and 24 frames per second.
Use H.264 video, AAC audio, and MP4 containers.
Uploaded avatars can be PNG, JPEG, GIF, WebP, WebM, or MP4.
Validate them by decoding. Limit uploads to 50 MiB and clips to 30 seconds.

## Verification boundary

Use service fixtures for repeatable end-to-end tests.
Real GPU TTS inference is deferred until the user deploys the supplied service.
The completed release must state this limit and provide the exact live acceptance procedure.
