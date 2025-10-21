#!/usr/bin/env python3
"""
Vertical Recommender

Given a directory of files for a single use case/index, analyze file extensions
and recommend the most fitting existing vertical type:
- CODE
- DOCUMENTS
- STRUCTURED
- SPREADSHEETS
- MEDIA

Outputs a concise recommendation with confidence, counts by type, and suggested
chunk settings based on established defaults.

Usage:
    python vertical_recommender.py recommend <path> [--json]

Examples:
    python vertical_recommender.py recommend ./my_batch
    python vertical_recommender.py recommend ./my_batch --json > recommendation.json
"""

import os
import sys
import json
import mimetypes
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import click

# Initialize mimetypes
mimetypes.init()

# Category definition with optimal settings and known extensions
CATEGORIES: Dict[str, Dict] = {
    "CODE": {
        "extensions": [
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rb", ".php",
            ".html", ".htm", ".css", ".scss", ".tsx", ".jsx"
        ],
        "chunk_size": 3000,
        "overlap": 200,
        "notes": "Larger chunks preserve function/context boundaries."
    },
    "DOCUMENTS": {
        "extensions": [
            ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt", ".md", ".rtf", ".html", ".htm"
        ],
        "chunk_size": 2000,
        "overlap": 100,
        "notes": "Paragraph-sized chunks with slight overlap for coherence."
    },
    "STRUCTURED": {
        "extensions": [
            ".json", ".xml", ".yaml", ".yml", ".toml", ".ini"
        ],
        "chunk_size": 5000,
        "overlap": 0,
        "notes": "Keep structure intact; avoid overlap to prevent syntax breaks."
    },
    "SPREADSHEETS": {
        "extensions": [
            ".xlsx", ".xls", ".csv"
        ],
        "chunk_size": 4000,
        "overlap": 50,
        "notes": "Balance row context with chunk size."
    },
    "MEDIA": {
        "extensions": [
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4", ".mp3", ".wav"
        ],
        "chunk_size": 0,
        "overlap": 0,
        "notes": "Media typically not text-indexed; consider captions/transcripts."
    }
}

ALL_KNOWN_EXTS = {ext: cat for cat, spec in CATEGORIES.items() for ext in spec["extensions"]}


@dataclass
class CategoryCounts:
    category: str
    count: int
    size_bytes: int
    extensions: Dict[str, int]


@dataclass
class Recommendation:
    recommended_vertical: str
    confidence: float
    reasoning: str
    total_files: int
    counts_by_category: List[CategoryCounts]
    suggested_chunk_size: int
    suggested_overlap: int
    indexed_extensions: str  # comma-separated


def scan_directory(path: Path) -> List[Path]:
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if path.is_file():
        return [path]
    # Recurse and include only files
    return [p for p in path.rglob('*') if p.is_file()]


def categorize_extension(ext: str) -> str:
    ext = ext.lower()
    return ALL_KNOWN_EXTS.get(ext, "UNKNOWN")


def tally_files(files: List[Path]) -> Dict[str, CategoryCounts]:
    counts: Dict[str, CategoryCounts] = {}
    for cat in list(CATEGORIES.keys()) + ["UNKNOWN"]:
        counts[cat] = CategoryCounts(category=cat, count=0, size_bytes=0, extensions={})

    for f in files:
        ext = f.suffix.lower()
        cat = categorize_extension(ext)
        try:
            size = f.stat().st_size
        except Exception:
            size = 0
        entry = counts[cat]
        entry.count += 1
        entry.size_bytes += size
        entry.extensions[ext] = entry.extensions.get(ext, 0) + 1

    return counts


def choose_vertical(counts: Dict[str, CategoryCounts]) -> Tuple[str, float, str]:
    """Choose the best vertical and return (category, confidence, reasoning)."""
    total = sum(c.count for c in counts.values())
    if total == 0:
        return ("UNKNOWN", 0.0, "No files found.")

    # Sort by count desc (ignore UNKNOWN unless everything is UNKNOWN)
    sorted_cats = sorted(
        (c for c in counts.values() if c.category != "UNKNOWN"),
        key=lambda x: x.count,
        reverse=True,
    )

    if not sorted_cats or sorted_cats[0].count == 0:
        return ("UNKNOWN", 0.1, "All files are of unknown types.")

    top = sorted_cats[0]
    share = top.count / total

    # Confidence heuristic
    if share >= 0.9:
        conf = 0.95
        note = "Clear majority of files belong to this category."
    elif share >= 0.75:
        conf = 0.85
        note = "Strong majority; a few outliers present."
    elif share >= 0.6:
        conf = 0.7
        note = "Majority present; consider filtering outliers if needed."
    else:
        conf = 0.5
        note = "Mixed content; recommending best fit but consider splitting."

    # If top is MEDIA and there are many DOCS too, adjust note
    if top.category == "MEDIA" and counts.get("DOCUMENTS", CategoryCounts("DOCUMENTS", 0, 0, {})).count > 0:
        note += " Media typically not text-indexed; you may exclude them or add captions."

    return (top.category, conf, note)


