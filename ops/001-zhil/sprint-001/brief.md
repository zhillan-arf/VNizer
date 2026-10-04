---
id: SPRINT-001
title: Deliver the PDF narration application
status: complete
owner: 001-zhil
---

# Sprint 001

## Purpose

Convert research PDFs into videos for manual YouTube upload and audio listening.
Each PDF produces one transcript, one audio-only MP4, and one visual novel MP4.
The original request is preserved in `docs/archive/sprint-001-original-brief.md`.

## Scope

Build the authentication, upload, process, and admin pages.
Support multiple PDFs, durable progress, downloads, cancellation, deletion, and stage retries.
Use configurable file-to-text (FTT) and text-to-speech (TTS) services.
Prepare mood-based avatar assets and a Docker deployment package.
Download the requested Qwen TTS model under `/data-model/zhillan/VNizer`.
The user will deploy services and supply final acceptance PDFs.

## Source material

- `/home/zhillan/active-vision`: repository layout, task workflow, and language rules.
- `/home/zhillan/misc/pacu`: page rendering, Qwen requests, provenance, and resumable parsing.
- `/home/zhillan/misc/vmodel`: avatar framing, mood performances, and media preparation.
- `docs/plans/research.md`: external sources and local findings.

## Product decisions

Use a Python web server, a separate durable worker, SQLite, and local artifact storage.
Keep media paths relative to a configurable data root. Prepare an export and restore procedure.
Use sentence-aware chunks with a strict 512-character limit.
Keep service settings fixed within an attempt. Retry can select current service settings.
Use saved page and speech results to avoid repeating successful work.

## Phase map

| Phase | Outcome | Controller | Depends on | Exit evidence |
| --- | --- | --- | --- | --- |
| P01 | Repository workflow and source archive | TASK-S001-001 | None | File review and commit |
| P02 | Product requirements, design, and backlog | TASK-S001-002 | P01 | Requirement coverage review and commit |
| P03 | Durable jobs, API, and authentication | TASK-S001-003 | P02 | API and storage tests; commit |
| P04 | PDF transcription and narration chunks | TASK-S001-004 | P03 | Parser, checkpoint, and chunk tests; commit |
| P05 | TTS service, model download, and video rendering | TASK-S001-005 | P04 | Download inventory and media tests; commit |
| P06 | Web pages and avatar administration | TASK-S001-006 | P05 | Browser workflow and visual checks; commit |
| P07 | Deployment package and release checks | TASK-S001-007 | P06 | Full test suite and deployment handoff; commit |
| P08 | External Supertonic TTS support | TASK-S001-008 | P07 | Live speech experiment, adapter checks, and deployment defaults; commit |

## Acceptance

All requirements in `docs/product/sprint-001.md` must have recorded evidence.
A simulated service test must produce all three downloads from multiple PDFs.
Tests must cover service failure, retry, restart, cancellation, and artifact deletion.
The TTS weights must exist locally and match an inventory with checksums.
The release must include deployment instructions and a live-service acceptance procedure.
GPU inference can wait for the user's deployment, as requested in the source brief.
State this verification boundary clearly. Do not describe simulated speech as model validation.

## Exclusions

Do not upload to YouTube or deploy Docker services.
Do not build multi-user billing, cloud scaling, or voice cloning.
Do not include source PDFs, model weights, or generated user media in Git.

## Risks

VLM output can omit content or misread equations. Preserve provenance and report uncertain content.
Long documents can require substantial processing time and disk space.
The host GPU is occupied. Real TTS quality checks depend on later deployment.
Existing character permissions do not establish permission for public video distribution.

## Completion evidence

The original seven controllers are archived with `status: done`.
P08 adds the external TTS service after the original release.
The requirement audit is `docs/verification/release-audit.md`.
The final test and image-build evidence is `docs/verification/p07.md`.
The user-run deployment procedure is `deploy/README.md`.
