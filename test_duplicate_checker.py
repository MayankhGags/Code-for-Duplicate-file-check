"""
Unit Tests for Duplicate File Check Application.

Tests:
1. Recursive filesystem scanning across subdirectories.
2. File size pre-filtering (ensures unique sizes are skipped).
3. SHA-256 hashing accuracy and identical content detection.
4. Distinguishing files with identical sizes but different content.
5. Wasted disk space computation.
6. Empty file handling.
"""

import os
import shutil
import tempfile
import unittest

from duplicate_checker import DuplicateFileChecker, format_bytes


class TestDuplicateFileChecker(unittest.TestCase):
    """Test suite for duplicate file detection logic."""

    def setUp(self):
        # Create a temporary directory for isolated filesystem testing
        self.test_dir = tempfile.mkdtemp(prefix="dup_test_")

        # Subdirectories
        self.sub_a = os.path.join(self.test_dir, "folder_a")
        self.sub_b = os.path.join(self.test_dir, "folder_b")
        os.makedirs(self.sub_a)
        os.makedirs(self.sub_b)

        # 1. Unique file
        with open(os.path.join(self.test_dir, "unique_1.txt"), "w") as f:
            f.write("This is a unique file with unique size and content.")

        # 2. Pair of duplicate files (file1 in root, file2 in folder_a)
        content_dup1 = "Exact duplicate payload for testing SHA-256 matching."
        with open(os.path.join(self.test_dir, "dup1_original.txt"), "w") as f:
            f.write(content_dup1)
        with open(os.path.join(self.sub_a, "dup1_copy.txt"), "w") as f:
            f.write(content_dup1)

        # 3. Triplet of duplicates across root, folder_a, folder_b
        content_dup2 = "Triplet duplicate dataset payload across nested directories."
        with open(os.path.join(self.test_dir, "triplet_1.dat"), "w") as f:
            f.write(content_dup2)
        with open(os.path.join(self.sub_a, "triplet_2.dat"), "w") as f:
            f.write(content_dup2)
        with open(os.path.join(self.sub_b, "triplet_3.dat"), "w") as f:
            f.write(content_dup2)

        # 4. Same size, different content (to test collision prevention)
        with open(os.path.join(self.test_dir, "same_size_A.txt"), "w") as f:
            f.write("1234567890ABCDEF")  # 16 bytes
        with open(os.path.join(self.test_dir, "same_size_B.txt"), "w") as f:
            f.write("0987654321FEDCBA")  # 16 bytes

        # 5. Empty files (0 bytes)
        with open(os.path.join(self.test_dir, "empty_1.txt"), "w") as f:
            pass
        with open(os.path.join(self.sub_b, "empty_2.txt"), "w") as f:
            pass

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_duplicate_detection(self):
        """Verifies duplicate groups are correctly identified without false positives."""
        checker = DuplicateFileChecker(include_empty_files=False)
        report = checker.scan(self.test_dir)

        # Expected duplicate groups:
        # 1. Triplet (3 files)
        # 2. Pair (2 files)
        # Total duplicate groups = 2
        self.assertEqual(len(report.duplicate_groups), 2, "Should find exactly 2 duplicate groups.")

        # Check group counts
        group_counts = sorted([len(g.files) for g in report.duplicate_groups])
        self.assertEqual(group_counts, [2, 3])

        # Check total duplicate files = 2 + 3 = 5
        self.assertEqual(report.total_duplicate_files, 5)

        # Check total redundant files = (2 - 1) + (3 - 1) = 1 + 2 = 3
        self.assertEqual(report.total_redundant_files, 3)

    def test_same_size_different_content_not_flagged(self):
        """Verifies that files with matching size but differing contents are not marked duplicate."""
        checker = DuplicateFileChecker()
        report = checker.scan(self.test_dir)

        all_duplicate_paths = []
        for g in report.duplicate_groups:
            all_duplicate_paths.extend(g.files)

        self.assertNotIn(os.path.join(self.test_dir, "same_size_A.txt"), all_duplicate_paths)
        self.assertNotIn(os.path.join(self.test_dir, "same_size_B.txt"), all_duplicate_paths)

    def test_empty_files_handling(self):
        """Verifies 0-byte files are ignored by default and captured when requested."""
        # Ignored by default
        checker_no_empty = DuplicateFileChecker(include_empty_files=False)
        report1 = checker_no_empty.scan(self.test_dir)
        has_empty_group = any(g.file_size == 0 for g in report1.duplicate_groups)
        self.assertFalse(has_empty_group)

        # Captured when include_empty_files=True
        checker_with_empty = DuplicateFileChecker(include_empty_files=True)
        report2 = checker_with_empty.scan(self.test_dir)
        empty_groups = [g for g in report2.duplicate_groups if g.file_size == 0]
        self.assertEqual(len(empty_groups), 1)
        self.assertEqual(len(empty_groups[0].files), 2)

    def test_wasted_space_calculation(self):
        """Verifies mathematical accuracy of wasted disk space calculation."""
        checker = DuplicateFileChecker()
        report = checker.scan(self.test_dir)

        calculated_wasted = 0
        for group in report.duplicate_groups:
            expected_group_wasted = (len(group.files) - 1) * group.file_size
            self.assertEqual(group.wasted_space_bytes, expected_group_wasted)
            calculated_wasted += expected_group_wasted

        self.assertEqual(report.total_wasted_space_bytes, calculated_wasted)
        self.assertGreater(report.total_wasted_space_bytes, 0)

    def test_format_bytes_utility(self):
        """Tests human readable formatting utility."""
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1048576), "1.00 MB")
        self.assertEqual(format_bytes(1073741824), "1.00 GB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