def build_recommendation(counts: Dict[str, CategoryCounts]) -> Recommendation:
    cat, conf, note = choose_vertical(counts)
    total = sum(c.count for c in counts.values())

    if cat in CATEGORIES:
        chunk = CATEGORIES[cat]["chunk_size"]
        overlap = CATEGORIES[cat]["overlap"]
        idx_exts = ",".join(sorted(CATEGORIES[cat]["extensions"]))
    else:
        chunk, overlap, idx_exts = 2000, 100, ""

    return Recommendation(
        recommended_vertical=cat,
        confidence=round(conf, 2),
        reasoning=note,
        total_files=total,
        counts_by_category=[counts[k] for k in ["CODE", "DOCUMENTS", "STRUCTURED", "SPREADSHEETS", "MEDIA", "UNKNOWN"]],
        suggested_chunk_size=chunk,
        suggested_overlap=overlap,
        indexed_extensions=idx_exts,
    )


def print_human(rec: Recommendation):
    def human_size(n: int) -> str:
        x = float(n)
        for u in ["B", "KB", "MB", "GB"]:
            if x < 1024:
                return f"{x:.1f} {u}"
            x /= 1024
        return f"{x:.1f} TB"

    print("\n=== Vertical Recommendation ===")
    print(f"Recommended: {rec.recommended_vertical}")
    print(f"Confidence : {int(rec.confidence * 100)}%")
    print(f"Reasoning  : {rec.reasoning}")
    print(f"Total Files: {rec.total_files}")

    print("\nBreakdown by Category:")
    for c in rec.counts_by_category:
        if c.count == 0:
            continue
        exts = ", ".join(f"{e}({n})" for e, n in sorted(c.extensions.items(), key=lambda kv: kv[1], reverse=True)[:10])
        print(f"  - {c.category:12s} files={c.count:5d} size={human_size(c.size_bytes):>8s}  exts: {exts}")

    print("\nSuggested Settings:")
    print(f"  chunk_size       = {rec.suggested_chunk_size}")
    print(f"  overlap          = {rec.suggested_overlap}")
    if rec.indexed_extensions:
        print(f"  indexed_extensions (for indexer) = {rec.indexed_extensions}")

    print("\nNext steps:")
    if rec.recommended_vertical == "UNKNOWN":
        print("  - Review file types; add missing extensions or choose the closest vertical manually.")
    else:
        print("  - Use this vertical type when creating the index (e.g., choose prefix matching the vertical).")
        print("  - Optionally filter files to only the listed extensions before upload.")


@click.group()
def cli():
    """Vertical Recommender CLI"""
    pass


@cli.command("recommend")
@click.argument("path", type=click.Path(exists=True))
@click.option("--json-out", is_flag=True, help="Output JSON to stdout instead of human-readable text")
@click.option("--recursive/--no-recursive", default=True, help="Recurse into subfolders (default: True)")
def recommend_cmd(path: str, json_out: bool, recursive: bool):
    base = Path(path)

    # Scan files
    if base.is_dir() and recursive:
        files = [p for p in base.rglob('*') if p.is_file()]
    else:
        files = scan_directory(base)

    counts = tally_files(files)
    rec = build_recommendation(counts)

    if json_out:
        # Convert dataclasses for JSON
        payload = asdict(rec)
        payload["counts_by_category"] = [
            {
                "category": c.category,
                "count": c.count,
                "size_bytes": c.size_bytes,
                "extensions": c.extensions,
            } for c in rec.counts_by_category
        ]
        print(json.dumps(payload, indent=2))
    else:
        print_human(rec)


if __name__ == "__main__":
    cli()
