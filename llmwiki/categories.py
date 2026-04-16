"""Category page generator (v1.0 · #154).

Generates per-tag index pages (`wiki/categories/<tag>.md`) from the
`tags:` field in wiki page frontmatter.

Two output modes:

  - **Dataview** (``generate_dataview_categories``) — pages contain a
    live Dataview query that Obsidian renders dynamically.
  - **Static** (``generate_static_categories``) — pages contain a
    pre-rendered markdown list for use in the static HTML site.

Both modes work from the same page scan; the user picks which mode
fits their workflow (Obsidian users → Dataview; GitHub Pages users →
static).

Usage::

    from llmwiki.categories import scan_tags, generate_static_categories
    pages = load_pages()
    counts = scan_tags(pages)
    generate_static_categories(pages, out_dir, min_count=2)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

# ─── Tag scanning ──────────────────────────────────────────────────────

# Noise tags that should never become a category (too broad or too common)
NOISE_TAGS: set[str] = {
    "claude-code",
    "session-transcript",
    "demo",
    "",
}


def _parse_tags(raw: str) -> list[str]:
    """Parse the YAML ``tags:`` value into a cleaned list of tag strings."""
    if not raw:
        return []
    # strip surrounding [ ]
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    # split on commas
    parts = [p.strip().strip('"').strip("'") for p in raw.split(",")]
    return [p.lower() for p in parts if p and p.lower() not in NOISE_TAGS]


def scan_tags(pages: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Scan all pages and return ``{tag: [page_rel, ...]}``."""
    out: dict[str, list[str]] = {}
    for rel, page in pages.items():
        raw_tags = page["meta"].get("tags", "")
        for tag in _parse_tags(raw_tags):
            out.setdefault(tag, []).append(rel)
    # Sort page lists for deterministic output
    return {tag: sorted(pages_) for tag, pages_ in out.items()}


# ─── Dataview output ──────────────────────────────────────────────────

def dataview_page(tag: str) -> str:
    """Render the Dataview query page body for a tag."""
    return f"""---
title: "Category: {tag}"
type: navigation
tag: {tag}
---

# Category: {tag}

Pages tagged with `{tag}`.

```dataview
TABLE type, confidence, last_updated
FROM "sources" OR "entities" OR "concepts" OR "syntheses"
WHERE contains(tags, "{tag}")
SORT last_updated DESC
```

## Connections

- [[index]] — full catalog
- [[dashboard]] — live overview
"""


# ─── Static output ────────────────────────────────────────────────────

def _page_slug(rel: str) -> str:
    return rel.rsplit("/", 1)[-1].removesuffix(".md")


def _page_title(pages: dict[str, dict[str, Any]], rel: str) -> str:
    return pages[rel]["meta"].get("title", _page_slug(rel))


def static_page(
    tag: str,
    page_rels: list[str],
    pages: dict[str, dict[str, Any]],
) -> str:
    """Render a static category page body for GitHub Pages."""
    lines = [
        "---",
        f'title: "Category: {tag}"',
        "type: navigation",
        f"tag: {tag}",
        "---",
        "",
        f"# Category: {tag}",
        "",
        f"{len(page_rels)} pages tagged with `{tag}`.",
        "",
    ]
    # Group by top-level folder
    by_folder: dict[str, list[str]] = {}
    for rel in page_rels:
        folder = rel.split("/", 1)[0] if "/" in rel else "root"
        by_folder.setdefault(folder, []).append(rel)

    for folder in sorted(by_folder):
        lines.append(f"## {folder}")
        lines.append("")
        for rel in by_folder[folder]:
            slug = _page_slug(rel)
            title = _page_title(pages, rel)
            lines.append(f"- [[{slug}|{title}]]")
        lines.append("")

    lines.extend([
        "## Connections",
        "",
        "- [[index]] — full catalog",
        "- [[dashboard]] — live overview",
        "",
    ])
    return "\n".join(lines)


# ─── Generators ──────────────────────────────────────────────────────

def generate_dataview_categories(
    tags: dict[str, list[str]],
    out_dir: Path,
    *,
    min_count: int = 2,
) -> list[Path]:
    """Write Dataview category pages for every tag with >= ``min_count`` pages.

    Returns the list of written paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for tag, page_rels in sorted(tags.items()):
        if len(page_rels) < min_count:
            continue
        slug = re.sub(r"[^a-z0-9_-]+", "-", tag)
        path = out_dir / f"{slug}.md"
        path.write_text(dataview_page(tag), encoding="utf-8")
        written.append(path)
    return written


def generate_static_categories(
    pages: dict[str, dict[str, Any]],
    out_dir: Path,
    *,
    min_count: int = 2,
) -> list[Path]:
    """Write static category pages (no Dataview) for every tag."""
    tags = scan_tags(pages)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for tag, page_rels in sorted(tags.items()):
        if len(page_rels) < min_count:
            continue
        slug = re.sub(r"[^a-z0-9_-]+", "-", tag)
        path = out_dir / f"{slug}.md"
        path.write_text(static_page(tag, page_rels, pages), encoding="utf-8")
        written.append(path)
    return written
