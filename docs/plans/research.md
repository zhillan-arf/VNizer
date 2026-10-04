# Source review and decisions

Reviewed on 2026-10-04.

## Pacu

Read `src/pacu/config.py`, `pipeline/parsing/vlm.py`, and `pipeline/parsing/corpus_qwen.py` in the reference repository.
Pacu renders pages at 200 DPI and sends structured image requests to a Qwen endpoint.
It retains raw responses, request metadata, page identity, warnings, and resumable work items.
VNizer will preserve these choices. Its narration layer will add spoken descriptions and mood labels.
Pacu's configured model name differs from the name in the source brief.
Discover the advertised model through the configured endpoint instead of assuming either name is valid.

## Speech service

The [official model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) documents local model loading and custom voice generation.
It lists ten supported languages and nine speakers. The model uses the Apache-2.0 license.
The [official repository](https://github.com/QwenLM/Qwen3-TTS) provides the Python package and generation interface.
Use Python 3.12 in the GPU container. Wrap the documented generation API with a small HTTP service.
Download model files before deployment. Record an immutable revision and checksums.
Do not claim support for every source language. Unsupported language behavior must be explicit.

## Figures and tables

The [W3C complex image guidance](https://www.w3.org/WAI/tutorials/images/complex/) recommends descriptions that convey essential information and relationships.
Its examples include graphs, diagrams, and charts.
VNizer will apply that approach to audio narration, with additional source fidelity rules.
The description must retain labels, units, numerical details, and uncertainty.
Full table rows remain available to the listener. A trend summary cannot replace the data.

## Avatar assets

Read VModel's `config/web-resources/source.json`, `encoding.json`, and `docs/third-party-notices.md`.
VModel uses portrait framing and short animated loops with defined performance states.
Its Ene notice states local project permission and requires separate treatment of rendered media rights.
Create an original vector avatar with five mood expressions for VNizer.
This avoids making an unsupported public distribution claim about the existing character.
The asset generator and generated initial assets belong in this repository.
