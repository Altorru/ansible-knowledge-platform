#!/usr/bin/env python3
"""Provision the first account and seed an empty repository without overwriting data."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def main():
    user = os.environ['FORGEJO_ADMIN_USER']
    password = os.environ['FORGEJO_ADMIN_PASSWORD']
    repo = os.environ['KNOWLEDGE_REPO']
    seed = Path(os.environ['KNOWLEDGE_SEED'])
    cli = ['/usr/local/bin/forgejo', '--config', '/etc/forgejo/app.ini',
           '--work-path', '/var/lib/forgejo', 'admin', 'user']
    users = run(cli + ['list']).stdout.splitlines()
    changed = False
    if not any(len(fields := line.split()) > 1 and fields[1] == user for line in users):
        run(cli + ['create', '--username', user, '--password', password,
                   '--email', os.environ['FORGEJO_ADMIN_EMAIL'], '--admin', '--must-change-password=false'])
        changed = True
    auth = 'Basic ' + base64.b64encode(f'{user}:{password}'.encode()).decode()

    def api(path, body=None):
        request = Request('http://127.0.0.1:3000/api/v1' + path,
                          data=None if body is None else json.dumps(body).encode(),
                          headers={'Authorization': auth, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    try:
        repository = api(f'/repos/{user}/{repo}')
    except HTTPError as error:
        if error.code != 404:
            raise
        repository = api('/user/repos', {'name': repo, 'private': True,
                                         'auto_init': False, 'default_branch': 'main'})
        changed = True
    if repository['empty']:
        with tempfile.TemporaryDirectory(prefix='knowledge-seed-') as temp:
            temp = Path(temp)
            for item in seed.iterdir():
                if item.is_dir():
                    shutil.copytree(item, temp / item.name)
                else:
                    shutil.copy2(item, temp / item.name)
            run(['git', 'init', '--initial-branch=main'], cwd=temp)
            run(['git', 'add', '.'], cwd=temp)
            run(['git', '-c', 'user.name=Documentation', '-c', f'user.email={os.environ["FORGEJO_ADMIN_EMAIL"]}',
                 'commit', '-m', 'Initialiser la base de connaissance'], cwd=temp)
            run(['git', '-c', 'credential.helper=', '-c',
                 'credential.helper=!python3 /usr/local/lib/knowledge/git_credentials.py',
                 'push', f'http://127.0.0.1:3000/{user}/{repo}.git', 'HEAD:refs/heads/main'], cwd=temp)
        changed = True
    print('CHANGED' if changed else 'UNCHANGED')


if __name__ == '__main__':
    main()
