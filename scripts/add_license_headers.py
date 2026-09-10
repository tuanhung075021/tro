# Copyright (c) 2026 tro Contributors
# SPDX-License-Identifier: MIT
"""
License Header Management Tool for tro project.
Checks and automatically inserts SPDX MIT License headers in source files.
"""

import argparse
import os
from pathlib import Path
import sys

PYTHON_SHELL_EXTENSIONS = {".py", ".sh"}
JS_TS_CSS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".css"}
SUPPORTED_EXTENSIONS = PYTHON_SHELL_EXTENSIONS | JS_TS_CSS_EXTENSIONS

IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "__pycache__",
    "document",
    ".agents",
    ".pytest_cache",
    "env",
}

PYTHON_SHELL_HEADER = (
    "# Copyright (c) 2026 tro Contributors\n"
    "# SPDX-License-Identifier: MIT"
)

JS_TS_CSS_HEADER = (
    "/*\n"
    " * Copyright (c) 2026 tro Contributors\n"
    " * SPDX-License-Identifier: MIT\n"
    " */"
)


def get_license_header(extension: str) -> str:
    """Return the canonical license header for a given file extension."""
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext in PYTHON_SHELL_EXTENSIONS:
        return PYTHON_SHELL_HEADER
    if ext in JS_TS_CSS_EXTENSIONS:
        return JS_TS_CSS_HEADER
    raise ValueError(f"Unsupported source extension: {extension}")


def has_license_header(content: str, extension: str | None = None) -> bool:
    """Check whether the source content has the required license header near the top.

    Verifies that both required text tokens ('Copyright (c) 2026 tro Contributors' and
    'SPDX-License-Identifier: MIT') exist within a valid comment block near the beginning of the file,
    matching the comment syntax for the given file extension.
    """
    if content.startswith("\ufeff"):
        content = content[1:]

    lines = content.splitlines()
    start_idx = 0

    # 1. Skip shebang line if present at line 0
    if lines and lines[0].startswith("#!"):
        start_idx = 1

    # 2. Skip Python encoding declaration if present at line 0 or 1
    # PEP 263: encoding comment must start with '#' and contain 'coding[:=]'
    if start_idx < len(lines):
        candidate_encoding = lines[start_idx].strip()
        if candidate_encoding.startswith("#") and (
            "coding:" in candidate_encoding or "coding=" in candidate_encoding
        ):
            start_idx += 1

    # 3. Skip up to 5 leading blank lines after shebang / encoding
    blank_lines = 0
    while start_idx < len(lines) and not lines[start_idx].strip():
        blank_lines += 1
        start_idx += 1

    if blank_lines > 5 or start_idx >= len(lines):
        return False

    # Determine expected comment style based on extension
    ext = extension.lower() if extension else None
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    is_python_shell = ext in PYTHON_SHELL_EXTENSIONS if ext else None
    is_js_ts_css = ext in JS_TS_CSS_EXTENSIONS if ext else None

    # Inspect candidate lines of the header block (up to 50 lines)
    candidate_lines = lines[start_idx : start_idx + 50]
    top_text = "\n".join(candidate_lines)

    if (
        "Copyright (c) 2026 tro Contributors" not in top_text
        or "SPDX-License-Identifier: MIT" not in top_text
    ):
        return False

    # Verify that the header appears in a valid comment block before any code.
    def check_hash_comments(cand_lines: list[str]) -> bool:
        has_cp = False
        has_spdx = False
        for line in cand_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("#"):
                # Hit code or non-# line before finding both header tokens
                break
            if "Copyright (c) 2026 tro Contributors" in stripped:
                has_cp = True
            if "SPDX-License-Identifier: MIT" in stripped:
                has_spdx = True
            if has_cp and has_spdx:
                return True
        return has_cp and has_spdx

    def check_c_style_comments(cand_lines: list[str]) -> bool:
        # Check block comments /* ... */
        has_cp = False
        has_spdx = False
        in_block = False
        for line in cand_lines:
            stripped = line.strip()
            if not stripped and not in_block:
                continue

            if not in_block:
                if stripped.startswith("/*"):
                    in_block = True
                    if "Copyright (c) 2026 tro Contributors" in stripped:
                        has_cp = True
                    if "SPDX-License-Identifier: MIT" in stripped:
                        has_spdx = True
                    if "*/" in stripped:
                        in_block = False
                        if not stripped.endswith("*/"):
                            break
                        if has_cp and has_spdx:
                            return True
                elif stripped.startswith("//"):
                    if "Copyright (c) 2026 tro Contributors" in stripped:
                        has_cp = True
                    if "SPDX-License-Identifier: MIT" in stripped:
                        has_spdx = True
                    if has_cp and has_spdx:
                        return True
                else:
                    # Non-comment code line encountered before header complete
                    break
            else:
                # Inside block comment
                if "Copyright (c) 2026 tro Contributors" in stripped:
                    has_cp = True
                if "SPDX-License-Identifier: MIT" in stripped:
                    has_spdx = True
                if "*/" in stripped:
                    in_block = False
                    if not stripped.endswith("*/"):
                        break
                    if has_cp and has_spdx:
                        return True
        if has_cp and has_spdx:
            return True

        # Check contiguous // line comments
        has_cp = False
        has_spdx = False
        for line in cand_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("//"):
                break
            if "Copyright (c) 2026 tro Contributors" in stripped:
                has_cp = True
            if "SPDX-License-Identifier: MIT" in stripped:
                has_spdx = True
            if has_cp and has_spdx:
                return True
        return has_cp and has_spdx

    if is_python_shell is True:
        return check_hash_comments(candidate_lines)
    elif is_js_ts_css is True:
        return check_c_style_comments(candidate_lines)
    else:
        return check_hash_comments(candidate_lines) or check_c_style_comments(candidate_lines)


