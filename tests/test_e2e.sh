#!/usr/bin/env bash
# auto-notes E2E test: Bilibili video → ASR → OCR → LLM → Markdown
#
# Usage:
#   export OPENAI_API_KEY="sk-..."
#   ./tests/test_e2e.sh
#
# Or specify a different URL:
#   ./tests/test_e2e.sh "https://www.bilibili.com/video/BV1xx"

set -euo pipefail

URL="${1:-https://www.bilibili.com/video/BV1qG4y1B74U?p=34}"

echo "=== auto-notes E2E Test ==="
echo "URL: $URL"
echo ""

uv run auto-notes "$URL" \
  --lang zh \
  --llm openai \
  -m deepseek-chat \
  --base-url https://api.deepseek.com/v1 \
  --cookies chrome

echo ""
echo "=== Done ==="
