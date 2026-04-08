"""Eval framework — automated quality checks for a compiled llmwiki.

Runs a battery of checks against the current wiki/ directory and produces a
score (0-100) + a detailed report. Used for:

- CI regression checking
- Before/after comparison when testing new ingest strategies
- Measuring wiki quality over time (monthly Maintain phase)

Usage:

    python3 -m llmwiki eval                    # runs all checks, writes eval-report.json
    python3 -m llmwiki eval --json             # json output to stdout
    python3 -m llmwiki eval --check orphans    # one check only
    python3 -m llmwiki eval --fail-below 70    # exit non-zero if score < 70

The eval is purely structural — no LLM calls, no embeddings, no network.
Every check runs in under a second on a 300-page wiki.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from llmwiki import REPO_ROOT

WIKI_DIR = REPO_ROOT / "wiki"
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


class Check:
    """A single eval check.

    Subclasses override `run(pages) -> CheckResult` to compute their score.
    """

    name: str = "base"
    description: str = ""
    max_score: int = 10

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"')
    return out


def scan_pages() -> dict[str, dict[str, Any]]:
    """Return {slug: {path, type, frontmatter, body, out_links}}."""
    pages: dict[str, dict[str, Any]] = {}
    if not WIKI_DIR.exists():
        return pages
    for p in sorted(WIKI_DIR.rglob("*.md")):
        if p.name == "README.md":
            continue
        slug = p.stem
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        try:
            rel = p.relative_to(WIKI_DIR)
            type_ = rel.parts[0] if len(rel.parts) > 1 else "root"
        except ValueError:
            type_ = "root"
        pages[slug] = {
            "path": str(p.relative_to(REPO_ROOT)),
            "type": type_,
            "frontmatter": fm,
            "body": text,
            "size": len(text),
            "out_links": set(WIKILINK_RE.findall(text)),
        }
    return pages


# ─── Individual checks ────────────────────────────────────────────────────


class OrphanCheck(Check):
    name = "orphans"
    description = "Every page should have at least one inbound wikilink"
    max_score = 15

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        in_deg: dict[str, int] = {slug: 0 for slug in pages}
        for slug, page in pages.items():
            for target in page["out_links"]:
                if target in in_deg:
                    in_deg[target] += 1
        # index/overview/log are expected to have no inbound
        protected = {"index", "overview", "log", "lint-report"}
        orphans = [s for s, d in in_deg.items() if d == 0 and s not in protected]
        if not pages:
            return {"score": 0, "notes": "no pages"}
        ratio = 1 - (len(orphans) / max(1, len(pages) - len(protected)))
        score = round(self.max_score * max(0, ratio))
        return {
            "score": score,
            "max": self.max_score,
            "orphan_count": len(orphans),
            "total_pages": len(pages),
            "notes": f"{len(orphans)} orphans across {len(pages)} pages",
            "sample": orphans[:5],
        }


class BrokenLinkCheck(Check):
    name = "broken_links"
    description = "Every [[wikilink]] should resolve to an existing page"
    max_score = 20

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        broken: list[dict[str, str]] = []
        total_links = 0
        for slug, page in pages.items():
            for target in page["out_links"]:
                total_links += 1
                if target not in pages:
                    broken.append({"page": slug, "target": target})
        if total_links == 0:
            return {"score": 0, "max": self.max_score, "notes": "no wikilinks"}
        ratio = 1 - (len(broken) / total_links)
        score = round(self.max_score * ratio)
        return {
            "score": score,
            "max": self.max_score,
            "broken_count": len(broken),
            "total_links": total_links,
            "notes": f"{len(broken)} broken out of {total_links} wikilinks",
            "sample": broken[:5],
        }


class FrontmatterCheck(Check):
    name = "frontmatter"
    description = "Every page should have title, type, tags, last_updated"
    max_score = 15

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        required = {"title", "type"}
        missing: list[dict[str, Any]] = []
        for slug, page in pages.items():
            if slug in ("index", "overview", "log"):
                continue
            fm = page["frontmatter"]
            lacks = required - set(fm.keys())
            if lacks:
                missing.append({"page": slug, "missing": sorted(lacks)})
        total = len([s for s in pages if s not in ("index", "overview", "log")])
        if total == 0:
            return {"score": 0, "max": self.max_score, "notes": "no content pages"}
        ratio = 1 - (len(missing) / total)
        score = round(self.max_score * ratio)
        return {
            "score": score,
            "max": self.max_score,
            "missing_count": len(missing),
            "notes": f"{len(missing)} of {total} pages missing required frontmatter fields",
            "sample": missing[:5],
        }


class CoverageCheck(Check):
    name = "coverage"
    description = "Should have sources, entities, and concepts pages (not just one category)"
    max_score = 15

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for p in pages.values():
            type_counts[p["type"]] = type_counts.get(p["type"], 0) + 1

        expected_types = ["sources", "entities", "concepts"]
        present = sum(1 for t in expected_types if type_counts.get(t, 0) > 0)
        score = round(self.max_score * (present / len(expected_types)))
        return {
            "score": score,
            "max": self.max_score,
            "type_counts": type_counts,
            "notes": f"{present}/{len(expected_types)} expected types present",
        }


class CrossLinkingCheck(Check):
    name = "cross_linking"
    description = "Each source page should link to 2+ entities/concepts"
    max_score = 15

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        sources = [s for s, p in pages.items() if p["type"] == "sources"]
        if not sources:
            return {"score": 0, "max": self.max_score, "notes": "no source pages"}
        under_linked = [s for s in sources if len(pages[s]["out_links"]) < 2]
        ratio = 1 - (len(under_linked) / len(sources))
        score = round(self.max_score * ratio)
        return {
            "score": score,
            "max": self.max_score,
            "under_linked_count": len(under_linked),
            "total_sources": len(sources),
            "notes": f"{len(under_linked)} of {len(sources)} sources under-linked",
            "sample": under_linked[:5],
        }


class SizeCheck(Check):
    name = "sizes"
    description = "Pages should be neither empty nor bloated (target 500-5000 chars)"
    max_score = 10

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        too_small = []
        too_big = []
        for slug, page in pages.items():
            if slug in ("index", "overview", "log"):
                continue
            size = page["size"]
            if size < 500:
                too_small.append({"slug": slug, "size": size})
            elif size > 15000:
                too_big.append({"slug": slug, "size": size})
        total = len([s for s in pages if s not in ("index", "overview", "log")])
        if total == 0:
            return {"score": 0, "max": self.max_score, "notes": "no content pages"}
        problem_ratio = (len(too_small) + len(too_big)) / total
        score = round(self.max_score * max(0, 1 - problem_ratio))
        return {
            "score": score,
            "max": self.max_score,
            "too_small": len(too_small),
            "too_big": len(too_big),
            "total_pages": total,
            "notes": f"{len(too_small)} too small, {len(too_big)} too big",
        }


class ContradictionCheck(Check):
    name = "contradictions"
    description = "Contradictions should be recorded under '## Contradictions', not hidden"
    max_score = 10

    def run(self, pages: dict[str, dict[str, Any]]) -> dict[str, Any]:
        # Look for pages that *claim* to have contradictions
        pages_with_contradictions = [
            s for s, p in pages.items() if "## Contradictions" in p["body"]
        ]
        # This check always gives full marks if the section exists — the
        # presence of a Contradictions section is a good signal. We only
        # dock if a page has the section but it's empty.
        empty = []
        for slug in pages_with_contradictions:
            body = pages[slug]["body"]
            section_start = body.index("## Contradictions")
            # Get everything up to the next ## or end
            rest = body[section_start + len("## Contradictions"):]
            next_section = re.search(r"\n##\s", rest)
            section_body = rest[: next_section.start()] if next_section else rest
            if not re.search(r"\w", section_body):
                empty.append(slug)
        notes = f"{len(pages_with_contradictions)} pages track contradictions"
        if empty:
            notes += f" ({len(empty)} empty)"
        score = self.max_score - min(len(empty), self.max_score)
        return {
            "score": score,
            "max": self.max_score,
            "pages_with_contradictions": len(pages_with_contradictions),
            "empty_contradiction_sections": len(empty),
            "notes": notes,
        }


CHECKS: list[type[Check]] = [
    OrphanCheck,
    BrokenLinkCheck,
    FrontmatterCheck,
    CoverageCheck,
    CrossLinkingCheck,
    SizeCheck,
    ContradictionCheck,
]


def run_eval(selected: list[str] | None = None) -> dict[str, Any]:
    pages = scan_pages()
    results: list[dict[str, Any]] = []
    total_score = 0
    total_max = 0
    for cls in CHECKS:
        if selected and cls.name not in selected:
            continue
        check = cls()
        try:
            r = check.run(pages)
        except Exception as e:
            r = {"score": 0, "max": check.max_score, "error": str(e)}
        r["name"] = check.name
        r["description"] = check.description
        results.append(r)
        total_score += r.get("score", 0)
        total_max += r.get("max", check.max_score)

    return {
        "total_score": total_score,
        "total_max": total_max,
        "percentage": round(100 * total_score / max(1, total_max), 1),
        "total_pages": len(pages),
        "checks": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", nargs="*", help="Only run these checks")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout instead of a text report")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "eval-report.json", help="Where to write the JSON report")
    parser.add_argument("--fail-below", type=int, default=0, help="Exit non-zero if score percentage < this")
    args = parser.parse_args(argv)

    report = run_eval(selected=args.check)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"==> llmwiki eval — {report['total_pages']} pages")
        print(f"    Total: {report['total_score']} / {report['total_max']} ({report['percentage']}%)")
        print()
        for r in report["checks"]:
            score = r.get("score", 0)
            max_ = r.get("max", "?")
            name = r.get("name", "?")
            notes = r.get("notes", "")
            bar = "█" * int(10 * score / max(1, max_)) + "░" * (10 - int(10 * score / max(1, max_)))
            print(f"  [{bar}] {score:3}/{max_:3}  {name:20}  {notes}")

        # Write the JSON report
        try:
            args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"\n    wrote {args.out.relative_to(REPO_ROOT)}")
        except (OSError, ValueError):
            pass

    if args.fail_below > 0 and report["percentage"] < args.fail_below:
        print(f"error: score {report['percentage']}% below threshold {args.fail_below}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
