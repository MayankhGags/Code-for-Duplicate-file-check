"""
Duplicate File Check CLI Application.

A command-line tool that scans a specified directory recursively to locate
and report duplicate files using file size pre-filtering and SHA-256 hashing.

Safety Guarantee: This application NEVER deletes or modifies files.
"""

import argparse
import json
import os
import sys

from duplicate_checker import DuplicateFileChecker, ScanReport, format_bytes


def print_banner() -> None:
    print("=" * 78)
    print("                DUPLICATE FILE DETECTION SYSTEM (SHA-256)")
    print("=" * 78)


def display_report(report: ScanReport) -> None:
    """Renders formatted command-line output of duplicate detection results."""
    print(f"\nScanned Directory : {report.target_directory}")
    print(f"Scan Duration     : {report.duration_seconds:.2f} seconds")
    print(f"Total Files Found : {report.total_files_scanned}")
    print(f"Candidates Hashed : {report.candidate_files_hashed} (Files with matching sizes)")
    print("-" * 78)

    if not report.duplicate_groups:
        print("\n[Result] No duplicate files were found in the scanned directory.")
        print("-" * 78)
        return

    print(f"\nDiscovered {len(report.duplicate_groups)} group(s) of duplicate files:\n")

    for idx, group in enumerate(report.duplicate_groups, 1):
        print(f"--- Duplicate Group #{idx} ---")
        print(f"  SHA-256 Hash : {group.file_hash}")
        print(f"  File Size    : {format_bytes(group.file_size)} ({group.file_size:,} bytes)")
        print(f"  Total Copies : {group.duplicate_count} files (Wasted: {format_bytes(group.wasted_space_bytes)})")
        print("  Locations:")
        print(f"    [Original] {group.files[0]}")
        for copy_path in group.files[1:]:
            print(f"    [Copy]     {copy_path}")
        print()

    print("=" * 78)
    print("                          SCAN SUMMARY METRICS")
    print("=" * 78)
    print(f"Total Files Scanned           : {report.total_files_scanned:,}")
    print(f"Duplicate Groups Identified   : {len(report.duplicate_groups):,}")
    print(f"Total Duplicate Files         : {report.total_duplicate_files:,}")
    print(f"Redundant / Excess Copies     : {report.total_redundant_files:,}")
    print(f"Potential Recoverable Space   : {format_bytes(report.total_wasted_space_bytes)} ({report.total_wasted_space_bytes:,} bytes)")

    if report.inaccessible_files:
        print(f"\n[Warning] {len(report.inaccessible_files)} file(s) could not be accessed due to permissions or OS locks:")
        for path, err in report.inaccessible_files[:5]:
            print(f"  - {path}: {err}")
        if len(report.inaccessible_files) > 5:
            print(f"  ... and {len(report.inaccessible_files) - 5} more files.")

    print("\n[Safety Guarantee] No files have been deleted. Review the reported locations above.")
    print("=" * 78 + "\n")


def export_json(report: ScanReport, json_path: str) -> None:
    """Exports scan report details to a JSON file."""
    data = {
        "target_directory": report.target_directory,
        "scan_duration_seconds": report.duration_seconds,
        "total_files_scanned": report.total_files_scanned,
        "duplicate_groups_count": len(report.duplicate_groups),
        "total_duplicate_files": report.total_duplicate_files,
        "total_redundant_copies": report.total_redundant_files,
        "total_wasted_space_bytes": report.total_wasted_space_bytes,
        "duplicate_groups": [
            {
                "sha256": g.file_hash,
                "file_size_bytes": g.file_size,
                "copies_count": g.duplicate_count,
                "wasted_bytes": g.wasted_space_bytes,
                "files": g.files
            }
            for g in report.duplicate_groups
        ],
        "inaccessible_files": [
            {"path": path, "error": err} for path, err in report.inaccessible_files
        ]
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Export] Duplicate report saved to JSON: {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Duplicate File Check - Fast, Safe Duplicate File Detection Using SHA-256"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Path to directory to scan (default: current directory)"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help="Minimum file size in bytes to inspect (default: 0)"
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include zero-byte files in duplicate detection (default: false)"
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Optional path to output results in JSON format"
    )

    args = parser.parse_args()

    print_banner()

    try:
        checker = DuplicateFileChecker(
            min_file_size=args.min_size,
            include_empty_files=args.include_empty
        )
        report = checker.scan(args.directory)
        display_report(report)

        if args.json:
            export_json(report, args.json)

    except (FileNotFoundError, NotADirectoryError) as err:
        print(f"\n[Error] {err}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Scan Aborted] Scan interrupted by user.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
