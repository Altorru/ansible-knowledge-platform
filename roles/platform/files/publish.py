#!/usr/bin/env python3
"""Build a committed snapshot and switch the served release only on success."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)


def publish(config):
    root = Path(config['root']).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'publish.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('SKIPPED: another publication or backup is running')
            return
        git = ['git', '-c', f"safe.directory={config['repository']}",
               '--git-dir', config['repository']]
        commit = run(git + ['rev-parse', '--verify', f"refs/heads/{config['branch']}^{{commit}}"]).stdout.strip()
        current = root / 'current'
        fingerprint = hashlib.sha256(
            Path(config['mkdocs_config']).read_bytes()
            + Path(config['requirements']).read_bytes()
            + Path(__file__).read_bytes()
        ).hexdigest()[:16]
        release_id = commit + '-' + fingerprint
        releases = root / 'releases'
        releases.mkdir(exist_ok=True)
        release = releases / release_id
        if current.is_symlink() and current.resolve() == release and (release / 'index.html').is_file():
            print(f'UNCHANGED: {commit}')
            return
        with tempfile.TemporaryDirectory(prefix='build-', dir=root) as tmp:
            tmp = Path(tmp)
            archive = tmp / 'source.tar'
            run(git + ['archive', '--format=tar', '--output', str(archive), commit])
            source = tmp / 'source'
            source.mkdir()
            with tarfile.open(archive) as tar:
                # Documents only: never run configuration, plugins or hooks from Git.
                for member in tar.getmembers():
                    if member.name != 'docs' and not member.name.startswith('docs/'):
                        continue
                    target = (source / member.name).resolve()
                    if not target.is_relative_to(source.resolve()) or not (member.isfile() or member.isdir()):
                        raise ValueError(f'Unsafe document path: {member.name}')
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with tar.extractfile(member) as incoming, target.open('wb') as outgoing:
                            shutil.copyfileobj(incoming, outgoing)
            if not (source / 'docs/index.md').is_file():
                raise ValueError('docs/index.md is required')
            config_copy = source / 'mkdocs.yml'
            shutil.copyfile(config['mkdocs_config'], config_copy)
            output = tmp / 'site'
            built = run([config['mkdocs'], 'build', '--strict', '--config-file', str(config_copy),
                         '--site-dir', str(output)], cwd=source)
            if not (output / 'index.html').is_file():
                raise ValueError('Build did not produce index.html')
            (output / 'commit.txt').write_text(commit + '\n')
            (output / 'release.json').write_text(json.dumps({'commit': commit, 'build': fingerprint}) + '\n')
            # Release directories are immutable, identified by commit and build configuration.
            if not release.exists():
                os.rename(output, release)
            next_link = root / '.current-next'
            next_link.unlink(missing_ok=True)
            next_link.symlink_to(Path('releases') / release_id)
            os.replace(next_link, current)
            print(f'PUBLISHED: {commit}')
            if built.stderr:
                print(built.stderr, end='')
        # Keep five complete releases, always preserving the active one.
        others = sorted((p for p in releases.iterdir() if p.is_dir() and p != release),
                        key=lambda p: p.stat().st_mtime, reverse=True)
        for old in others[4:]:
            shutil.rmtree(old)


if __name__ == '__main__':
    try:
        publish(json.loads(Path(sys.argv[1]).read_text()))
    except subprocess.CalledProcessError as error:
        print(error.stderr or str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
