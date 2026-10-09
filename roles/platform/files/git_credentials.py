#!/usr/bin/env python3
"""Ephemeral credentials for the initial HTTP push, never embedded in a Git URL."""
import os
import sys

if len(sys.argv) > 1 and sys.argv[1] == 'get':
    print('username=' + os.environ['FORGEJO_ADMIN_USER'])
    print('password=' + os.environ['FORGEJO_ADMIN_PASSWORD'])
