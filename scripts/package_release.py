#!/usr/bin/env python3
"""Export the committed source and a standalone, licensed Agent Skill."""

import hashlib
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'git-commit-convention-skill'
SKILL_PREFIX = f'.agents/skills/{NAME}/'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    if git('status', '--porcelain', '--untracked-files=normal').strip():
        raise SystemExit('ERROR: commit all source changes before packaging')
    version = git('show', 'HEAD:VERSION').decode('utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise SystemExit('ERROR: VERSION must be a numeric major.minor.patch version')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    source_zip = output / f'{NAME}-{version}-source.zip'
    git('archive', '--format=zip', f'--prefix={NAME}-{version}/', f'--output={source_zip}', 'HEAD')
    skill_zip = output / f'{NAME}-{version}.zip'
    with zipfile.ZipFile(source_zip) as source, zipfile.ZipFile(skill_zip, 'w', zipfile.ZIP_DEFLATED) as skill:
        prefix = f'{NAME}-{version}/'
        for entry in source.infolist():
            relative = entry.filename.removeprefix(prefix)
            if entry.is_dir():
                continue
            if relative.startswith(SKILL_PREFIX):
                target = f'{NAME}/' + relative.removeprefix(SKILL_PREFIX)
            elif relative == 'LICENSE':
                target = f'{NAME}/LICENSE'
            else:
                continue
            copied = zipfile.ZipInfo(target, entry.date_time)
            copied.compress_type = zipfile.ZIP_DEFLATED
            copied.external_attr = entry.external_attr
            skill.writestr(copied, source.read(entry))
    checksum = output / f'{NAME}-{version}-SHA256SUMS.txt'
    checksum.write_text(''.join(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n'
        for path in [skill_zip, source_zip]
    ), encoding='utf-8')
    print(f'Packaged {version} from {git("rev-parse", "HEAD").decode().strip()}')
    for path in [skill_zip, source_zip, checksum]:
        print(path)


if __name__ == '__main__':
    main()
