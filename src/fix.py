# #!/usr/bin/env python3
# """
# fix_encoding.py — JSON Encoding Fixer
# ======================================
# Detects and fixes mojibake (garbled text) inside JSON files.
# Walks every string value recursively, fixes in-place, and writes
# clean JSON output. Supports a single file or an entire directory.

# Usage
# -----
#   # Single file
#   python fix_encoding.py data.json

#   # Single file with custom output path
#   python fix_encoding.py data.json --output fixed/data.json

#   # Entire directory (mirrors structure into output dir)
#   python fix_encoding.py ./scraped_data/ --output ./fixed_data/

#   # Dry-run: show what would be fixed without writing anything
#   python fix_encoding.py ./scraped_data/ --dry-run
# """

# import argparse
# import json
# import re
# import sys
# from pathlib import Path

# import chardet


# # ── Mojibake detection & repair ───────────────────────────────────────────────

# _MOJIBAKE_RE = re.compile(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ¸¹º»¼½¾¿]{2,}')

# _ENCODING_PAIRS = [
#     ("latin-1", "utf-8"),
#     ("cp1252",  "utf-8"),
#     ("latin-1", "tis-620"),
#     ("cp1252",  "tis-620"),
# ]


# def is_mojibake(text: str) -> bool:
#     return bool(_MOJIBAKE_RE.search(text))


# def fix_mojibake(text: str) -> tuple[str, bool]:
#     if not is_mojibake(text):
#         return text, False
#     for read_as, actual in _ENCODING_PAIRS:
#         try:
#             fixed = text.encode(read_as).decode(actual)
#             if not is_mojibake(fixed):
#                 return fixed, True
#         except (UnicodeEncodeError, UnicodeDecodeError):
#             continue
#     return text, False


# # ── Recursive JSON walker ─────────────────────────────────────────────────────

# def _walk(node, stats: dict) -> object:
#     if isinstance(node, dict):
#         return {k: _walk(v, stats) for k, v in node.items()}
#     if isinstance(node, list):
#         return [_walk(item, stats) for item in node]
#     if isinstance(node, str):
#         stats["strings_checked"] += 1
#         if is_mojibake(node):
#             stats["garbled_found"] += 1
#             fixed, changed = fix_mojibake(node)
#             if changed:
#                 stats["fixed"] += 1
#                 stats["changes"].append({"before": node, "after": fixed})
#             else:
#                 stats["failed"] += 1
#                 stats["unfixable"].append(node)
#             return fixed
#         return node
#     return node


# # ── File-level processor ──────────────────────────────────────────────────────

# def process_file(input_path: Path, output_path: Path, dry_run: bool = False) -> dict:
#     raw      = input_path.read_bytes()
#     detected = chardet.detect(raw)
#     enc      = detected.get("encoding") or "utf-8"
#     confidence = detected.get("confidence", 0)

#     try:
#         data = json.loads(raw.decode(enc, errors="replace"))
#     except json.JSONDecodeError as e:
#         print(f"  ✗ [SKIP] Not valid JSON: {input_path}  ({e})")
#         return {"file": str(input_path), "skipped": True, "reason": str(e)}

#     stats: dict = {
#         "file":            str(input_path),
#         "detected_enc":    enc,
#         "enc_confidence":  f"{confidence:.0%}",
#         "strings_checked": 0,
#         "garbled_found":   0,
#         "fixed":           0,
#         "failed":          0,
#         "changes":         [],
#         "unfixable":       [],
#         "skipped":         False,
#         "dry_run":         dry_run,
#     }

#     fixed_data = _walk(data, stats)

#     if not dry_run:
#         output_path.parent.mkdir(parents=True, exist_ok=True)
#         output_path.write_text(
#             json.dumps(fixed_data, ensure_ascii=False, indent=2),
#             encoding="utf-8",
#         )

