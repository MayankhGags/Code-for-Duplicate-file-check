"""
Duplicate File Checker Engine.

Identifies duplicate files using a multi-stage filtering pipeline:
1. Recursive filesystem traversal.
2. File size comparison (fast pre-filtering; unique sizes cannot be duplicates).
3. Cryptographic SHA-256 hashing on size-matched candidates using chunked reads.
4. Duplicate grouping and wasted disk space quantification.
5. Robust error handling for permission issues and locked files.
"""

import hashlib
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB chunk size for memory-efficient hashing


def format_bytes(size_bytes: int) -> str:
    """Formats a byte count into a human-readable string (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
    return f"{size_bytes:.2f} PB"


@dataclass
class DuplicateGroup:
    """Represents a set of identical duplicate files."""
    file_hash: str
    file_size: int
    files: List[str]

    @property
    def duplicate_count(self) -> int:
        return len(self.files)

    @property
    def redundant_file_count(self) -> int:
        """Count of extra redundant copies (excluding one original)."""
        return max(0, len(self.files) - 1)

    @property
    def wasted_space_bytes(self) -> int:
        """Total disk space occupied by redundant copies."""
        return self.redundant_file_count * self.file_size


@dataclass
class ScanReport:
    """Encapsulates results from a duplicate file scan."""
    target_directory: str
    total_files_scanned: int = 0
    candidate_files_hashed: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    inaccessible_files: List[Tuple[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def total_duplicate_files(self) -> int:
        return sum(len(group.files) for group in self.duplicate_groups)

    @property
    def total_redundant_files(self) -> int:
        return sum(group.redundant_file_count for group in self.duplicate_groups)

    @property
    def total_wasted_space_bytes(self) -> int:
        return sum(group.wasted_space_bytes for group in self.duplicate_groups)


class DuplicateFileChecker:
    """Core engine for detecting duplicate files."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        min_file_size: int = 0,
        include_empty_files: bool = False
    ):
        """
        Args:
            chunk_size: Read buffer size in bytes for SHA-256 calculation.
            min_file_size: Minimum file size in bytes to consider.
            include_empty_files: Whether to evaluate 0-byte files as duplicates.
        """
        self.chunk_size = chunk_size
        self.min_file_size = min_file_size
        self.include_empty_files = include_empty_files

    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        Computes the SHA-256 hash of a file using buffered chunked reads.

        Args:
            file_path: Absolute path to the file.

        Returns:
            Hexadecimal SHA-256 hash string, or None if file cannot be read.
        """
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (PermissionError, OSError):
            return None

    def scan(self, target_directory: str) -> ScanReport:
        """
        Scans target directory recursively and returns duplicate file report.

        Args:
            target_directory: Root directory to scan.

        Returns:
            ScanReport containing detailed duplicate analysis.
        """
        start_time = time.time()
        report = ScanReport(target_directory=os.path.abspath(target_directory))

        if not os.path.exists(target_directory):
            raise FileNotFoundError(f"Target directory does not exist: {target_directory}")

        if not os.path.isdir(target_directory):
            raise NotADirectoryError(f"Target path is not a directory: {target_directory}")

        # -----------------------------------------------------------------
        # STAGE 1: Recursive Traversal & File Size Grouping
        # -----------------------------------------------------------------
        size_buckets: Dict[int, List[str]] = defaultdict(list)

        for root, _, files in os.walk(target_directory, onerror=None):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                report.total_files_scanned += 1

                try:
                    # Ignore symlinks to prevent duplicate loops
                    if os.path.islink(file_path):
                        continue

                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size

                    # Filter by size criteria
                    if file_size < self.min_file_size:
                        continue
                    if file_size == 0 and not self.include_empty_files:
                        continue

                    size_buckets[file_size].append(file_path)

                except (PermissionError, OSError) as err:
                    report.inaccessible_files.append((file_path, str(err)))

        # -----------------------------------------------------------------
        # STAGE 2: Filter Potential Candidates by Size
        # (Files with unique sizes are skipped from hashing)
        # -----------------------------------------------------------------
        candidate_buckets: Dict[int, List[str]] = {
            size: paths for size, paths in size_buckets.items() if len(paths) >= 2
        }

        # -----------------------------------------------------------------
        # STAGE 3: Cryptographic SHA-256 Hashing on Candidates
        # -----------------------------------------------------------------
        for size, file_paths in candidate_buckets.items():
            hash_groups: Dict[str, List[str]] = defaultdict(list)

            for file_path in file_paths:
                report.candidate_files_hashed += 1
                file_hash = self.calculate_file_hash(file_path)

                if file_hash is None:
                    report.inaccessible_files.append((file_path, "Permission denied / read error"))
                    continue

                hash_groups[file_hash].append(file_path)

            # -----------------------------------------------------------------
            # STAGE 4: Group Confirmed Duplicates
            # -----------------------------------------------------------------
            for file_hash, matching_paths in hash_groups.items():
                if len(matching_paths) >= 2:
                    report.duplicate_groups.append(
                        DuplicateGroup(
                            file_hash=file_hash,
                            file_size=size,
                            files=sorted(matching_paths)
                        )
                    )

        # Sort duplicate groups descending by wasted space
        report.duplicate_groups.sort(key=lambda g: g.wasted_space_bytes, reverse=True)
        report.duration_seconds = time.time() - start_time
        return report
