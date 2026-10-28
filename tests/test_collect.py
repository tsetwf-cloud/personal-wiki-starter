"""Only synthetic fixtures; never discovers a host profile or database."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/collect.py'


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.base = Path(self.tmp.name)
        self.output = self.base / 'collection'
        self.input = self.base / 'messages.jsonl'
        self.input.write_text('', encoding='utf-8')
        self.config = self.base / 'collector.json'
        self.settings = {'version': 1, 'adapter': 'jsonl', 'input': str(self.input),
                         'scopes': [self.scope()]}
        self.save_config()

    def tearDown(self):
        self.tmp.cleanup()

    def scope(self, **changes):
        return dict(source='export', platform='telegram', conversation='fictional-chat',
                    profile='demo', thread=None, roles=['user', 'assistant'], **changes)

    def message(self, **changes):
        value = dict(source='export', platform='telegram', conversation='fictional-chat',
                     profile='demo', thread=None, message_id='message-1',
                     time='2026-01-02T03:04:05+00:00', role='user', content='虚构阅读计划', active=True)
        value.update(changes)
        return value

    def save_config(self):
        self.config.write_text(json.dumps(self.settings), encoding='utf-8')

    def write_rows(self, rows):
        self.input.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')

    def cli(self, command, *args, ok=True, env=None):
        p = subprocess.run([sys.executable, '-B', str(CLI), '--config', str(self.config),
                            '--output', str(self.output), command, *args], capture_output=True,
                           text=True, env={**os.environ, **(env or {})})
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0, p.stdout)
        return p

    def test_doctor_and_preview_are_read_only_with_honest_capabilities(self):
        self.write_rows([self.message()])
        doctor = self.cli('doctor')
        self.assertEqual(doctor['adapter'], 'jsonl')
        self.assertEqual(doctor['real_message_integration'], 'unverified')
        self.assertFalse(doctor['network'])
        preview = self.cli('preview')
        self.assertEqual(preview['message_count'], 1)
        self.assertEqual(preview['writes'], [])
        self.assertFalse(self.output.exists())
        template = self.cli('template')
        self.assertEqual(template['adapter'], 'jsonl')
        self.assertIn('scopes', template)
        self.assertFalse(self.output.exists())

    def test_collection_exports_provenance_manifest_and_resumes_without_duplicates(self):
        self.write_rows([self.message(), self.message(message_id='2', content='助手建议', role='assistant'),
                         self.message(message_id='3', conversation='other')])
        self.cli('initialize', '--start', 'history')
        result = self.cli('collect')
        self.assertEqual(result['message_count'], 2)
        manifest = json.loads((self.output / result['manifest']).read_text(encoding='utf-8'))
        self.assertEqual(manifest['channel'], 'file')
        self.assertEqual(len(manifest['sources']), 2)
        for source in manifest['sources']:
            body = (self.output / source['file']).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), source['source_id'])
            self.assertIn('fictional-chat', body.decode('utf-8'))
            self.assertNotIn('fictional-chat', source['file'])
        self.assertEqual(self.cli('collect')['message_count'], 0)
        with self.input.open('a', encoding='utf-8') as f:
            f.write(json.dumps(self.message(message_id='4', content='next')) + '\n')
        self.assertEqual(self.cli('collect')['message_count'], 1)
        self.assertEqual(len(list((self.output / 'sources').glob('*.txt'))), 3)

    def test_scope_cannot_expand_or_change_input_and_now_baselines(self):
        self.write_rows([self.message()])
        self.cli('collect', ok=False)
        self.cli('initialize', '--start', 'now')
        self.assertEqual(self.cli('collect')['message_count'], 0)
        self.settings['scopes'][0]['thread'] = 'another-topic'
        self.save_config()
        self.cli('collect', ok=False)
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 1)

    def test_scope_batch_optout_isolation_and_strict_record_schema(self):
        self.write_rows([self.message(), self.message(message_id='2', content='#不入库'),
                         self.message(message_id='3', profile='other', content='secret')])
        self.assertEqual(self.cli('preview')['message_count'], 0)
        self.cli('initialize', '--start', 'history')
        self.assertEqual(self.cli('collect')['message_count'], 0)
        broken = self.message()
        del broken['active']
        self.write_rows([broken])
        self.cli('preview', ok=False)

    def test_crash_after_source_requires_exact_token_and_rolls_forward(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        self.cli('collect', ok=False, env={'COLLECT_FAIL_AFTER': 'source'})
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 0)
        status = self.cli('status')
        self.assertTrue(status['recovery_required'])
        self.cli('collect', ok=False)
        self.cli('recover', '--token', 'wrong', ok=False)
        self.cli('recover', '--token', status['lock_token'])
        self.assertEqual(self.cli('collect')['message_count'], 0)
        self.assertEqual(len(list((self.output / 'sources').glob('*.txt'))), 1)
        self.assertEqual(len(list((self.output / 'manifests').glob('*.json'))), 1)

    def test_rewrite_and_immutable_corruption_fail_without_cursor_advance(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        self.cli('collect', ok=False, env={'COLLECT_FAIL_AFTER': 'source'})
        source = next((self.output / 'sources').glob('*.txt'))
        source.write_text('tampered', encoding='utf-8')
        self.cli('recover', '--token', self.cli('status')['lock_token'], ok=False)
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 0)

    def sqlite_fixture(self):
        db = self.base / 'fixture.db'
        with sqlite3.connect(db) as c:
            c.executescript('''CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT,
              profile_name TEXT, chat_id TEXT, thread_id TEXT, chat_type TEXT,
              parent_session_id TEXT, end_reason TEXT);
              CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT,
              content TEXT, timestamp REAL, active INTEGER, _compressed_summary INTEGER,
              tool_calls TEXT, display_kind TEXT, platform_message_id TEXT);''')
            c.executemany('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', [
                ('root', 'telegram', 'demo', 'fictional-chat', None, 'dm', None, 'compression'),
                ('child', 'telegram', 'demo', 'fictional-chat', None, 'dm', 'root', None),
                ('other', 'telegram', 'other', 'fictional-chat', None, 'dm', None, None),
                ('topic', 'telegram', 'demo', 'fictional-chat', '42', 'dm', None, None),
                ('sub', 'telegram', 'demo', 'fictional-chat', None, 'dm', 'child', None)])
            messages = [
                (1, 'root', 'user', 'root request', 1, 0, None, None),
                (2, 'child', 'assistant', 'child answer', 1, 0, '[]', None),
                (3, 'other', 'user', 'other private', 1, 0, None, None),
                (4, 'topic', 'user', 'other topic', 1, 0, None, None),
                (5, 'sub', 'user', 'subagent', 1, 0, None, None),
                (6, 'child', 'user', 'compressed', 1, 1, None, None),
                (7, 'child', 'user', 'inactive', 0, 0, None, None),
                (8, 'child', 'tool', 'tool data', 1, 0, None, None),
                (9, 'child', 'assistant', 'tool call', 1, 0, '[{}]', None),
                (10, 'child', 'user', 'notification', 1, 0, None, 'internal_notification'),
                (11, 'child', 'user', '[CONTEXT SUMMARY]: generated', 1, 0, None, None)]
            for i, session, role, content, active, summary, tools, display in messages:
                c.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?)',
                          (i, session, role, content, 1767313445, active, summary, tools, display, None))
        self.settings['adapter'] = 'hermes-sqlite'
        self.settings['input'] = str(db)
        self.settings['scopes'][0]['source'] = 'telegram'
        self.save_config()
        return db

    def test_sqlite_readonly_schema_scoping_cross_compression_and_filters(self):
        db = self.sqlite_fixture()
        before = db.read_bytes()
        report = self.cli('doctor')
        self.assertEqual(report['schema'], 'supported')
        self.assertEqual(report['real_message_integration'], 'unverified')
        self.assertEqual(self.cli('preview')['message_count'], 2)
        self.assertFalse(self.output.exists())
        self.cli('initialize', '--start', 'history')
        result = self.cli('collect')
        self.assertEqual(result['message_count'], 2)
        self.assertEqual(self.cli('collect')['message_count'], 0)
        self.assertEqual(db.read_bytes(), before)
        text = '\n'.join(p.read_text(encoding='utf-8') for p in (self.output / 'sources').glob('*'))
        self.assertIn('root request', text)
        self.assertIn('child answer', text)
        self.assertNotIn('other private', text)
        self.assertNotIn('subagent', text)
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO messages VALUES (12,'child','user','next request',1767313446,1,0,NULL,NULL,NULL)")
        self.assertEqual(self.cli('collect')['message_count'], 1)

    def test_sqlite_unsupported_schema_fails_closed_without_creating_output(self):
        db = self.base / 'unsupported.db'
        with sqlite3.connect(db) as c:
            c.execute('CREATE TABLE messages(id INTEGER)')
        self.settings.update(adapter='hermes-sqlite', input=str(db))
        self.save_config()
        self.assertEqual(self.cli('doctor')['schema'], 'unsupported')
        self.cli('preview', ok=False)
        self.assertFalse(self.output.exists())

    def test_append_identity_conflict_and_input_rewrite_are_rejected(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        self.cli('collect')
        with self.input.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(self.message(content='changed same identity')) + '\n')
        self.cli('collect', ok=False)
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 1)
        self.assertTrue(self.cli('status')['recovery_required'])

    def test_conflicting_duplicate_in_single_batch_fails_before_export(self):
        self.write_rows([self.message(), self.message(content='changed same identity')])
        self.cli('initialize', '--start', 'history')
        self.cli('collect', ok=False)
        self.assertFalse((self.output / 'sources').exists())
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 0)

    def test_optout_applies_even_when_only_assistant_role_is_selected(self):
        self.settings['scopes'][0]['roles'] = ['assistant']
        self.save_config()
        self.write_rows([self.message(content='#仅本地'), self.message(message_id='2', role='assistant')])
        self.assertEqual(self.cli('preview')['message_count'], 0)

    def test_existing_lock_never_overwrites_another_writer(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        lock = self.output / 'lock.json'
        lock.write_text('{"token":"other-writer"}', encoding='utf-8')
        self.cli('collect', ok=False)
        self.assertEqual(json.loads(lock.read_text())['token'], 'other-writer')
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 0)

    def test_rewrite_of_collected_jsonl_is_rejected_without_silent_reset(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        self.cli('collect')
        self.write_rows([self.message(content='rewritten')])
        self.cli('collect', ok=False)
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 1)

    def test_crash_after_cursor_is_idempotent_on_recovery(self):
        self.write_rows([self.message()])
        self.cli('initialize', '--start', 'history')
        self.cli('collect', ok=False, env={'COLLECT_FAIL_AFTER': 'cursor'})
        self.assertEqual(json.loads((self.output / 'state.json').read_text())['cursor'], 1)
        self.cli('recover', '--token', self.cli('status')['lock_token'])
        self.assertEqual(self.cli('collect')['message_count'], 0)
        self.assertEqual(len(list((self.output / 'sources').glob('*.txt'))), 1)


if __name__ == '__main__':
    unittest.main()
