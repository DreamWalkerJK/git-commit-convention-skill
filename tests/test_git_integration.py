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
    def test_file_and_stdin_preserve_subject_line_endings(self):
        subject = 'fix(认证): 修复令牌过期'.encode('utf-8')
        cases = [
            (subject, 0),
            (subject + b'\n\nDetails', 0),
            (subject + b'\r\n\r\nDetails', 0),
            (subject + b'\r', 1),
            (subject + b'\r\r\n', 1),
            (subject + b'\rhidden', 1),
            (subject + b'\r' + b'x' * 80, 1),
            (b'\xff', 2),
        ]
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory) / 'message.txt'
            for payload, expected in cases:
                with self.subTest(payload=payload):
                    message.write_bytes(payload)
                    results = [
                        subprocess.run([sys.executable, str(VALIDATOR)], input=payload, capture_output=True),
                        subprocess.run([sys.executable, str(VALIDATOR), str(message)], capture_output=True),
                    ]
                    for result in results:
                        self.assertEqual(result.returncode, expected, result.stderr)
                        self.assertNotIn(b'Traceback', result.stderr)
                    self.assertEqual(results[0].stdout, results[1].stdout)
                    self.assertEqual(results[0].stderr, results[1].stderr)

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
            message = repo / 'message.txt'
            message.write_bytes(b'fix(api): valid\r' + b'x' * 80 + b'\n')
            invalid = git('commit', '--allow-empty', '--cleanup=verbatim', '--file', str(message))
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn('maximum is 72', invalid.stderr)
            self.assertEqual(git('rev-parse', 'HEAD').stdout, head)
            message.write_bytes('fix(认证): 修复令牌过期\r\n\r\nDetails\r\n'.encode('utf-8'))
            valid = git('commit', '--allow-empty', '--cleanup=verbatim', '--file', str(message))
            self.assertEqual(valid.returncode, 0, valid.stderr)
            range_cli = ROOT / 'scripts/validate_commit_range.py'
            result = subprocess.run([sys.executable, str(range_cli), 'HEAD'], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            bypassed = git('commit', '--allow-empty', '--no-verify', '-m', 'invalid historical message')
            self.assertEqual(bypassed.returncode, 0, bypassed.stderr)
            result = subprocess.run([sys.executable, str(range_cli), 'HEAD~1..HEAD'], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_raw_git_history_preserves_carriage_returns(self):
        with tempfile.TemporaryDirectory(prefix='commit history ') as directory:
            repo = Path(directory)
            env = os.environ.copy()

            def git(*args, data=None):
                return subprocess.run([
                    'git', '-c', 'user.name=Skill Test', '-c', 'user.email=skill@example.invalid',
                    '-c', 'commit.gpgsign=false', *args,
                ], cwd=repo, env=env, input=data, capture_output=True, check=True).stdout

            git('init')
            tree = git('hash-object', '-t', 'tree', '-w', '--stdin', data=b'').strip().decode('ascii')
            subject = 'fix(认证): 修复令牌过期'.encode('utf-8')
            for payload, expected in [
                (subject + b'\n\nDetails\n', 0),
                (subject + b'\r\n\r\nDetails\r\n', 0),
                (subject + b'\r' + b'x' * 80 + b'\n', 1),
                (subject + b'\rhidden\n', 1),
            ]:
                with self.subTest(payload=payload):
                    commit = git('commit-tree', tree, data=payload).strip().decode('ascii')
                    result = subprocess.run([
                        sys.executable, str(ROOT / 'scripts/validate_commit_range.py'), commit,
                    ], cwd=repo, capture_output=True)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)

    def test_unterminated_and_invalid_utf8_history(self):
        with tempfile.TemporaryDirectory(prefix='raw commit history ') as directory:
            repo = Path(directory)

            def git(*args, data=None):
                return subprocess.run([
                    'git', *args,
                ], cwd=repo, input=data, capture_output=True, check=True).stdout

            git('init')
            tree = git('hash-object', '-t', 'tree', '-w', '--stdin', data=b'').strip()
            headers = (
                b'tree ' + tree + b'\n'
                b'author Skill Test <skill@example.invalid> 1700000000 +0000\n'
                b'committer Skill Test <skill@example.invalid> 1700000000 +0000\n\n'
            )
            # Writing raw objects avoids commit-tree normalizing the final LF
            # or recoding the malformed UTF-8 before the range checker sees it.
            for payload, expected in [
                (b'fix(api): valid', 0),
                (b'fix(api): valid\r', 1),
                (b'fix(api): invalid \xff\n', 2),
            ]:
                with self.subTest(payload=payload):
                    commit = git('hash-object', '-t', 'commit', '-w', '--stdin', data=headers + payload).strip().decode('ascii')
                    result = subprocess.run([
                        sys.executable, str(ROOT / 'scripts/validate_commit_range.py'), commit,
                    ], cwd=repo, capture_output=True)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)
                    if expected == 2:
                        self.assertIn(b'ERROR: cannot read commit', result.stderr)
