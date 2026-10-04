# Sprint 001 release audit

This audit covers the original brief, requirements R01 through R22, and phase controllers P01 through P07.
Live GPU inference and the owner's PDF acceptance remain user-run deployment checks, as specified in the brief.

| Requirement | Implementation and evidence |
| --- | --- |
| R01 | `config.py` reads `.env`; API and browser tests cover bypass, credentials, incorrect passwords, and partial configuration. |
| R02 | Authentication and upload pages show recent processes. Browser checks confirm protected access and saved navigation. |
| R03 | Upload API validates count, size, suffix, encryption, and PDF structure. Browser tests cover browse and drag-and-drop. |
| R04 | Preflight checks model discovery, image input, and TTS readiness. Failure tests prove that no process is created. |
| R05 | SQLite stores progress and process IDs. API recovery, browser reload, worker restart, and parent-death tests cover persistence. |
| R06 | `test_end_to_end.py` runs the actual worker on two PDFs. Each PDF produces TXT, audio-only MP4, and video MP4. |
| R07 | API, browser, and complete-pipeline tests cover individual downloads and a ZIP with six outputs. |
| R08 | Document states retain stage, progress, attempt, and error. Failed media retries preserve completed transcription. |
| R09 | Admin lists processes and registered or temporary artifacts. Browser and API tests cover stop and deletion. |
| R10 | Settings API and admin form update services without restart. API tests prove persisted updates. |
| R11 | Each attempt stores its settings and selected avatars. Snapshot, retry, and speech-cache tests cover retained work. |
| R12 | Parser uses 200 DPI images, structured Qwen requests, raw responses, source pages, and page checkpoints. See P04 evidence. |
| R13 | Chunk tests cover sentences, commas, abbreviations, long words, CJK, and the 512-character limit. |
| R14 | Chunk records contain mood, role, page, order, and narration text. Unknown moods become neutral with a warning. |
| R15 | The prompt defines table, figure, and equation narration. Representative structured-content tests preserve units, signs, and uncertainty. |
| R16 | Both model repositories were downloaded and verified. `tts-model-inventory.json` and `tts-tokenizer-inventory.json` record revisions and hashes. |
| R17 | `deploy/tts/` supplies a Docker service with authenticated health and speech endpoints. Contract tests cover generation and validation. |
| R18 | Real FFmpeg tests inspect H.264/AAC streams, dimensions, and duration. P05 includes inspected character and narration frames. |
| R19 | Five Ene mood clips are prepared locally. Five original fallback assets are committed. Browser tests cover avatar operations. |
| R20 | SQLite and artifacts use local `data/`. Backup tests cover locks, integrity, checksums, and restoration. The runbook defines migration boundaries. |
| R21 | The source brief is archived. Repository rules, sprint brief, task records, and phase commits follow the reference workflow. |
| R22 | `deploy/README.md` gives setup, service configuration, operations, backup, restore, and a 17-step live acceptance procedure. |

## Original scope coverage

The four requested pages map to R01 through R10 and R19.
The FTT service and sentence-based chunks map to R11 through R15.
The TTS model download and deployment package map to R16 and R17.
The delegated narration, database, and avatar decisions are recorded in the design and research documents.
The setup, archived brief, requirements, phased backlog, implementation, and phase commits all belong to Sprint 001.

## Known runtime boundary

The supplied FTT endpoint advertises the requested model but currently rejects image input.
The operator must enable images or select another compatible endpoint before live conversion.
The application reports this condition during preflight.

The TTS HTTP contract was tested with a fixture. Real voice inference has not run on the occupied GPU.
The model files are prepared for the user's deployment.
Real transcription fidelity and voice quality must be checked against the owner's PDF samples.
These limits do not represent a claim of live-model validation.

## Verification records

- `p05.md`: model, media, and avatar verification.
- `p06.md`: browser workflows and visual inspection.
- P07 controller: final test, package, Compose, and image-build results.

The STE review used short sentences and consistent project terms.
This report does not claim a full dictionary-level ASD-STE100 certification.
