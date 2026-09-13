import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/package_release.py'
SPEC = importlib.util.spec_from_file_location('packager', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageReleaseTests(unittest.TestCase):
    def test_committed_payload_checksums_and_dirty_tree_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / MODULE.SKILL_PREFIX
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('portable rules', encoding='utf-8')
            (root / 'VERSION').write_text('0.1.1\n', encoding='utf-8')
            (root / 'LICENSE').write_text('test license', encoding='utf-8')
            (root / '.gitignore').write_text('dist/\n', encoding='utf-8')
            def git(*args):
                return subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                       '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=.no-hooks', *args],
                                      cwd=root, check=True, capture_output=True)
            git('init')
            git('add', '.')
            git('commit', '-m', 'test(package): create fixture')
            with patch.object(MODULE, 'ROOT', root):
                MODULE.main()
                checksums = root / f'dist/{MODULE.NAME}-0.1.1-SHA256SUMS.txt'
                for line in checksums.read_text().splitlines():
                    digest, filename = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256((root / 'dist' / filename).read_bytes()).hexdigest(), digest)
                with zipfile.ZipFile(root / f'dist/{MODULE.NAME}-0.1.1.zip') as archive:
                    self.assertEqual(set(archive.namelist()), {f'{MODULE.NAME}/SKILL.md', f'{MODULE.NAME}/LICENSE'})
                    self.assertEqual(archive.read(f'{MODULE.NAME}/SKILL.md'), b'portable rules')
                (source / 'SKILL.md').write_text('uncommitted rules', encoding='utf-8')
                with self.assertRaisesRegex(SystemExit, 'commit all source changes'):
                    MODULE.main()
