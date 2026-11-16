# Duplicate File Check System

A high-performance, memory-efficient Python application that identifies duplicate files across directory hierarchies using two-phase **file size pre-filtering** and **cryptographic SHA-256 checksum verification**.

---

## 1. Project Objective

The objective of this project is to reliably detect redundant and duplicate files without unnecessary disk reads:
- Recursively traverses directories and subdirectories.
- Implements an initial **size-based pre-filtering** stage (files with unique sizes are skipped from hashing entirely).
- Calculates **SHA-256 hashes** using chunked buffered reads to handle arbitrarily large files without high RAM consumption.
- Groups identical files and calculates potential recoverable disk space ($(\text{Copies} - 1) \times \text{Size}$).
- Handles inaccessible files and permission errors gracefully without crashing.
- Enforces an absolute **non-destructive safety guarantee** (never deletes or alters files).

---

## 2. Technologies Used

- **Language:** Python 3.8+ (Standard Library)
- **Key Modules:** `hashlib`, `os`, `argparse`, `dataclasses`, `collections`, `json`, `time`
- **Dependencies:** None (Zero third-party package dependencies)

---

## 3. Detection Architecture & Optimization

```
[ Root Directory ]
       │
       ▼
┌──────────────────────────────┐
│  RECURSIVE DIRECTORY SCAN    │  Collects file paths and metadata using
└──────────────┬───────────────┘  os.walk with permission error protection.
       │
       ▼
┌──────────────────────────────┐
│  STAGE 1: FILE SIZE FILTER   │  Groups files by st_size.
└──────────────┬───────────────┘  Files with unique sizes are excluded immediately!
       │
       ▼ (Only candidates with matching sizes)
┌──────────────────────────────┐
│  STAGE 2: SHA-256 HASHING    │  Computes cryptographic hash via chunked reads
└──────────────┬───────────────┘  (64 KB buffers) to ensure constant memory usage.
       │
       ▼
┌──────────────────────────────┐
│  STAGE 3: DUPLICATE GROUPING │  Groups verified matches and computes
└──────────────┬───────────────┘  redundant count and wasted disk space.
       │
       ▼
[ Formatted CLI Report & Optional JSON Export ]
```

---

## 4. File Structure

```
Code-for-Duplicate-file-check/
├── README.md                 # Project documentation and performance design
├── requirements.txt          # Python dependency specifications
├── main.py                   # Command-line interface and reporting runner
├── duplicate_checker.py      # Core detection engine (hashing, scanning, grouping)
├── test_duplicate_checker.py # Automated unit test suite with isolated fixtures
├── sample_test_files/        # Illustrative test files demonstrating duplicate detection
│   ├── doc1.txt
│   ├── doc1_copy.txt
│   ├── unique_notes.txt
│   └── nested/
│       └── doc1_backup.txt
└── .gitignore                # Standard Python gitignore rules
```

---

## 5. Execution Instructions

### A. Quick Start with Included Sample Files:
```bash
python main.py sample_test_files
```

### B. Scanning a Target Directory:
```bash
# Scan current directory:
python main.py .

# Scan an external directory:
python main.py "C:\path\to\documents"

# Ignore small files below 1 KB (1024 bytes):
python main.py "C:\path\to\documents" --min-size 1024

# Include zero-byte empty files:
python main.py "C:\path\to\documents" --include-empty

# Export report to JSON for downstream auditing:
python main.py "C:\path\to\documents" --json duplicate_audit.json
```

### C. Running Unit Tests:
```bash
python test_duplicate_checker.py
```

---

## 6. Expected Output

```
==============================================================================
                DUPLICATE FILE DETECTION SYSTEM (SHA-256)
==============================================================================

Scanned Directory : C:\Users\mayan\Documents\Code-for-Duplicate-file-check\sample_test_files
Scan Duration     : 0.00 seconds
Total Files Found : 4
Candidates Hashed : 3 (Files with matching sizes)
------------------------------------------------------------------------------

Discovered 1 group(s) of duplicate files:

--- Duplicate Group #1 ---
  SHA-256 Hash : da101a405af54b6b877ea3afe48d8a74dbb28cc2978fcf08bb32b65c7ff32031
  File Size    : 147 B (147 bytes)
  Total Copies : 3 files (Wasted: 294 B)
  Locations:
    [Original] sample_test_files\doc1.txt
    [Copy]     sample_test_files\doc1_copy.txt
    [Copy]     sample_test_files\nested\doc1_backup.txt

==============================================================================
                          SCAN SUMMARY METRICS
==============================================================================
Total Files Scanned           : 4
Duplicate Groups Identified   : 1
Total Duplicate Files         : 3
Redundant / Excess Copies     : 2
Potential Recoverable Space   : 294 B (294 bytes)

[Safety Guarantee] No files have been deleted. Review the reported locations above.
==============================================================================
```
