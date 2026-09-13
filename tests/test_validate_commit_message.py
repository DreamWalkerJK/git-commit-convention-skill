from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "git-commit-convention-skill" / "scripts" / "validate_commit_message.py"
SPEC = importlib.util.spec_from_file_location("validate_commit_message", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateCommitMessageTests(unittest.TestCase):
    def test_all_allowed_types(self) -> None:
        for commit_type in MODULE.ALLOWED_TYPES:
            with self.subTest(commit_type=commit_type):
                self.assertEqual(MODULE.validate(f"{commit_type}(core): update"), [])

    def test_chinese_and_english_messages(self) -> None:
        self.assertEqual(MODULE.validate("feat(api): 添加分页查询"), [])
        self.assertEqual(MODULE.validate("fix(auth): handle token expiry"), [])
        self.assertEqual(MODULE.validate("docs(安装): 更新 README"), [])

    def test_exactly_72_characters_is_valid(self) -> None:
        prefix = "feat(api): "
        subject = prefix + "x" * (72 - len(prefix))
        self.assertEqual(len(subject), 72)
        self.assertEqual(MODULE.validate(subject), [])

    def test_73_characters_is_invalid(self) -> None:
        prefix = "feat(api): "
        subject = prefix + "x" * (73 - len(prefix))
        self.assertIn("maximum is 72", " ".join(MODULE.validate(subject)))

    def test_invalid_type_scope_and_description(self) -> None:
        self.assertTrue(MODULE.validate("feature(api): add pagination"))
        self.assertTrue(MODULE.validate("feat(): add pagination"))
        self.assertTrue(MODULE.validate("feat(api):"))
        self.assertTrue(MODULE.validate("feat(api):   "))
        self.assertTrue(MODULE.validate("feat( api): add pagination"))
        self.assertTrue(MODULE.validate("feat(api(core)): add pagination"))

    def test_parentheses_are_allowed_in_description(self) -> None:
        self.assertEqual(MODULE.validate("feat(api): add (pagination)"), [])

    def test_optional_body_does_not_change_subject_validation(self) -> None:
        self.assertEqual(MODULE.validate("fix(api): handle timeout\n\nDetails"), [])
        self.assertEqual(MODULE.validate("fix(api): handle timeout\r\n\r\nDetails"), [])

    def test_empty_message(self) -> None:
        self.assertEqual(MODULE.validate(""), ["commit message is empty"])


if __name__ == "__main__":
    unittest.main()
