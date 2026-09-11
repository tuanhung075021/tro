# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""
Comprehensive automated tests for FOSS setup and license header management tool.
Covers R1, R2, R3, all acceptance criteria, and adversarial edge cases.
"""

import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

# Ensure repo root and scripts dir are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import add_license_headers


class TestFossLicenseAndGitIgnore(unittest.TestCase):
    """Tests for Requirement R1: LICENSE and .gitignore configurations."""

    def test_license_file_exists(self):
        license_path = REPO_ROOT / "LICENSE"
        self.assertTrue(license_path.is_file(), "LICENSE file must exist at repository root")

    def test_license_content_mit(self):
        license_content = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_content)
        self.assertIn("Copyright (c) 2026 tro. Contributors", license_content)
        self.assertIn("Permission is hereby granted, free of charge", license_content)
        self.assertIn("WITHOUT WARRANTY OF ANY KIND", license_content)

    def test_gitignore_file_exists(self):
        gitignore_path = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.is_file(), ".gitignore file must exist at repository root")

    def test_gitignore_contains_required_patterns(self):
        gitignore_content = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        patterns = [
            # Python
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            ".venv/",
            "env/",
            "*.egg-info/",
            ".pytest_cache/",
            # Node/Web
            "node_modules/",
            "npm-debug.log*",
            "dist/",
            ".env.local",
            ".env.*.local",
            # Database & Runtime
            "*.db",
            "*.sqlite3",
            "*.log",
            # IDE & OS
            ".vscode/",
            ".idea/",
            "Thumbs.db",
            ".DS_Store",
        ]
        for pattern in patterns:
            self.assertIn(
                pattern,
                gitignore_content,
                f"Pattern '{pattern}' must be present in .gitignore",
            )


class TestRepositoryDirectoryStructure(unittest.TestCase):
    """Tests for Requirement R2: Directory skeleton and .gitkeep files."""

    def test_required_directories_exist(self):
        required_dirs = [
            REPO_ROOT / "core",
            REPO_ROOT / "tests",
            REPO_ROOT / "backend" / "app",
            REPO_ROOT / "frontend",
            REPO_ROOT / "scripts",
        ]
        for d in required_dirs:
            self.assertTrue(d.is_dir(), f"Directory '{d}' must exist")

    def test_gitkeep_files_exist_in_required_directories(self):
        required_gitkeeps = [
            REPO_ROOT / "core" / ".gitkeep",
            REPO_ROOT / "tests" / ".gitkeep",
            REPO_ROOT / "backend" / "app" / ".gitkeep",
            REPO_ROOT / "frontend" / ".gitkeep",
            REPO_ROOT / "scripts" / ".gitkeep",
        ]
        for gk in required_gitkeeps:
            self.assertTrue(gk.is_file(), f".gitkeep file must exist at '{gk}'")


class TestLicenseHeaderScript(unittest.TestCase):
    """Tests for Requirement R3: add_license_headers.py tool and functionality."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_script_has_license_header(self):
        script_path = REPO_ROOT / "scripts" / "add_license_headers.py"
        self.assertTrue(script_path.is_file(), "scripts/add_license_headers.py must exist")
        content = script_path.read_text(encoding="utf-8")
        self.assertTrue(
            add_license_headers.has_license_header(content),
            "scripts/add_license_headers.py must contain the MIT license header at top",
        )

    def test_get_license_header_formats(self):
        py_header = add_license_headers.get_license_header(".py")
        self.assertIn("# Copyright (c) 2026 tro. Contributors", py_header)
        self.assertIn("# SPDX-License-Identifier: MIT", py_header)

        sh_header = add_license_headers.get_license_header(".sh")
        self.assertEqual(py_header, sh_header)

        js_header = add_license_headers.get_license_header(".js")
        self.assertTrue(js_header.startswith("/*\n"))
        self.assertIn(" * Copyright (c) 2026 tro. Contributors", js_header)
        self.assertIn(" * SPDX-License-Identifier: MIT", js_header)
        self.assertTrue(js_header.endswith("\n */"))

        for ext in [".jsx", ".ts", ".tsx", ".css"]:
            self.assertEqual(add_license_headers.get_license_header(ext), js_header)

        with self.assertRaises(ValueError):
            add_license_headers.get_license_header(".txt")

    def test_has_license_header_detection(self):
        # Python format
        py_code = "# Copyright (c) 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n\nprint('hi')\n"
        self.assertTrue(add_license_headers.has_license_header(py_code))

        # JS block comment format
        js_code = "/*\n * Copyright (c) 2026 tro. Contributors\n * SPDX-License-Identifier: MIT\n */\nconsole.log(1);\n"
        self.assertTrue(add_license_headers.has_license_header(js_code))

        # JS line comment format
        js_line_code = "// Copyright (c) 2026 tro. Contributors\n// SPDX-License-Identifier: MIT\nconsole.log(1);\n"
        self.assertTrue(add_license_headers.has_license_header(js_line_code))

        # With shebang
        shebang_code = "#!/bin/bash\n# Copyright (c) 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\necho hi\n"
        self.assertTrue(add_license_headers.has_license_header(shebang_code))

        # With shebang containing flags
        shebang_flags_code = "#!/bin/bash -ex\n# Copyright (c) 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\necho hi\n"
        self.assertTrue(add_license_headers.has_license_header(shebang_flags_code))

        # Missing header
        self.assertFalse(add_license_headers.has_license_header("print('no header')"))
        self.assertFalse(add_license_header := add_license_headers.has_license_header(""))
        self.assertFalse(add_license_headers.has_license_header("   \n\n  "))

        # Partial header (only copyright, missing SPDX)
        partial_1 = "# Copyright (c) 2026 tro. Contributors\nprint('hi')\n"
        self.assertFalse(add_license_headers.has_license_header(partial_1))

        # Partial header (only SPDX, missing copyright)
        partial_2 = "# SPDX-License-Identifier: MIT\nprint('hi')\n"
        self.assertFalse(add_license_headers.has_license_header(partial_2))

        # Header too deep in file (e.g. line 50)
        deep_header = "\n" * 40 + py_code
        self.assertFalse(add_license_headers.has_license_header(deep_header))

        # Adversarial: String assignment containing header tokens must NOT be accepted as a comment header
        code_string = 'msg = "Copyright (c) 2026 tro. Contributors\\nSPDX-License-Identifier: MIT"\nprint(msg)\n'
        self.assertFalse(
            add_license_headers.has_license_header(code_string),
            "Non-comment code strings must not be recognized as valid license headers",
        )

        # Adversarial: Language-specific comment syntax enforcement
        # C-style comment in Python file must NOT be accepted
        py_c_style = "/*\n * Copyright (c) 2026 tro. Contributors\n * SPDX-License-Identifier: MIT\n */\n"
        self.assertFalse(
            add_license_headers.has_license_header(py_c_style, ".py"),
            "C-style comments in Python files must be rejected",
        )
        self.assertFalse(
            add_license_headers.has_license_header(py_c_style, ".sh"),
            "C-style comments in Shell files must be rejected",
        )

        # Hash comment in JS / TS / CSS must NOT be accepted
        js_hash_style = "# Copyright (c) 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n"
        for ext in [".js", ".jsx", ".ts", ".tsx", ".css"]:
            self.assertFalse(
                add_license_headers.has_license_header(js_hash_style, ext),
                f"Hash comments in {ext} files must be rejected",
            )

        # Adversarial: JS block comment without leading asterisk on interior lines
        js_plain_block = "/*\nCopyright (c) 2026 tro. Contributors\nSPDX-License-Identifier: MIT\n*/\nconsole.log(1);\n"
        self.assertTrue(
            add_license_headers.has_license_header(js_plain_block, ".js"),
            "JS block comments without leading '*' must be recognized as valid",
        )

        # Adversarial: Code statements interleaved between header tokens must NOT be accepted
        interleaved_code = (
            "# Copyright (c) 2026 tro. Contributors\n"
            "x = 100\n"
            "# SPDX-License-Identifier: MIT\n"
        )
        self.assertFalse(
            add_license_headers.has_license_header(interleaved_code, ".py"),
            "Headers interleaved with executable code must be rejected",
        )

        # Adversarial: Code preceding header must NOT be accepted
        code_before_header = (
            "print('init')\n"
            "# Copyright (c) 2026 tro. Contributors\n"
            "# SPDX-License-Identifier: MIT\n"
        )
        self.assertFalse(
            add_license_headers.has_license_header(code_before_header, ".py"),
            "Code placed before license header must be rejected",
        )

        # Adversarial: Legacy header without trailing dot in brand name must be rejected
        legacy_py = "# Copyright (c) 2026 tro Contributors\n# SPDX-License-Identifier: MIT\nprint(1)\n"
        self.assertFalse(
            add_license_headers.has_license_header(legacy_py, ".py"),
            "Legacy brand without trailing dot ('tro Contributors') must be rejected",
        )
        legacy_js = "/*\n * Copyright (c) 2026 tro Contributors\n * SPDX-License-Identifier: MIT\n */\n"
        self.assertFalse(
            add_license_headers.has_license_header(legacy_js, ".js"),
            "Legacy brand without trailing dot in JS comment must be rejected",
        )

        # Safe compatibility regex: variations of valid tro. Contributors headers
        valid_variants = [
            "# Copyright (c) 2025-2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n",
            "# Copyright (c) 2026–2027 tro. Contributors\n# SPDX-License-Identifier: MIT\n",
            "# Copyright (c) 2025—2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n",
            "# Copyright © 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n",
            "# Copyright 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\n",
            "# Copyright (c) tro. Contributors\n# SPDX-License-Identifier: MIT\n",
        ]
        for variant in valid_variants:
            self.assertTrue(
                add_license_headers.has_license_header(variant, ".py"),
                f"Valid copyright variant must be accepted: {variant.strip()}",
            )

    def test_add_header_to_python_file(self):
        original = "def solve():\n    return 42\n"
        updated = add_license_headers.add_header_to_content(original, ".py")
        self.assertTrue(add_license_headers.has_license_header(updated))
        self.assertIn("def solve():", updated)
        # Idempotency
        updated_again = add_license_headers.add_header_to_content(updated, ".py")
        self.assertEqual(updated, updated_again)

    def test_add_header_to_js_file(self):
        original = "export function main() {\n  return 0;\n}\n"
        updated = add_license_headers.add_header_to_content(original, ".js")
        self.assertTrue(add_license_headers.has_license_header(updated))
        self.assertTrue(updated.startswith("/*\n * Copyright (c) 2026 tro. Contributors"))
        # Idempotency
        self.assertEqual(updated, add_license_headers.add_header_to_content(updated, ".js"))

    def test_add_header_to_jsx_ts_tsx_css_files(self):
        for ext in [".jsx", ".ts", ".tsx", ".css"]:
            original = "/* content */\n"
            updated = add_license_headers.add_header_to_content(original, ext)
            self.assertTrue(add_license_headers.has_license_header(updated, ext))
            self.assertTrue(updated.startswith("/*\n * Copyright (c) 2026 tro. Contributors"))

    def test_add_header_preserves_shebang(self):
        original = "#!/usr/bin/env bash\necho 'hello world'\n"
        updated = add_license_headers.add_header_to_content(original, ".sh")
        self.assertTrue(updated.startswith("#!/usr/bin/env bash\n"))
        self.assertTrue(add_license_headers.has_license_header(updated))
        self.assertIn("echo 'hello world'", updated)

    def test_add_header_preserves_shebang_with_flags(self):
        original = "#!/bin/bash -euo pipefail\necho 'safe bash'\n"
        updated = add_license_headers.add_header_to_content(original, ".sh")
        self.assertTrue(updated.startswith("#!/bin/bash -euo pipefail\n"))
        self.assertTrue(add_license_headers.has_license_header(updated))

    def test_add_header_preserves_encoding_cookie(self):
        original = "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\nprint('ok')\n"
        updated = add_license_headers.add_header_to_content(original, ".py")
        self.assertTrue(updated.startswith("#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"))
        self.assertTrue(add_license_headers.has_license_header(updated))

    def test_add_header_preserves_encoding_cookie_without_shebang(self):
        original = "# -*- coding: utf-8 -*-\nx = 1\n"
        updated = add_license_headers.add_header_to_content(original, ".py")
        self.assertTrue(updated.startswith("# -*- coding: utf-8 -*-\n"))
        self.assertTrue(add_license_headers.has_license_header(updated))

    def test_add_header_does_not_treat_code_assignment_as_encoding_cookie(self):
        """Code containing 'coding:' or 'coding=' without leading '#' must not be treated as encoding cookie."""
        original = 'transcoding_mode = "fast"\nx = 1\n'
        updated = add_license_headers.add_header_to_content(original, ".py")
        # Header must be at the very top, before transcoding_mode
        self.assertTrue(updated.startswith("# Copyright (c) 2026 tro. Contributors"))
        self.assertIn('transcoding_mode = "fast"', updated)
        self.assertTrue(add_license_headers.has_license_header(updated, ".py"))

    def test_direct_bom_handling_in_library_functions(self):
        """has_license_header and add_header_to_content must transparently handle UTF-8 BOM."""
        # Content with BOM and no header
        raw = "\ufeffx = 1\n"
        self.assertFalse(add_license_headers.has_license_header(raw, ".py"))
        updated = add_license_headers.add_header_to_content(raw, ".py")
        self.assertTrue(updated.startswith("\ufeff# Copyright (c) 2026 tro. Contributors"))
        self.assertTrue(add_license_headers.has_license_header(updated, ".py"))
        # Idempotency with BOM
        self.assertEqual(updated, add_license_headers.add_header_to_content(updated, ".py"))

    def test_add_header_to_empty_file(self):
        updated = add_license_headers.add_header_to_content("", ".py")
        self.assertTrue(add_license_headers.has_license_header(updated))
        self.assertTrue(updated.endswith("\n"))

    def test_add_header_to_whitespace_file(self):
        updated = add_license_headers.add_header_to_content("   \n\n\t  ", ".py")
        self.assertTrue(add_license_headers.has_license_header(updated))
        self.assertTrue(updated.endswith("\n"))

    def test_add_header_crlf_line_endings(self):
        original = "def solve():\r\n    return 42\r\n"
        updated = add_license_headers.add_header_to_content(original, ".py")
        self.assertIn("\r\n", updated)
        self.assertTrue(add_license_headers.has_license_header(updated))

    def test_utf8_bom_handling(self):
        bom_file = self.temp_path / "bom.py"
        bom_file.write_bytes("\ufeffx = 1\n".encode("utf-8"))

        # Run script in insertion mode
        code = add_license_headers.main([str(bom_file)])
        self.assertEqual(code, 0)

        # File content must have preserved BOM and added header
        new_content = bom_file.read_bytes().decode("utf-8")
        self.assertTrue(new_content.startswith("\ufeff# Copyright (c) 2026 tro. Contributors"))

    def test_non_utf8_surrogate_escape_handling(self):
        # File with legacy Windows-1252 byte (0xE9 = e acute)
        legacy_file = self.temp_path / "legacy.py"
        legacy_bytes = b"# Comment with legacy char: \xe9\nx = 1\n"
        legacy_file.write_bytes(legacy_bytes)

        # In check mode, should report missing header without crash
        code = add_license_headers.main(["--check", str(legacy_file)])
        self.assertEqual(code, 1)

        # In write mode, should add header and preserve the legacy byte
        code = add_license_headers.main([str(legacy_file)])
        self.assertEqual(code, 0)

        updated_bytes = legacy_file.read_bytes()
        self.assertIn(b"\xe9", updated_bytes, "Legacy byte must be preserved losslessly")
        self.assertIn(b"# Copyright (c) 2026 tro. Contributors", updated_bytes)

    def test_find_source_files_ignores_specified_dirs(self):
        ignored_names = [".git", "node_modules", ".venv", "dist", "__pycache__", "document"]
        for ign in ignored_names:
            ign_dir = self.temp_path / ign
            ign_dir.mkdir(parents=True, exist_ok=True)
            (ign_dir / "bad.py").write_text("print('bad')", encoding="utf-8")
            (ign_dir / "bad.js").write_text("console.log('bad');", encoding="utf-8")

        valid_dir = self.temp_path / "valid_src"
        valid_dir.mkdir(parents=True, exist_ok=True)
        py_file = valid_dir / "app.py"
        jsx_file = valid_dir / "view.jsx"
        ts_file = valid_dir / "index.ts"
        tsx_file = valid_dir / "component.tsx"
        css_file = valid_dir / "style.css"
        sh_file = valid_dir / "run.sh"
        txt_file = valid_dir / "notes.txt"

        for f in [py_file, jsx_file, ts_file, tsx_file, css_file, sh_file]:
            f.write_text("/* dummy */", encoding="utf-8")
        txt_file.write_text("text file", encoding="utf-8")

        found = add_license_headers.find_source_files([self.temp_path], base_root=self.temp_path)
        found_names = [f.name for f in found]

        self.assertIn("app.py", found_names)
        self.assertIn("view.jsx", found_names)
        self.assertIn("index.ts", found_names)
        self.assertIn("component.tsx", found_names)
        self.assertIn("style.css", found_names)
        self.assertIn("run.sh", found_names)
        self.assertNotIn("notes.txt", found_names)
        self.assertNotIn("bad.py", found_names)
        self.assertNotIn("bad.js", found_names)

    def test_workspace_inside_ignored_name_ancestor(self):
        """Adversarial test: repository cloned inside a path containing an ignored folder name."""
        project_in_doc = self.temp_path / "document" / "my_project"
        project_in_doc.mkdir(parents=True, exist_ok=True)
        src_file = project_in_doc / "core.py"
        src_file.write_text("print('core')", encoding="utf-8")

        # Nested ignored dir inside the project
        nested_doc = project_in_doc / "document"
        nested_doc.mkdir(parents=True, exist_ok=True)
        ignored_file = nested_doc / "ignored.py"
        ignored_file.write_text("print('ignored')", encoding="utf-8")

        found = add_license_headers.find_source_files([project_in_doc], base_root=project_in_doc)
        found_paths = [str(f.resolve()) for f in found]

        self.assertIn(str(src_file.resolve()), found_paths)
        self.assertNotIn(str(ignored_file.resolve()), found_paths)

    def test_external_path_under_ignored_ancestor_name(self):
        """Even without base_root passed, targets outside repo_root under ignored-named ancestor work."""
        external_proj = self.temp_path / "document" / "external_repo"
        external_proj.mkdir(parents=True, exist_ok=True)
        test_file = external_proj / "app.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        # Notice we do NOT pass base_root, testing default resolution for external target
        found = add_license_headers.find_source_files([external_proj])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].resolve(), test_file.resolve())

    def test_explicitly_passed_ignored_dir_is_ignored(self):
        """Adversarial test: passing an ignored directory directly as an argument."""
        ignored_dir = self.temp_path / "document"
        ignored_dir.mkdir(parents=True, exist_ok=True)
        file_in_ignored = ignored_dir / "test.py"
        file_in_ignored.write_text("print('test')", encoding="utf-8")

        found = add_license_headers.find_source_files([ignored_dir], base_root=self.temp_path)
        self.assertEqual(len(found), 0, "Explicitly targeted ignored directory must yield 0 files")

    def test_cli_nonexistent_path_returns_error(self):
        nonexistent = self.temp_path / "does_not_exist.py"
        code = add_license_headers.main([str(nonexistent)])
        self.assertEqual(code, 1, "Passing nonexistent path must return exit code 1")

    def test_cli_check_flag_failure_and_success(self):
        sample_file = self.temp_path / "sample.py"
        sample_file.write_text("x = 1\n", encoding="utf-8")

        # In check mode, missing header must return exit code 1
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = stdout_capture, stderr_capture
            code = add_license_headers.main(["--check", str(self.temp_path)])
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

        self.assertEqual(code, 1, "--check must exit with 1 when header is missing")
        output = stdout_capture.getvalue()
        self.assertIn("Missing license header", output)
        self.assertIn("sample.py", output)

        # In write mode, should add header and exit with 0
        stdout_capture = io.StringIO()
        try:
            sys.stdout = stdout_capture
            code = add_license_headers.main([str(self.temp_path)])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0, "write mode must exit with 0")
        self.assertIn("Added license header", stdout_capture.getvalue())

        # Now in check mode, should pass with exit code 0
        stdout_capture = io.StringIO()
        try:
            sys.stdout = stdout_capture
            code = add_license_headers.main(["--check", str(self.temp_path)])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0, "--check must exit with 0 when all headers are valid")
        self.assertIn("Check passed", stdout_capture.getvalue())

    def test_repo_wide_check_passes(self):
        """Verify that running --check across the actual repository returns exit code 0."""
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout_capture
            exit_code = add_license_headers.main(["--check"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(
            exit_code,
            0,
            f"--check on repository failed! Output:\n{stdout_capture.getvalue()}",
        )

    def test_external_ignored_dir_without_base_root_is_ignored(self):
        """Passing an external ignored dir without base_root must still be ignored."""
        ignored_dir = self.temp_path / "document"
        ignored_dir.mkdir(parents=True, exist_ok=True)
        file_in_ignored = ignored_dir / "test.py"
        file_in_ignored.write_text("print('test')", encoding="utf-8")

        found = add_license_headers.find_source_files([ignored_dir])
        self.assertEqual(
            len(found),
            0,
            "External ignored directory without base_root must yield 0 files",
        )

    def test_code_on_same_line_after_closing_comment_rejected(self):
        """Executable code on the same line after */ must cause rejection."""
        bad_code = (
            "/* Copyright (c) 2026 tro. Contributors */ console.log('bad');\n"
            "/* SPDX-License-Identifier: MIT */\n"
        )
        self.assertFalse(
            add_license_headers.has_license_header(bad_code, ".js"),
            "Code following comment closure on same line must be rejected",
        )

    def test_multiline_block_comment_with_code_on_closing_line_rejected(self):
        """Executable code on the same line after multi-line */ must cause rejection."""
        bad_code = (
            "/*\n"
            " * Copyright (c) 2026 tro. Contributors\n"
            " * SPDX-License-Identifier: MIT\n"
            " */ console.log('bad');\n"
        )
        self.assertFalse(
            add_license_headers.has_license_header(bad_code, ".js"),
            "Code following multi-line block comment closure on same line must be rejected",
        )

    def test_unclosed_block_comment_rejected(self):
        """Unclosed block comment must not be accepted as a valid license header."""
        unclosed_code = (
            "/*\n"
            " * Copyright (c) 2026 tro. Contributors\n"
            " * SPDX-License-Identifier: MIT\n"
            "console.log('code');\n"
        )
        self.assertFalse(
            add_license_headers.has_license_header(unclosed_code, ".js"),
            "Unclosed block comment must be rejected",
        )

    def test_single_line_both_tokens_with_trailing_code_rejected(self):
        """Single-line block comment with both tokens followed by code must be rejected."""
        bad_code = "/* Copyright (c) 2026 tro. Contributors - SPDX-License-Identifier: MIT */ console.log(1);\n"
        self.assertFalse(
            add_license_headers.has_license_header(bad_code, ".js"),
            "Single-line block comment with trailing code must be rejected",
        )

    def test_extension_handling_without_leading_dot(self):
        """Extension parameters without leading dot must be accepted."""
        py_h = add_license_headers.get_license_header("py")
        self.assertIn("Copyright", py_h)
        js_h = add_license_headers.get_license_header("js")
        self.assertIn("Copyright", js_h)
        py_code = "# Copyright (c) 2026 tro. Contributors\n# SPDX-License-Identifier: MIT\nx = 1\n"
        self.assertTrue(add_license_headers.has_license_header(py_code, "py"))
        updated = add_license_headers.add_header_to_content("x = 1\n", "py")
        self.assertTrue(add_license_headers.has_license_header(updated, "py"))

    def test_js_with_shebang_preserved(self):
        """Node.js shebang in JS file must be preserved."""
        original = "#!/usr/bin/env node\nconsole.log('hi');\n"
        updated = add_license_headers.add_header_to_content(original, ".js")
        self.assertTrue(updated.startswith("#!/usr/bin/env node\n"))
        self.assertTrue(add_license_headers.has_license_header(updated, ".js"))


if __name__ == "__main__":
    unittest.main()
