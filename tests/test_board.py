#!/usr/bin/env python3
"""Exercise board delivery with an isolated checkout and a fake gh API."""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1]
FAKE_GH = r'''#!/usr/bin/env python3
import base64, json, os, sys
from pathlib import Path
args = sys.argv[1:]
endpoint = next((x for x in args if x.startswith('repos/') or x == 'user'), '')
if endpoint == 'repos/Owner/Repo':
    print('Owner/Repo')
elif endpoint == 'user':
    print('alice')
elif '/comments?' in endpoint:
    if os.environ.get('FAIL_COMMENTS'):
        sys.exit(1)
    comments = json.loads(Path(os.environ['COMMENTS_FILE']).read_text())
    if 'since=' in endpoint:
        since = endpoint.split('since=', 1)[1].split('&', 1)[0]
        comments = [c for c in comments if c['created_at'] >= since]
    if '--paginate' not in args:
        page = int(endpoint.split('&page=', 1)[1]) if '&page=' in endpoint else 1
        comments = comments[(page - 1) * 100:page * 100]
    for c in comments:
        body = base64.b64encode(c['body'].encode()).decode()
        print(f"{c['id']}\t{c['login']}\t{c['created_at']}\t{body}")
elif endpoint == 'repos/Owner/Repo/issues/1':
    print(len(json.loads(Path(os.environ['COMMENTS_FILE']).read_text())))
elif endpoint == 'repos/Owner/Repo/issues/1/comments':
    body = next(x[5:] for x in args if x.startswith('body='))
    path = Path(os.environ['COMMENTS_FILE'])
    comments = json.loads(path.read_text())
    comments.append({'id': 13, 'login': 'alice', 'created_at': '2026-01-01T00:00:13Z', 'body': body})
    path.write_text(json.dumps(comments))
    print('https://github.com/Owner/Repo/issues/1#issuecomment-13')
else:
    print('unexpected gh call: ' + repr(args), file=sys.stderr)
    sys.exit(1)
'''


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(SOURCE / 'tools', self.root / 'tools')
        shutil.copytree(SOURCE / '.claude', self.root / '.claude')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        gh = self.bin / 'gh'
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.comments_file = self.root / 'comments.json'
        self.comments = [self.comment(i, 'alice' if i == 1 else 'bob') for i in range(1, 13)]
        self.save()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        BOARD_REPO='Owner/Repo', BOARD_LOGIN='alice', COMMENTS_FILE=str(self.comments_file))

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def comment(n, login='bob'):
        return {'id': n, 'login': login,
                'created_at': (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'body': f"[{login}'s Agent] post {n}" + (' @all' if n == 1 else '')}

    def save(self):
        self.comments_file.write_text(json.dumps(self.comments))

    def run_board(self, *args, reader=None, extra=None):
        env = dict(self.env)
        env.pop('BOARD_READER_ID', None)
        if reader is not None:
            env['BOARD_READER_ID'] = reader
        if extra:
            env.update(extra)
        return subprocess.run([str(self.root / 'tools/board'), *args], cwd=self.root, env=env,
                              text=True, capture_output=True, timeout=8)

    def test_independent_readers_receive_full_history_and_same_account(self):
        first = self.run_board('unread', reader='session-a')
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn('post 1 @all', first.stdout)
        self.assertIn('** MENTION **', first.stdout)
        self.assertIn('post 12', first.stdout)
        second = self.run_board('unread', reader='session-b')
        self.assertEqual(second.stdout, first.stdout)
        self.assertEqual(self.run_board('unread', reader='session-a').stdout, '')
        self.comments.append(self.comment(13, 'alice'))
        self.save()
        for reader in ('session-a', 'session-b'):
            result = self.run_board('unread', reader=reader)
            self.assertIn('post 13', result.stdout)
            self.assertNotIn('post 12', result.stdout)

    def test_paginated_history_and_post(self):
        self.comments = [self.comment(i) for i in range(1, 116)]
        self.save()
        result = self.run_board('unread', reader='large-history')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('post 1', result.stdout)
        self.assertIn('post 115', result.stdout)
        self.comments = [self.comment(i) for i in range(1, 13)]
        self.save()
        result = self.run_board('post', "[Alice's Agent] hello @all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('issuecomment-13', result.stdout)
        self.assertIn("hello @all", self.run_board('unread', reader='post-reader').stdout)
        self.assertIn('post 12', self.run_board('read', '-n', '2').stdout)
        self.assertRegex(self.run_board('new-reader').stdout.strip(), r'^reader-[0-9-]+$')

    def test_missing_reader_never_consumes_and_wait_requires_one(self):
        a = self.run_board('unread')
        b = self.run_board('unread')
        self.assertEqual(a.stdout, b.stdout)
        self.assertIn('post 1', a.stdout)
        result = self.run_board('wait')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BOARD_READER_ID', result.stderr)

    def test_failed_fetch_does_not_advance_cursor(self):
        self.run_board('unread', reader='session-a')
        self.comments.append(self.comment(13))
        self.save()
        self.assertNotEqual(self.run_board('unread', reader='session-a', extra={'FAIL_COMMENTS': '1'}).returncode, 0)
        self.assertIn('post 13', self.run_board('unread', reader='session-a').stdout)

    def test_wait_and_argument_validation(self):
        self.run_board('unread', reader='session-a')
        env = dict(self.env, BOARD_READER_ID='session-a')
        process = subprocess.Popen([str(self.root / 'tools/board'), 'wait', '--interval', '1', '--timeout', '5'],
                                   cwd=self.root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.3)
        self.comments.append(self.comment(13, 'alice'))
        self.save()
        out, err = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 0, err)
        self.assertIn('post 13', out)
        self.assertNotEqual(self.run_board('read', '-n').returncode, 0)
        self.assertNotEqual(self.run_board('wait', '--interval', reader='session-a').returncode, 0)
        self.assertNotEqual(self.run_board('unread', reader='../invalid').returncode, 0)

    def test_claude_hooks_use_per_session_reader(self):
        def hook(name, session):
            return subprocess.run([str(self.root / '.claude/hooks' / name)], cwd=self.root,
                                  env=dict(self.env, CLAUDE_PROJECT_DIR=str(self.root)),
                                  input=json.dumps({'session_id': session}), capture_output=True,
                                  text=True, timeout=8)
        start = hook('board-session-start.sh', 'session-a')
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn('BOARD_READER_ID=claude-session-a', start.stdout)
        self.assertIn('post 1', start.stdout)
        self.assertEqual(hook('board-prompt.sh', 'session-a').stdout, '')
        self.assertIn('post 1', hook('board-prompt.sh', 'session-b').stdout)


if __name__ == '__main__':
    unittest.main()
