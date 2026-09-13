"""Exercise Git and the shipped CLI with real messages and isolated repos."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path('.agents/skills/git-commit-convention-skill')
VALIDATOR = ROOT / SKILL / 'scripts/validate_commit_message.py'


class GitIntegrationTests(unittest.TestCase):
    def test_utf8_stdin_file_and_bad_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory) / 'message.txt'
            payload = 'fix(认证): 修复令牌过期\r\n\r\n详细说明\r\n'.encode('utf-8')
            message.write_bytes(payload)
            for args, data in [([], payload), ([str(message)], None)]:
                result = subprocess.run([sys.executable, str(VALIDATOR), *args], input=data, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            message.write_bytes(b'\xff')
            result = subprocess.run([sys.executable, str(VALIDATOR), str(message)], capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)

    def test_unicode_line_separator_cannot_hide_long_title(self):
        for separator in ['\u2028', '\u2029', '\x00', '\t', '\x0b']:
            with self.subTest(separator=repr(separator)):
                payload = ('fix(api): valid' + separator + 'x' * 72).encode('utf-8')
                result = subprocess.run([sys.executable, str(VALIDATOR)], input=payload, capture_output=True)
                self.assertEqual(result.returncode, 1, result.stderr)

    def test_real_git_hook_and_history(self):
        with tempfile.TemporaryDirectory(prefix='commit skill ') as directory:
            repo = Path(directory)
            shutil.copytree(ROOT / SKILL, repo / SKILL, ignore=shutil.ignore_patterns('__pycache__'))
            (repo / '.githooks').mkdir()
            hook = repo / '.githooks/commit-msg'
            shutil.copyfile(ROOT / '.githooks/commit-msg', hook)
            hook.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
            # Keep tests independent of developer identity/signing configuration.
            def git(*args):
                return subprocess.run([
                    'git', '-c', 'user.name=Skill Test', '-c', 'user.email=skill@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=.githooks', *args,
                ], cwd=repo, env=env, encoding='utf-8', capture_output=True)

            self.assertEqual(git('init').returncode, 0)
            valid = git('commit', '--allow-empty', '-m', 'fix(认证): 修复令牌过期')
            self.assertEqual(valid.returncode, 0, valid.stderr)
            head = git('rev-parse', 'HEAD').stdout
            invalid = git('commit', '--allow-empty', '-m', 'bad message')
            self.assertNotEqual(invalid.returncode, 0)
            self.assertEqual(git('rev-parse', 'HEAD').stdout, head)
            range_cli = ROOT / 'scripts/validate_commit_range.py'
            result = subprocess.run([sys.executable, str(range_cli), 'HEAD'], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            bypassed = git('commit', '--allow-empty', '--no-verify', '-m', 'invalid historical message')
            self.assertEqual(bypassed.returncode, 0, bypassed.stderr)
            result = subprocess.run([sys.executable, str(range_cli), 'HEAD~1..HEAD'], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)
