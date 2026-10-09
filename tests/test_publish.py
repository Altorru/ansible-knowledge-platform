import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'roles/platform/files/publish.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        shutil.copytree(ROOT / 'seed', self.repo)
        self.git('init', '--initial-branch=main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.commit()
        self.config = {
            'root': str(self.base / 'published'), 'repository': str(self.repo / '.git'),
            'branch': 'main', 'mkdocs': os.environ.get('MKDOCS_BIN', shutil.which('mkdocs')),
            'mkdocs_config': str(ROOT / 'seed/mkdocs.yml'),
            'requirements': str(ROOT / 'requirements.txt'),
        }
        if not self.config['mkdocs']:
            self.skipTest('Install requirements.txt to run real MkDocs build tests')

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-m', 'Document update')
        return self.git('rev-parse', 'HEAD')

    def publish(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            publisher.publish(self.config)
        return out.getvalue()

    def test_real_build_and_unchanged_commit(self):
        self.assertIn('PUBLISHED:', self.publish())
        current = Path(self.config['root']) / 'current'
        self.assertTrue((current / 'index.html').is_file())
        target = current.resolve()
        self.assertIn('UNCHANGED:', self.publish())
        self.assertEqual(current.resolve(), target)

    def test_broken_link_keeps_last_good_release_then_recovers(self):
        self.publish()
        current = Path(self.config['root']) / 'current'
        previous = current.resolve()
        index = self.repo / 'docs/index.md'
        index.write_text(index.read_text() + '\n[Missing](does-not-exist.md)\n')
        self.commit()
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        self.assertEqual(current.resolve(), previous)
        index.write_text('# Documentation repaired\n')
        commit = self.commit()
        self.assertIn('PUBLISHED:', self.publish())
        self.assertEqual((current / 'commit.txt').read_text().strip(), commit)

    def test_repository_hooks_and_config_are_not_executed(self):
        marker = self.base / 'executed'
        (self.repo / 'mkdocs.yml').write_text('hooks:\n  - malicious.py\n')
        (self.repo / 'malicious.py').write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
        self.commit()
        self.assertIn('PUBLISHED:', self.publish())
        self.assertFalse(marker.exists())

    def test_symlink_in_documents_is_rejected(self):
        self.publish()
        current = Path(self.config['root']) / 'current'
        previous = current.resolve()
        (self.repo / 'docs/secret').symlink_to('/etc/passwd')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'Unsafe document path'):
            self.publish()
        self.assertEqual(current.resolve(), previous)


if __name__ == '__main__':
    unittest.main()