#     tag = "[DRY-RUN]" if dry_run else ("[FIXED]  " if stats["fixed"] else "[CLEAN]  ")
#     print(
#         f"  {tag} {input_path.name:<40} "
#         f"garbled: {stats['garbled_found']:>3}  "
#         f"fixed: {stats['fixed']:>3}  "
#         f"failed: {stats['failed']:>3}  "
#         f"enc: {enc}"
#     )
#     return stats


# # ── Directory processor ───────────────────────────────────────────────────────

# def process_directory(input_dir: Path, output_dir: Path, dry_run: bool = False) -> list[dict]:
#     json_files = sorted(input_dir.rglob("*.json"))
#     if not json_files:
#         print(f"No .json files found in {input_dir}")
#         return []

#     print(f"Found {len(json_files)} JSON file(s) in '{input_dir}'\n")
#     all_stats = []
#     for src in json_files:
#         dst   = output_dir / src.relative_to(input_dir)
#         stats = process_file(src, dst, dry_run=dry_run)
#         all_stats.append(stats)
#     return all_stats


# # ── Report writer ─────────────────────────────────────────────────────────────

# def write_report(all_stats: list[dict], report_path: Path) -> None:
#     skipped = sum(1 for s in all_stats if s.get("skipped"))
#     report = {
#         "summary": {
#             "files_processed": len(all_stats) - skipped,
#             "files_skipped":   skipped,
#             "strings_checked": sum(s.get("strings_checked", 0) for s in all_stats),
#             "garbled_found":   sum(s.get("garbled_found",   0) for s in all_stats),
#             "fixed":           sum(s.get("fixed",           0) for s in all_stats),
#             "failed":          sum(s.get("failed",          0) for s in all_stats),
#         },
#         "files": all_stats,
#     }
#     report_path.parent.mkdir(parents=True, exist_ok=True)
#     report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
#     print(f"  Report  → {report_path}")


# # ── CLI ───────────────────────────────────────────────────────────────────────

# def main() -> None:
#     if len(sys.argv) == 1:
#         print("=== Demo mode ===\n")
#         samples = [
#             "à¸à¸£à¸°à¹",
#             "Hello World",
#             "à¹à¸à¸£à¸­à¸à¸à¸²à¸£",
#             "Price: $100",
#             "ร้านอาหาร",
#         ]
#         print(f"{'Original':<45} {'Fixed':<35} Status")
#         print("-" * 90)
#         for s in samples:
#             fixed, changed = fix_mojibake(s)
#             status = "✅ fixed" if changed else ("⚠️  unfixable" if is_mojibake(s) else "✓  clean")
#             print(f"{s:<45} {fixed:<35} {status}")
#         print("\nUsage: python fix_encoding.py <file_or_dir> [--output <path>] [--dry-run]")
#         return

#     p = argparse.ArgumentParser(description="Fix mojibake encoding in JSON files.")
#     p.add_argument("input",  help="Path to a .json file or a directory.")
#     p.add_argument("--output", "-o", default=None, help="Output file or directory.")
#     p.add_argument("--report", "-r", default=None, help="Path for the JSON report.")
#     p.add_argument("--dry-run", action="store_true", help="Detect only, no files written.")
#     args    = p.parse_args()
#     src     = Path(args.input)
#     dry_run = args.dry_run

#     if not src.exists():
#         sys.exit(f"Error: '{src}' does not exist.")

#     if src.is_file():
#         dst         = Path(args.output) if args.output else src.with_stem(src.stem + ".fixed")
#         report_path = Path(args.report) if args.report else dst.with_suffix(".report.json")
#         print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing file: {src}\n")
#         stats = process_file(src, dst, dry_run=dry_run)
#         if not dry_run:
#             print(f"  Output  → {dst}")
#         write_report([stats], report_path)

