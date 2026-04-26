#!/usr/bin/env bash
# reset-wiki.sh — Löscht alle wiki-Inhalte und führt ein frisches `llmwiki init` aus.
#
# Usage:
#   ./scripts/reset-wiki.sh        # interaktive Bestätigung
#   ./scripts/reset-wiki.sh --force # ohne Nachfrage

set -euo pipefail

FORCE=false
if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
    FORCE=true
fi

# ─── Sicherheitscheck: Sind wir im Projekt-Root? ─────────────────────────────
if [[ ! -d "llmwiki" && ! -f ".llmwiki-state.json" ]]; then
    echo "Fehler: Bitte im llmwiki-Projekt-Root ausführen." >&2
    exit 1
fi

# ─── Zusammenfassung ─────────────────────────────────────────────────────────
echo "=== llmwiki Reset ==="
echo "Folgende Verzeichnisse/Dateien werden GELÖSCHT:"
echo "  raw/sessions/*"
echo "  wiki/sources/*  wiki/entities/*  wiki/concepts/*  wiki/syntheses/*  wiki/hot/*"
echo "  wiki/*.md (index, overview, log, MEMORY, SOUL, CRITICAL_FACTS, dashboard, hints, hot)"
echo "  site/*"
echo "  .llmwiki-state.json"
echo "  .llmwiki-synth-state.json"
echo ""

if [[ "$FORCE" == false ]]; then
    read -rp "Wirklich fortfahren? [j/N] " reply
    if [[ ! "$reply" =~ ^[Jj]$ ]]; then
        echo "Abgebrochen."
        exit 0
    fi
fi

# ─── Löschen ─────────────────────────────────────────────────────────────────

delete_contents() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        find "$dir" -mindepth 1 ! -name ".gitkeep" -delete 2>/dev/null || true
        echo "  ✓ $dir/ geleert"
    fi
}

delete_if_exists() {
    local file="$1"
    if [[ -e "$file" ]]; then
        rm -rf "$file"
        echo "  ✓ $file gelöscht"
    fi
}

echo "Lösche Inhalte ..."

delete_contents "raw/sessions"
delete_contents "wiki/sources"
delete_contents "wiki/entities"
delete_contents "wiki/concepts"
delete_contents "wiki/syntheses"
delete_contents "wiki/hot"
delete_contents "site"

# Top-Level wiki-Seiten (md-Dateien und Verzeichnisse die init neu anlegt)
for f in wiki/*.md; do
    delete_if_exists "$f"
done

# State-Dateien
delete_if_exists ".llmwiki-state.json"
delete_if_exists ".llmwiki-synth-state.json"

# Auch graphify-out zurücksetzen wenn vorhanden
delete_contents "graphify-out" 2>/dev/null || true

echo ""
echo "Führe aus: python3 -m llmwiki init"
python3 -m llmwiki init

echo ""
echo "=== Reset abgeschlossen ==="
echo "Wiki ist jetzt leer. Nächster Schritt:"
echo "  python3 -m llmwiki sync   # Sessions aus den Agent-Stores importieren"
