from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_skill.py"
SPEC = importlib.util.spec_from_file_location("sync_skill", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SyncSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("new skill\n", encoding="utf-8")
        (self.source / "scripts").mkdir()
        (self.source / "scripts" / "validate.py").write_text("new validator\n", encoding="utf-8")
        self.target = self.root / "copies" / "skill"
        self.output = io.StringIO()
        self.error = io.StringIO()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(MODULE, "SOURCE", self.source))
        stack.enter_context(mock.patch.object(MODULE, "TARGET", self.target))
        stack.enter_context(mock.patch.object(MODULE, "ROOT", self.root))
        stack.enter_context(contextlib.redirect_stdout(self.output))
        stack.enter_context(contextlib.redirect_stderr(self.error))

    def create_target(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "SKILL.md").write_text("old skill\n", encoding="utf-8")
        (self.target / "obsolete.txt").write_text("old payload\n", encoding="utf-8")

    @staticmethod
    def tree(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()
        }

    def test_both_missing_cannot_pass_check(self) -> None:
        shutil.rmtree(self.source)
        self.assertEqual(MODULE.synchronize(check=True), 1)
        self.assertFalse(self.target.parent.exists())
        self.assertNotIn("OK:", self.output.getvalue())

    def test_missing_source_preserves_existing_target(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        shutil.rmtree(self.source)
        for check in (True, False):
            with self.subTest(check=check):
                self.assertEqual(MODULE.synchronize(check=check), 1)
                self.assertEqual(self.tree(self.target), before)
                self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_missing_skill_entrypoint_cannot_replace_target(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        (self.source / "SKILL.md").unlink()
        for check in (True, False):
            with self.subTest(check=check):
                self.assertEqual(MODULE.synchronize(check=check), 1)
                self.assertEqual(self.tree(self.target), before)
        self.assertIn("missing SKILL.md", self.error.getvalue())

    def test_check_detects_missing_and_mismatched_target_without_writing(self) -> None:
        self.assertEqual(MODULE.synchronize(check=True), 1)
        self.assertFalse(self.target.parent.exists())
        self.create_target()
        before = self.tree(self.target)
        self.assertEqual(MODULE.synchronize(check=True), 1)
        self.assertEqual(self.tree(self.target), before)

    def test_success_replaces_stale_files_and_ignores_caches(self) -> None:
        self.create_target()
        (self.source / "__pycache__").mkdir()
        (self.source / "__pycache__" / "cache.pyc").write_bytes(b"cache")
        self.assertEqual(MODULE.synchronize(), 0)
        self.assertEqual(self.tree(self.target), {
            "SKILL.md": (self.source / "SKILL.md").read_bytes(),
            "scripts/validate.py": (self.source / "scripts" / "validate.py").read_bytes(),
        })
        self.assertEqual(MODULE.synchronize(check=True), 0)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_success_creates_missing_target_and_repairs_missing_entrypoint(self) -> None:
        self.assertEqual(MODULE.synchronize(), 0)
        (self.target / "SKILL.md").unlink()
        self.assertEqual(MODULE.synchronize(check=True), 1)
        self.assertEqual(MODULE.synchronize(), 0)
        self.assertEqual(MODULE.synchronize(check=True), 0)

    def test_file_target_is_preserved(self) -> None:
        self.target.parent.mkdir()
        self.target.write_bytes(b"existing user file")
        self.assertEqual(MODULE.synchronize(), 1)
        self.assertEqual(self.target.read_bytes(), b"existing user file")
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_copy_failure_preserves_existing_target_and_cleans_staging(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        with mock.patch.object(MODULE.shutil, "copytree", side_effect=OSError("copy failed")):
            self.assertEqual(MODULE.synchronize(), 1)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_replacement_failure_restores_previous_target(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        rename = Path.rename

        def fail_replacement(path: Path, destination: Path) -> Path:
            if path.name == "new":
                raise OSError("replacement failed")
            return rename(path, destination)

        with mock.patch.object(Path, "rename", fail_replacement):
            self.assertEqual(MODULE.synchronize(), 1)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_failed_restore_retains_and_reports_recovery_backup(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        rename = Path.rename

        def fail_replacement_and_restore(path: Path, destination: Path) -> Path:
            if path.name in {"new", "previous"}:
                raise OSError("rename failed")
            return rename(path, destination)

        with mock.patch.object(Path, "rename", fail_replacement_and_restore):
            self.assertEqual(MODULE.synchronize(), 1)
        self.assertFalse(self.target.exists())
        backups = list(self.target.parent.glob(".skill-sync-*/previous"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.tree(backups[0]), before)
        self.assertIn(str(backups[0].resolve()), self.error.getvalue())

    def test_cleanup_failure_reports_retained_directory(self) -> None:
        self.create_target()
        before = self.tree(self.target)
        with mock.patch.object(MODULE.shutil, "rmtree", side_effect=PermissionError("cleanup denied")):
            self.assertEqual(MODULE.synchronize(), 1)
        self.assertEqual(self.tree(self.target), self.tree(self.source))
        backups = list(self.target.parent.glob(".skill-sync-*/previous"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.tree(backups[0]), before)
        self.assertIn(str(backups[0].parent.resolve()), self.error.getvalue())

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_junction_target_cannot_touch_referent(self) -> None:
        referent = self.root / "referent"
        referent.mkdir()
        (referent / "SKILL.md").write_text("external skill\n", encoding="utf-8")
        self.target.parent.mkdir()
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.target), str(referent)],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(self.target.rmdir)
        before = self.tree(referent)
        self.assertEqual(MODULE.synchronize(), 1)
        self.assertEqual(self.tree(referent), before)


if __name__ == "__main__":
    unittest.main()
