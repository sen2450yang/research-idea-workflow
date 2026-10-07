#!/usr/bin/env python3
"""Exercise bundled file tooling in a temporary test directory.

Python 3.10+, standard library only. These tests do not run a model, literature
search, scientific analysis, local installation, or external API calls.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from init_project import initialize, main, prepare_files, MODES, EXPECTED_TEMPLATES
from validate_skill import validate

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "assets" / "templates"


class ToolingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="research-skill-test-")
        self.parent = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_project_creates_all_templates(self):
        target = self.parent / "new-study"
        paths = initialize(target, "研究问题")
        self.assertEqual({p.name for p in paths}, set(EXPECTED_TEMPLATES))
        self.assertTrue(all(p.is_file() for p in paths))
        state = json.loads((target / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["project_title"], "研究问题")
        self.assertTrue(all(s["status"] == "not_started" for s in state["stages"]))
        for p in paths:
            self.assertNotIn("{{PROJECT_TITLE}}", p.read_text(encoding="utf-8"))
            self.assertNotIn("{{CREATED_AT}}", p.read_text(encoding="utf-8"))

    def test_existing_directory_is_not_modified(self):
        target = self.parent / "existing"
        target.mkdir()
        marker = target / "keep.txt"
        marker.write_text("original", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            initialize(target, "研究问题")
        self.assertEqual(marker.read_text(encoding="utf-8"), "original")
        self.assertEqual(list(target.iterdir()), [marker])

    def test_existing_file_is_not_overwritten(self):
        target = self.parent / "existing.txt"
        target.write_text("original", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            initialize(target, "研究问题")
        self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_dry_run_writes_nothing(self):
        target = self.parent / "dry-run"
        planned = initialize(target, "研究问题", dry_run=True)
        self.assertEqual(len(planned), len(EXPECTED_TEMPLATES))
        self.assertFalse(target.exists())
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_missing_parent_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            initialize(self.parent / "missing" / "child", "研究问题")
        self.assertFalse((self.parent / "missing").exists())

    def test_json_handles_quotes_unicode_and_backslash(self):
        title = '题目 "A" 与 B \\ C'
        target = self.parent / "中文 空格"
        initialize(target, title)
        state = json.loads((target / "project-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["project_title"], title)

    def test_mode_marks_only_suggested_scope(self):
        for mode in MODES:
            files = prepare_files(TEMPLATES, "研究问题", mode)
            state = json.loads(files["project-state.json"])
            self.assertEqual(state["mode"], mode)
            self.assertTrue(all(s["status"] in {"not_started", "out_of_scope"} for s in state["stages"]))
        data = json.loads(prepare_files(TEMPLATES, "研究问题", "novelty")["project-state.json"])
        in_scope = {s["id"] for s in data["stages"] if s["status"] == "not_started"}
        self.assertEqual(in_scope, {1, 3, 6})

    def test_invalid_title_or_mode_is_rejected(self):
        for title in ("", "   ", "A\nB", "A\rB", "A\x00B"):
            with self.assertRaises(ValueError):
                prepare_files(TEMPLATES, title, "full")
        with self.assertRaises(ValueError):
            prepare_files(TEMPLATES, "title", "unknown")

    def test_missing_template_fails_before_writing(self):
        target = self.parent / "new-study"
        with self.assertRaises(FileNotFoundError):
            initialize(target, "研究问题", template_dir=self.parent)
        self.assertFalse(target.exists())

    def test_symlink_target_is_rejected(self):
        link = self.parent / "alias"
        try:
            link.symlink_to(self.parent / "absent", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("This OS does not permit test symlinks")
        with self.assertRaises(FileExistsError):
            initialize(link, "研究问题")

    def test_cli_error_returns_nonzero(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["--destination", str(self.parent), "--title", "研究问题"])
        self.assertEqual(code, 2)

    def test_bundle_static_validation(self):
        result = validate(ROOT)
        self.assertTrue(result["ok"], result["errors"])

    def test_missing_reference_is_detected(self):
        copied = self.parent / ROOT.name
        shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns("__pycache__"))
        (copied / "references" / "stages-05-08.md").unlink()
        result = validate(copied)
        self.assertFalse(result["ok"])
        self.assertTrue(any("stages-05-08.md" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
