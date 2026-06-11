# AGENTS.md

## Project
Auto-generate structured Markdown notes from Bilibili videos using ASR (mlx-whisper) + OCR (PaddleOCR) + LLM (OpenAI/Ollama/DeepSeek).

## Setup
```bash
uv sync
```

Prerequisites: `yt-dlp` must be available on PATH.

## Commands
```bash
auto-notes process "https://www.bilibili.com/video/BVxxx"                    # basic (audio-only, fast)
auto-notes process "https://..." -o ./out                                     # specify output
auto-notes process "https://..." --lang en                                    # specify non-Chinese audio
auto-notes process "https://..." --llm openai -m deepseek-chat --base-url https://api.deepseek.com/v1  # DeepSeek
auto-notes process "https://..." --cookies chrome                             # browser cookies (required)
auto-notes process "https://..." --full                                       # full mode: video + OCR (slower)
```

## Architecture
- `src/auto_notes/cli.py` — typer CLI entrypoint
- `src/auto_notes/pipeline.py` — orchestrator: download → keyframes + parallel ASR+OCR → merge → LLM → markdown
- `src/auto_notes/config.py` — TOML config loading (auto_notes.toml or ~/.config/auto_notes.toml)
- `src/auto_notes/downloader.py` — yt-dlp wrapper, retains intermediates, progress bar
- `src/auto_notes/keyframe.py` — OpenCV keyframe extraction at timed intervals (no ffmpeg needed)
- `src/auto_notes/asr.py` — mlx-whisper transcription with timestamps (Apple Silicon GPU)
- `src/auto_notes/ocr.py` — PaddleOCR with text deduplication
- `src/auto_notes/llm.py` — pluggable LLM abstraction (OpenAI-compatible / Ollama) with configurable base_url
- `src/auto_notes/output.py` — text merging + markdown note generation

## Key details
- ASR and OCR run in parallel via `ThreadPoolExecutor(max_workers=2)` (only in `--full` mode).
- Default is audio-only (`--no-full`). Use `--full` for video download + OCR.
- First run downloads models: mlx-whisper (medium, ~1.5GB) and PaddleOCR (~200MB). Both run fully offline after download.
- Intermediate files (transcript.json, ocr.json, frames/) are kept by default under `workspace/`. Download is cached — re-running skips re-download.
- Markdown output uses timestamp links in `[▶](→t=MM:SS)` format.
- Bilibili videos need `--cookies chrome` (or firefox/safari). yt-dlp downloads video+audio separately; keyframes from .mp4, ASR from .m4a.
- Use `--base-url` for OpenAI-compatible APIs (DeepSeek, etc.). API key goes in `OPENAI_API_KEY` env var.