def add_header_to_content(content: str, extension: str) -> str:
    """Prepend the appropriate license header to the source file content."""
    if not extension.startswith("."):
        extension = f".{extension}"
    has_bom = content.startswith("\ufeff")
    raw_content = content[1:] if has_bom else content

    if has_license_header(raw_content, extension):
        return content

    header = get_license_header(extension)
    newline = "\r\n" if "\r\n" in raw_content else "\n"
    formatted_header = header.replace("\n", newline)

    # Empty or whitespace-only content
    if not raw_content.strip():
        result = formatted_header + newline
        return "\ufeff" + result if has_bom else result

    lines = raw_content.splitlines(keepends=True)
    idx = 0

    # Preserve shebang
    if idx < len(lines) and lines[idx].startswith("#!"):
        idx += 1

    # Preserve Python encoding cookie (must start with '#' comment)
    if idx < len(lines):
        line_stripped = lines[idx].strip()
        if line_stripped.startswith("#") and (
            "coding:" in line_stripped or "coding=" in line_stripped
        ):
            idx += 1

    prefix = "".join(lines[:idx])
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += newline

    suffix = "".join(lines[idx:])
    suffix_stripped = suffix.lstrip("\r\n")

    if not prefix:
        if suffix_stripped:
            result = formatted_header + newline + newline + suffix_stripped
        else:
            result = formatted_header + newline
    else:
        if suffix_stripped:
            result = prefix + formatted_header + newline + newline + suffix_stripped
        else:
            result = prefix + formatted_header + newline

    return "\ufeff" + result if has_bom else result


def is_path_ignored(path: Path, base_path: Path | None = None) -> bool:
    """Check if any path component belongs to the ignored directories.

    If base_path is provided, only components relative to base_path are evaluated,
    preventing ancestor directory names from falsely matching ignored directory names.
    """
    path_resolved = path.resolve()
    repo_root = Path(__file__).resolve().parent.parent
    effective_base = (base_path or repo_root).resolve()

    # Target itself is named after an ignored directory
    if path_resolved.name in IGNORED_DIRS:
        return True

    try:
        rel_parts = path_resolved.relative_to(effective_base).parts
        return any(part in IGNORED_DIRS for part in rel_parts)
    except ValueError:
        pass

    # Relative path without base_path
    if not path.is_absolute():
        return any(part in IGNORED_DIRS for part in path.parts)

    return False