#     elif src.is_dir():
#         dst_dir     = Path(args.output) if args.output else src.parent / (src.name + "_fixed")
#         report_path = Path(args.report) if args.report else dst_dir / "_encoding_report.json"
#         print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing directory: {src}")
#         print(f"Output dir: {dst_dir}\n")
#         all_stats = process_directory(src, dst_dir, dry_run=dry_run)
#         write_report(all_stats, report_path)
#         garbled = sum(s.get("garbled_found", 0) for s in all_stats)
#         fixed   = sum(s.get("fixed",         0) for s in all_stats)
#         failed  = sum(s.get("failed",        0) for s in all_stats)
#         print(f"\n{'='*50}")
#         print(f"  Files : {len(all_stats)}  |  Garbled: {garbled}  |  Fixed: {fixed}  |  Failed: {failed}")
#         if not dry_run:
#             print(f"  Output dir → {dst_dir}")
#         print(f"{'='*50}")
#     else:
#         sys.exit(f"Error: '{src}' is neither a file nor a directory.")


# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
"""
fix_encoding.py — JSON Encoding Fixer
======================================
Detects and fixes mojibake (garbled text) inside JSON files.
Walks every string value recursively, fixes in-place, and writes
clean JSON output. Supports a single file or an entire directory.

WHY SOME STRINGS ARE "PARTIAL"
--------------------------------
Thai (and other multibyte) characters are 3-byte UTF-8 sequences, e.g.:
    ก  =  E0 B8 81
When a scraper reads UTF-8 bytes as Latin-1, each byte becomes its own
character: E0→à  B8→¸  81→U+0081.

The problem: byte values 0x80–0x9F are "C1 control characters". Many tools
(HTML parsers, JSON encoders, databases) silently strip these control chars,
so the 3rd byte of ก, ข, ค, ง, เ, แ, โ … is permanently gone.
Those characters CANNOT be recovered and will be shown as a blank/gap.
Strings where all characters survive are marked "fixed"; strings with
at least one lost character are marked "partial".

Usage
-----
  python fix_encoding.py data.json
  python fix_encoding.py data.json --output fixed/data.json
  python fix_encoding.py ./scraped_data/ --output ./fixed_data/
  python fix_encoding.py ./scraped_data/ --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

import chardet


# ── Mojibake detection ────────────────────────────────────────────────────────

# High-byte chars that appear when UTF-8 multibyte sequences are decoded as Latin-1
_MOJIBAKE_RE  = re.compile(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ¸¹º»¼½¾¿]{2,}')
# Split point: keep pure ASCII runs separate so we don't mangle them
_ASCII_SEG_RE = re.compile(r'([ -~\t\n\r]+)')


def is_mojibake(text: str) -> bool:
    return bool(_MOJIBAKE_RE.search(text))


# ── Segment-level fixer ───────────────────────────────────────────────────────

def _fix_segment(seg: str) -> tuple[str, bool]:
    """
    Attempt to re-encode a non-ASCII segment as latin-1 bytes, then decode
    as UTF-8 with errors='replace'.  Replacement chars (U+FFFD) are stripped —
    they represent bytes permanently lost upstream (C1 control chars that were
    stripped by a scraper, HTML parser, or database).

    Returns (fixed_text, had_replacement_chars).
    """
    try:
        raw = seg.encode("latin-1")
    except UnicodeEncodeError:
        # Segment already contains real Unicode above U+00FF — nothing to fix
        return seg, False

    decoded = raw.decode("utf-8", errors="replace")
    had_loss = "\ufffd" in decoded
    return decoded.replace("\ufffd", ""), had_loss


# ── String-level fixer ────────────────────────────────────────────────────────

def fix_string(text: str) -> tuple[str, str]:
    """
    Fix a potentially mojibake string.

    Returns (fixed_text, status) where status is one of:
      "clean"   — no mojibake detected, returned unchanged
      "fixed"   — fully repaired, no data loss
      "partial" — repaired but some characters were permanently lost
      "failed"  — detected as mojibake but could not improve it at all
    """
    if not is_mojibake(text):
        return text, "clean"

    segments   = _ASCII_SEG_RE.split(text)
    out_parts  = []
    any_change = False
    any_loss   = False

    for seg in segments:
        if not seg:
            continue
        if _ASCII_SEG_RE.fullmatch(seg):
            out_parts.append(seg)
            continue

        fixed, had_loss = _fix_segment(seg)
        if fixed != seg:
            any_change = True
        if had_loss:
            any_loss = True
        out_parts.append(fixed)

    result = "".join(out_parts)

    if not any_change:
        return text, "failed"
    if any_loss:
        return result, "partial"
    return result, "fixed"


# ── Recursive JSON walker ─────────────────────────────────────────────────────

def _walk(node, stats: dict) -> object:
    if isinstance(node, dict):
        return {k: _walk(v, stats) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(item, stats) for item in node]
    if isinstance(node, str):
        stats["strings_checked"] += 1
        fixed, status = fix_string(node)
        if status == "fixed":
            stats["fixed"] += 1
            stats["changes"].append({"before": node, "after": fixed, "status": "fixed"})
        elif status == "partial":
            stats["partial"] += 1
            stats["garbled_found"] += 1
            stats["changes"].append({"before": node, "after": fixed, "status": "partial",
                                     "note": "Some chars permanently lost (C1 bytes stripped upstream)"})
        elif status == "failed":
            stats["garbled_found"] += 1
            stats["failed"] += 1
            stats["unfixable"].append(node)
        # "clean" — nothing to record
        return fixed
    return node


# ── File processor ────────────────────────────────────────────────────────────

def process_file(input_path: Path, output_path: Path, dry_run: bool = False) -> dict:
    raw      = input_path.read_bytes()
    detected = chardet.detect(raw)
    enc      = detected.get("encoding") or "utf-8"
    confidence = detected.get("confidence", 0)

    try:
        data = json.loads(raw.decode(enc, errors="replace"))
    except json.JSONDecodeError as e:
        print(f"  ✗ [SKIP   ] Not valid JSON: {input_path}  ({e})")
        return {"file": str(input_path), "skipped": True, "reason": str(e)}

    stats: dict = {
        "file":            str(input_path),
        "detected_enc":    enc,
        "enc_confidence":  f"{confidence:.0%}",
        "strings_checked": 0,
        "garbled_found":   0,
        "fixed":           0,
        "partial":         0,
        "failed":          0,
        "changes":         [],
        "unfixable":       [],
        "skipped":         False,
        "dry_run":         dry_run,
    }

    fixed_data = _walk(data, stats)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(fixed_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if dry_run:
        tag = "[DRY-RUN ]"
    elif stats["partial"]:
        tag = "[PARTIAL ]"
    elif stats["fixed"]:
        tag = "[FIXED   ]"
    else:
        tag = "[CLEAN   ]"

    print(
        f"  {tag} {input_path.name:<38} "
        f"fixed: {stats['fixed']:>3}  "
        f"partial: {stats['partial']:>3}  "
        f"failed: {stats['failed']:>3}  "
        f"enc: {enc}"
    )
    if stats["partial"] and not dry_run:
        print(f"           ⚠  {stats['partial']} string(s) partially recovered "
              f"— some Thai chars (ก ข ค ง เ แ โ …) were lost upstream and cannot be restored.")

    return stats


# ── Directory processor ───────────────────────────────────────────────────────

def process_directory(input_dir: Path, output_dir: Path, dry_run: bool = False) -> list[dict]:
    json_files = sorted(input_dir.rglob("*.json"))
    if not json_files:
        print(f"No .json files found in {input_dir}")
        return []

    print(f"Found {len(json_files)} JSON file(s) in '{input_dir}'\n")
    all_stats = []
    for src in json_files:
        dst   = output_dir / src.relative_to(input_dir)
        stats = process_file(src, dst, dry_run=dry_run)
        all_stats.append(stats)
    return all_stats


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(all_stats: list[dict], report_path: Path) -> None:
    skipped = sum(1 for s in all_stats if s.get("skipped"))
    report = {
        "summary": {
            "files_processed": len(all_stats) - skipped,
            "files_skipped":   skipped,
            "strings_checked": sum(s.get("strings_checked", 0) for s in all_stats),
            "fully_fixed":     sum(s.get("fixed",           0) for s in all_stats),
            "partially_fixed": sum(s.get("partial",         0) for s in all_stats),
            "failed":          sum(s.get("failed",          0) for s in all_stats),
            "note_partial": (
                "Partial strings had C1 control bytes (0x80-0x9F) stripped upstream. "
                "Affected Thai chars: ก ข ค ง เ แ โ and others. These cannot be recovered."
            ),
        },
        "files": all_stats,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Report  → {report_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) == 1:
        print("=== Demo mode ===\n")
        samples = [
            # Fully fixable (all 3rd bytes >= 0xA0)
            ("à¹à¸à¸£à¸­à¸à¸à¸²à¸£",           "โครงการ — but 3rd bytes of โค ง are lost"),
            ("à¸•à¹\u0089à¸¡à¸¢à¸³",            "ต้มยำ (should fix cleanly)"),
            # Mixed with ASCII — has lost chars
            ("à¸à¸£à¸à¸­à¸°à¸¡à¸´à¹à¸(Amino acid)", "กรดอะมิโน — ก โ have lost bytes"),
            # Clean
            ("Hello World",                        "clean ASCII"),
            ("ร้านอาหาร",                          "already correct UTF-8"),
        ]
        print(f"{'Input (truncated)':<45} {'Output':<30} Status")
        print("-" * 100)
        for s, note in samples:
            fixed, status = fix_string(s)
            print(f"{s[:45]:<45} {fixed:<30} [{status}]  ({note})")
        print()
        print("Statuses:")
        print("  fixed   — fully repaired, no data loss")
        print("  partial — repaired but some chars permanently lost upstream (C1 bytes stripped)")
        print("  failed  — detected as mojibake but could not improve")
        print("  clean   — no mojibake detected")
        print("\nUsage: python fix_encoding.py <file_or_dir> [--output <path>] [--dry-run]")
        return

    p = argparse.ArgumentParser(description="Fix mojibake encoding in JSON files.")
    p.add_argument("input",  help="Path to a .json file or a directory.")
    p.add_argument("--output", "-o", default=None, help="Output file or directory.")
    p.add_argument("--report", "-r", default=None, help="Path for the JSON report.")
    p.add_argument("--dry-run", action="store_true", help="Detect only, no files written.")
    args    = p.parse_args()
    src     = Path(args.input)
    dry_run = args.dry_run

    if not src.exists():
        sys.exit(f"Error: '{src}' does not exist.")

    if src.is_file():
        dst         = Path(args.output) if args.output else src.with_stem(src.stem + ".fixed")
        report_path = Path(args.report) if args.report else dst.with_suffix(".report.json")
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing: {src}\n")
        stats = process_file(src, dst, dry_run=dry_run)
        if not dry_run:
            print(f"  Output  → {dst}")
        write_report([stats], report_path)

    elif src.is_dir():
        dst_dir     = Path(args.output) if args.output else src.parent / (src.name + "_fixed")
        report_path = Path(args.report) if args.report else dst_dir / "_encoding_report.json"
        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing directory: {src}")
        print(f"Output dir: {dst_dir}\n")
        all_stats = process_directory(src, dst_dir, dry_run=dry_run)
        write_report(all_stats, report_path)

        fixed   = sum(s.get("fixed",   0) for s in all_stats)
        partial = sum(s.get("partial", 0) for s in all_stats)
        failed  = sum(s.get("failed",  0) for s in all_stats)
        print(f"\n{'='*58}")
        print(f"  Files: {len(all_stats)}  |  Fixed: {fixed}  |  Partial: {partial}  |  Failed: {failed}")
        if not dry_run:
            print(f"  Output dir → {dst_dir}")
        print(f"{'='*58}")
    else:
        sys.exit(f"Error: '{src}' is neither a file nor a directory.")


if __name__ == "__main__":
    main()
