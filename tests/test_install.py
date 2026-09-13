from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("installer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstallTests(unittest.TestCase):
    def test_destination_mapping(self) -> None:
        project = Path("C:/project")
        self.assertEqual(
            MODULE.destination("generic", "project", project),
            project / ".agents" / "skills" / MODULE.SKILL_NAME,
        )
        self.assertEqual(
            MODULE.destination("claude", "project", project),
            project / ".claude" / "skills" / MODULE.SKILL_NAME,
        )

    def test_install_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skill"
            self.assertEqual(MODULE.install(target, apply=False, force=False), 0)
            self.assertFalse(target.exists())

    def test_install_and_uninstall_require_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skill"
            self.assertEqual(MODULE.install(target, apply=True, force=False), 0)
            self.assertTrue((target / MODULE.MARKER).exists())
            self.assertEqual(MODULE.uninstall(target, apply=False), 0)
            self.assertTrue(target.exists())
            self.assertEqual(MODULE.uninstall(target, apply=True), 0)
            self.assertFalse(target.exists())

    def test_unmanaged_target_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skill"
            target.mkdir()
            (target / "user-file.txt").write_text("keep", encoding="utf-8")
            self.assertEqual(MODULE.install(target, apply=True, force=False), 1)
            self.assertEqual((target / "user-file.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
