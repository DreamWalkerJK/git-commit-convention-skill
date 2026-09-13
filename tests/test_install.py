from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("installer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("original skill\n", encoding="utf-8")
        (self.source / "scripts").mkdir()
        (self.source / "scripts" / "validate.py").write_text("print('original')\n", encoding="utf-8")
        self.target = self.root / "installed" / MODULE.SKILL_NAME
        patcher = mock.patch.object(MODULE, "SOURCE", self.source)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.output = io.StringIO()
        self.error = io.StringIO()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(contextlib.redirect_stdout(self.output))
        stack.enter_context(contextlib.redirect_stderr(self.error))

    @staticmethod
    def tree(root: Path) -> dict:
        return {
            path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")
        }

    def create_install(self, target: Path | None = None) -> Path:
        target = target or self.target
        self.assertEqual(MODULE.install(target, apply=True, force=False), 0)
        return target

    def backups(self) -> list[Path]:
        backup_root = self.target.parent.parent / f".{MODULE.SKILL_NAME}-backups"
        return list(backup_root.iterdir()) if backup_root.exists() else []

    def write_legacy_marker(self, target: Path) -> None:
        MODULE.marker_path(target).write_text(json.dumps({"tool": MODULE.SKILL_NAME, "format": 1}), encoding="utf-8")

    def test_destination_mapping(self) -> None:
        project = Path("project")
        for agent in ("generic", "codex"):
            self.assertEqual(MODULE.destination(agent, "project", project), project / ".agents" / "skills" / MODULE.SKILL_NAME)
        self.assertEqual(MODULE.destination("claude", "project", project), project / ".claude" / "skills" / MODULE.SKILL_NAME)
        self.assertEqual(MODULE.destination("generic", "user", project), Path.home() / ".agents" / "skills" / MODULE.SKILL_NAME)
        self.assertEqual(MODULE.destination("claude", "user", project), Path.home() / ".claude" / "skills" / MODULE.SKILL_NAME)
        with mock.patch.object(MODULE, "codex_home", return_value=self.root / "custom-codex"):
            self.assertEqual(MODULE.destination("codex", "user", project), self.root / "custom-codex" / "skills" / MODULE.SKILL_NAME)

    def test_install_preview_does_not_write(self) -> None:
        self.assertEqual(MODULE.install(self.target, apply=False, force=False), 0)
        self.assertFalse(self.target.parent.exists())
        self.assertIn("Mode: preview", self.output.getvalue())

    def test_apply_reports_actual_mode_and_records_manifest(self) -> None:
        self.create_install()
        metadata = json.loads(MODULE.marker_path(self.target).read_text(encoding="utf-8"))
        self.assertEqual(metadata["format"], 2)
        self.assertEqual(metadata["files"], MODULE.inventory(self.source)["files"])
        self.assertIn("Mode: apply", self.output.getvalue())
        self.assertNotIn("Mode: preview", self.output.getvalue())

    def test_repeated_install_does_not_rewrite_files_or_create_backups(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        timestamps = {path: path.stat().st_mtime_ns for path in self.target.rglob("*")}
        self.assertEqual(MODULE.install(self.target, apply=True, force=True), 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in timestamps}, timestamps)
        self.assertEqual(self.backups(), [])
        self.assertIn("already installed", self.output.getvalue())

    def test_uninstall_preview_then_recoverable_removal(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        self.assertEqual(MODULE.uninstall(self.target, apply=False), 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(self.backups(), [])
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 0)
        self.assertFalse(self.target.exists())
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.tree(self.backups()[0]), before)
        self.assertIn(str(self.backups()[0].resolve()), self.output.getvalue())
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 0)
        self.assertEqual(len(self.backups()), 1)

    def test_unmanaged_target_is_preserved_even_with_force(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "user-file.txt").write_text("keep", encoding="utf-8")
        before = self.tree(self.target)
        for force in (False, True):
            self.assertEqual(MODULE.install(self.target, apply=True, force=force), 1)
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 1)
        self.assertEqual(self.tree(self.target), before)

    def test_invalid_markers_do_not_authorize_changes(self) -> None:
        markers = ["", "not json", "[]", "{}", '{"tool":"other","format":2}',
                   json.dumps({"tool": MODULE.SKILL_NAME, "format": 99}),
                   json.dumps({"tool": MODULE.SKILL_NAME, "format": True}),
                   json.dumps({"tool": MODULE.SKILL_NAME, "format": 2})]
        for index, marker in enumerate(markers):
            with self.subTest(marker=marker):
                target = self.create_install(self.root / f"bad-marker-{index}")
                MODULE.marker_path(target).write_text(marker, encoding="utf-8")
                before = self.tree(target)
                self.assertEqual(MODULE.install(target, apply=True, force=True), 1)
                self.assertEqual(MODULE.uninstall(target, apply=True), 1)
                self.assertEqual(MODULE.status(target), 1)
                self.assertEqual(self.tree(target), before)

    def test_edited_added_removed_files_and_empty_directories_are_preserved(self) -> None:
        for change in ("edit", "add", "remove", "empty-directory"):
            with self.subTest(change=change):
                target = self.create_install(self.root / change)
                if change == "edit":
                    (target / "SKILL.md").write_text("user edits", encoding="utf-8")
                elif change == "add":
                    (target / "personal-notes.txt").write_text("keep", encoding="utf-8")
                elif change == "remove":
                    (target / "scripts" / "validate.py").unlink()
                else:
                    (target / "personal-directory").mkdir()
                before = self.tree(target)
                self.assertEqual(MODULE.install(target, apply=True, force=True), 1)
                self.assertEqual(MODULE.uninstall(target, apply=True), 1)
                self.assertEqual(self.tree(target), before)

    def test_upgrade_preserves_previous_installation(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        (self.source / "SKILL.md").write_text("new release", encoding="utf-8")
        self.assertEqual(MODULE.install(self.target, apply=False), 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(self.backups(), [])
        self.assertEqual(MODULE.install(self.target, apply=True), 0)
        self.assertEqual((self.target / "SKILL.md").read_text(encoding="utf-8"), "new release")
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.tree(self.backups()[0]), before)
        self.assertIn(str(self.backups()[0].resolve()), self.output.getvalue())

    def test_failed_staging_leaves_existing_installation_untouched(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        (self.source / "SKILL.md").write_text("new release", encoding="utf-8")
        with mock.patch.object(MODULE.shutil, "copytree", side_effect=OSError("disk full")):
            self.assertEqual(MODULE.install(self.target, apply=True), 2)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_failed_replacement_restores_previous_installation(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        (self.source / "SKILL.md").write_text("new release", encoding="utf-8")
        original_rename = Path.rename

        def fail_staged(path: Path, destination: Path) -> Path:
            if "-stage-" in path.parent.name:
                raise OSError("replacement failed")
            return original_rename(path, destination)

        with mock.patch.object(Path, "rename", fail_staged):
            self.assertEqual(MODULE.install(self.target, apply=True), 2)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_failed_rollback_preserves_and_reports_recovery_backup(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        (self.source / "SKILL.md").write_text("new release", encoding="utf-8")
        original_rename = Path.rename

        def fail_publish_and_restore(path: Path, destination: Path) -> Path:
            if "-stage-" in path.parent.name or path.parent.name.endswith("-backups"):
                raise OSError("rename unavailable")
            return original_rename(path, destination)

        with mock.patch.object(Path, "rename", fail_publish_and_restore):
            self.assertEqual(MODULE.install(self.target, apply=True), 2)
        self.assertFalse(self.target.exists())
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.tree(self.backups()[0]), before)
        self.assertIn(str(self.backups()[0].resolve()), self.error.getvalue())

    def test_failed_uninstall_rename_preserves_installation(self) -> None:
        self.create_install()
        before = self.tree(self.target)
        with mock.patch.object(Path, "rename", side_effect=OSError("file locked")):
            self.assertEqual(MODULE.uninstall(self.target, apply=True), 2)
        self.assertEqual(self.tree(self.target), before)

    def test_legacy_installation_matching_current_source_migrates(self) -> None:
        self.create_install()
        self.write_legacy_marker(self.target)
        before = self.tree(self.target)
        self.assertEqual(MODULE.install(self.target, apply=True), 0)
        self.assertEqual(json.loads(MODULE.marker_path(self.target).read_text())["format"], 2)
        self.assertEqual(self.tree(self.backups()[0]), before)

    def test_legacy_marker_does_not_authorize_modified_content(self) -> None:
        self.create_install()
        self.write_legacy_marker(self.target)
        (self.target / "SKILL.md").write_text("unknown old content", encoding="utf-8")
        before = self.tree(self.target)
        self.assertEqual(MODULE.install(self.target, apply=True, force=True), 1)
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 1)
        self.assertEqual(self.tree(self.target), before)

    def test_original_v010_payload_can_migrate_with_lf_or_crlf(self) -> None:
        # Frozen original v0.1.0 payload: run migration checks in source archives
        # and shallow CI checkouts without needing Git, tags, or network access.
        encoded_release = (
            "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"
        )
        fixture = json.loads(zlib.decompress(base64.b64decode(encoded_release)))
        for ending in (b"\n", b"\r\n"):
            with self.subTest(ending=ending):
                target = self.root / "legacy-installs" / ("legacy-lf" if ending == b"\n" else "legacy-crlf")
                target.mkdir(parents=True)
                for name, content in fixture.items():
                    path = target / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content.encode("utf-8").replace(b"\r\n", b"\n").replace(b"\n", ending))
                self.write_legacy_marker(target)
                self.assertEqual(MODULE.install(target, apply=True), 0)
                self.assertEqual(json.loads(MODULE.marker_path(target).read_text())["format"], 2)

    def test_symlink_target_is_rejected_without_touching_referent(self) -> None:
        real = self.create_install(self.root / "real")
        self.target.parent.mkdir(parents=True)
        try:
            self.target.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("creating symlinks requires permission on this Windows installation")
        before = self.tree(real)
        self.assertEqual(MODULE.install(self.target, apply=True, force=True), 1)
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 1)
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(self.tree(real), before)

    @unittest.skipUnless(os.name == "nt", "junctions are Windows-specific")
    def test_junction_target_is_rejected_without_touching_referent(self) -> None:
        real = self.create_install(self.root / "real")
        self.target.parent.mkdir(parents=True)
        # Native PowerShell creates the test junction; no cross-shell deletion.
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        result = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 f"New-Item -ItemType Junction -Path {quote(self.target)} -Target {quote(real)} | Out-Null"],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.tree(real)
        self.assertEqual(MODULE.install(self.target, apply=True, force=True), 1)
        self.assertEqual(MODULE.uninstall(self.target, apply=True), 1)
        self.assertEqual(self.tree(real), before)
        # rmdir removes the junction itself, never traversing its destination.
        self.target.rmdir()


if __name__ == "__main__":
    unittest.main()
