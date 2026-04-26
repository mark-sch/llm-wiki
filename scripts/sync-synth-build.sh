#!/usr/bin/env bash
# llmwiki — Init → Sync → Synthesize → Build Pipeline
# Usage: ./scripts/sync-synth-build.sh [--skip-sync] [--skip-synth] [--skip-build] [--language <en|de>]
#
# Beispiel (alles auf einmal):
#   ./scripts/sync-synth-build.sh
#
# Beispiel (nur bauen, wenn wiki/sources schon fertig sind):
#   ./scripts/sync-synth-build.sh --skip-sync --skip-synth

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

SKIP_SYNC=false
SKIP_SYNTH=false
SKIP_BUILD=false
LANGUAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-sync) SKIP_SYNC=true; shift ;;
    --skip-synth) SKIP_SYNTH=true; shift ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    --language)
      LANGUAGE="$2"
      shift 2
      ;;
    --language=*)
      LANGUAGE="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Resolve language: CLI flag wins, then config.json, then fallback "de"
if [[ -z "$LANGUAGE" ]]; then
  if [[ -f config.json ]]; then
    LANGUAGE="$(python3 -c "import sys,json; print(json.load(open('config.json')).get('language','en'))" 2>/dev/null || echo en)"
  else
    LANGUAGE="en"
  fi
fi

echo "========================================"
echo " llmwiki Pipeline: Init → Sync → Synth → Build"
echo " language=${LANGUAGE}"
echo "========================================"
echo ""

# ─── 1. Init ──────────────────────────────────────────────────────────
echo "[1/4] Init — Verzeichnisstruktur …"
uv run llmwiki init --language "$LANGUAGE"
echo ""

# ─── 2. Sync ──────────────────────────────────────────────────────────
if [ "$SKIP_SYNC" = false ]; then
  echo "[2/4] Sync — Agent-Sessions → raw/sessions/ …"
  uv run llmwiki sync
  echo ""
else
  echo "[2/4] Sync — übersprungen (--skip-sync)"
fi

# ─── 3. Synthesize ────────────────────────────────────────────────────
if [ "$SKIP_SYNTH" = false ]; then
  echo "[3/4] Synthesize — LLM-generierte wiki/sources/ …"
  echo "      (Das kann bei vielen Sessions einige Zeit dauern.)"
  uv run llmwiki synthesize
  echo ""
else
  echo "[3/4] Synthesize — übersprungen (--skip-synth)"
fi

# ─── 4. Build ─────────────────────────────────────────────────────────
if [ "$SKIP_BUILD" = false ]; then
  echo "[4/4] Build — Statische Site unter site/ …"
  uv run llmwiki build
  echo ""
else
  echo "[4/4] Build — übersprungen (--skip-build)"
fi

echo "========================================"
echo " Fertig."
echo "========================================"

if [ "$SKIP_BUILD" = false ]; then
  echo ""
  echo "  Site-Index:    ${REPO_ROOT}/site/index.html"
  echo "  Zum Anschauen: uv run llmwiki serve"
  echo "                 oder: python3 -m http.server -d site 8765"
fi