def find_source_files(
    target_paths: list[Path], base_root: Path | None = None
) -> list[Path]:
    """Recursively discover all eligible source files from the provided paths."""
    matched_files: list[Path] = []
    repo_root = Path(__file__).resolve().parent.parent
    default_base = (base_root or repo_root).resolve()

    for target in target_paths:
        target_resolved = target.resolve()
        if not target_resolved.exists():
            continue

        # Determine target-specific base root
        try:
            target_resolved.relative_to(default_base)
            root_for_target = default_base
        except ValueError:
            root_for_target = target_resolved if target_resolved.is_dir() else target_resolved.parent

        if is_path_ignored(target_resolved, root_for_target):
            continue

        if target_resolved.is_file():
            if target_resolved.suffix.lower() in SUPPORTED_EXTENSIONS:
                matched_files.append(target_resolved)
        elif target_resolved.is_dir():
            for root_str, dirs, files in os.walk(target_resolved):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                root_path = Path(root_str)
                if is_path_ignored(root_path, root_for_target):
                    continue
                for f in sorted(files):
                    file_path = root_path / f
                    if (
                        not is_path_ignored(file_path, root_for_target)
                        and file_path.suffix.lower() in SUPPORTED_EXTENSIONS
                    ):
                        matched_files.append(file_path)

    # Sort and deduplicate preserving order
    return sorted(list(dict.fromkeys(matched_files)))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check and add MIT license headers to source files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only; exit with code 1 if any file lacks a header, 0 if all are valid.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=None,
        help="Paths to scan (files or directories). Defaults to repository root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main CLI execution flow."""
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent

    if args.paths:
        target_paths: list[Path] = []
        for p in args.paths:
            path_obj = Path(p)
            if not path_obj.exists():
                print(f"Error: Path does not exist: {p}", file=sys.stderr)
                return 1
            target_paths.append(path_obj)
    else:
        target_paths = [repo_root]

    source_files = find_source_files(target_paths, base_root=repo_root)

    if not source_files:
        print("No matching source files found.")
        return 0

    if args.check:
        missing_files: list[Path] = []
        for file_path in source_files:
            try:
                with file_path.open(
                    "r", encoding="utf-8", errors="surrogateescape", newline=""
                ) as f:
                    content = f.read()
                if not has_license_header(content, file_path.suffix):
                    missing_files.append(file_path)
            except Exception as e:
                print(f"Error reading {file_path}: {e}", file=sys.stderr)
                missing_files.append(file_path)

        if missing_files:
            for f in missing_files:
                try:
                    rel_path = f.relative_to(repo_root)
                except ValueError:
                    rel_path = f
                print(f"Missing license header: {rel_path}")
            print(
                f"\nCheck failed: {len(missing_files)} of {len(source_files)} "
                "file(s) lack a valid MIT license header."
            )
            return 1

        print(
            f"Check passed: All {len(source_files)} source file(s) have valid MIT license headers."
        )
        return 0

    # Insertion mode
    added_count = 0
    error_count = 0
    for file_path in source_files:
        try:
            with file_path.open(
                "r", encoding="utf-8", errors="surrogateescape", newline=""
            ) as f:
                content = f.read()
            if not has_license_header(content, file_path.suffix):
                updated = add_header_to_content(content, file_path.suffix)
                with file_path.open(
                    "w", encoding="utf-8", errors="surrogateescape", newline=""
                ) as f:
                    f.write(updated)
                try:
                    rel_path = file_path.relative_to(repo_root)
                except ValueError:
                    rel_path = file_path
                print(f"Added license header to: {rel_path}")
                added_count += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
            error_count += 1

    if error_count > 0:
        print(
            f"\nCompleted with {error_count} error(s) during processing.",
            file=sys.stderr,
        )
        return 1

    if added_count > 0:
        print(f"\nSuccessfully added license headers to {added_count} file(s).")
    else:
        print(f"All {len(source_files)} source file(s) already have valid license headers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
