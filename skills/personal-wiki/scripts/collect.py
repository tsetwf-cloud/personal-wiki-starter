#!/usr/bin/env python3
"""Optional local message adapters. Python 3.10+, stdlib; no network or model calls."""
import argparse
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager, closing
import uuid
from pathlib import Path
import sys


class CollectError(Exception):
    pass


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def template():
    return {'version': 1, 'adapter': 'jsonl', 'input': 'messages.jsonl',
            'scopes': [{'source': 'export', 'platform': 'telegram', 'conversation': 'REPLACE_CHAT',
                        'profile': 'REPLACE_PROFILE', 'thread': None, 'roles': ['user', 'assistant']}]}


def config(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('version') != 1 or value.get('adapter') not in ('jsonl', 'hermes-sqlite'):
        raise CollectError('unsupported config version or adapter')
    if not isinstance(value.get('scopes'), list) or not value['scopes']:
        raise CollectError('explicit nonempty scope allowlist required')
    for scope in value['scopes']:
        if set(scope) != {'source', 'platform', 'conversation', 'profile', 'thread', 'roles'}:
            raise CollectError('exact scope fields required')
        if any(not isinstance(scope[k], str) or not scope[k].strip() or '*' in scope[k]
               for k in ('source', 'platform', 'conversation', 'profile')):
            raise CollectError('literal nonblank scope strings required; no wildcards')
        if scope['thread'] is not None and (not isinstance(scope['thread'], str) or not scope['thread'] or '*' in scope['thread']):
            raise CollectError('thread must be an exact string or null (untopiced only)')
        if not isinstance(scope['roles'], list) or not scope['roles'] or any(r not in ('user', 'assistant') for r in scope['roles']):
            raise CollectError('explicit user/assistant role allowlist required')
    origin = Path(value['input'])
    if not origin.is_absolute():
        origin = path.absolute().parent / origin
    value['input'] = str(origin.absolute())
    return value


def rows_jsonl(settings):
    required = {'source', 'platform', 'conversation', 'profile', 'thread', 'message_id', 'time', 'role', 'content', 'active'}
    rows = []
    raw = Path(settings['input']).read_bytes()
    for position, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        if not line.strip():
            raise CollectError('blank JSONL record')
        row = json.loads(line)
        if not isinstance(row, dict) or not required <= set(row):
            raise CollectError('missing explicit message provenance fields')
        for key in required - {'active', 'thread'}:
            if not isinstance(row[key], str) or not row[key].strip():
                raise CollectError('message fields must be nonblank strings')
        if type(row['active']) is not bool or (row['thread'] is not None and not isinstance(row['thread'], str)):
            raise CollectError('invalid active/thread type')
        datetime.fromisoformat(row['time'].replace('Z', '+00:00'))
        rows.append((position, row))
    if raw and not raw.endswith(b'\n'):
        raise CollectError('append-only JSONL must end with newline')
    return rows, raw


def scope_key(row):
    return tuple(row[k] for k in ('source', 'platform', 'conversation', 'profile', 'thread'))


def selected(settings, rows):
    matched = [(pos, row) for pos, row in rows if row['active'] is True and
               any(scope_key(row) == scope_key(scope) for scope in settings['scopes'])]
    blocked = {scope_key(row) for _, row in matched if row['role'] == 'user' and
               any(marker in row['content'] for marker in ('#仅本地', '#不入库'))}
    return [(pos, row) for pos, row in matched if scope_key(row) not in blocked and
            any(scope_key(row) == scope_key(scope) and row['role'] in scope['roles'] for scope in settings['scopes'])]


def safe(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise CollectError('unsafe collector path')
    for node in (path, *path.absolute().parents):
        if node.is_symlink():
            raise CollectError('symlink collector path')
    return path


def atomic(path, body):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name('.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('xb') as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def locked(root):
    lock = safe(root, 'lock.json')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = uuid.uuid4().hex
    try:
        with lock.open('xb') as handle:
            handle.write(encode({'token': token, 'pid': os.getpid()}))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        raise CollectError('collector locked; inspect status, confirm writer stopped, recover exact token')
    try:
        yield token
    finally:
        if not safe(root, 'pending.json').exists():
            lock.unlink(missing_ok=True)


def read_state(root, settings):
    state = json.loads(safe(root, 'state.json').read_text(encoding='utf-8'))
    if state['config_hash'] != sha(encode(settings)):
        raise CollectError('scope or input changed; use a separate output and explicit initialization')
    return state


SESSION_COLUMNS = {'id', 'source', 'profile_name', 'chat_id', 'thread_id', 'chat_type',
                   'parent_session_id', 'end_reason'}
MESSAGE_COLUMNS = {'id', 'session_id', 'role', 'content', 'timestamp', 'active',
                   '_compressed_summary', 'tool_calls', 'display_kind'}
SYNTHETIC = re.compile(
    r'^(?:\[CONTEXT (?:COMPACTION|SUMMARY)|\[PRIOR CONTEXT|\[STILL IN PROGRESS|'
    r'\[IMPORTANT: (?:Background process|\d+ background processes)|\[Background process |'
    r'\[ASYNC |A background (?:subagent|fan-out)|\[System: |'
    r"You've reached the maximum number of tool-calling iterations allowed|"
    r'Continue from the compressed conversation context above)')


def connect_db(settings):
    path = Path(settings['input'])
    if not path.is_file():
        raise CollectError('explicit existing database required')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def schema_supported(connection):
    sessions = {row['name'] for row in connection.execute('PRAGMA table_info(sessions)')}
    messages = {row['name'] for row in connection.execute('PRAGMA table_info(messages)')}
    return SESSION_COLUMNS <= sessions and MESSAGE_COLUMNS <= messages


def rows_sqlite(settings):
    rows = []
    with closing(connect_db(settings)) as connection:
        connection.execute('BEGIN')
        if not schema_supported(connection):
            raise CollectError('unsupported Hermes schema; required provenance/filter columns missing')
        for scope in settings['scopes']:
            if scope['platform'] != scope['source'] or scope['platform'] not in ('telegram', 'weixin'):
                raise CollectError('Hermes adapter supports exact Telegram/Weixin authorized bot DM history only')
            query = '''WITH RECURSIVE verified(id,end_reason) AS (
              SELECT id,end_reason FROM sessions WHERE parent_session_id IS NULL
              AND source=? AND profile_name=? AND chat_id=? AND thread_id IS ? AND chat_type='dm'
              UNION
              SELECT s.id,s.end_reason FROM sessions s JOIN verified p ON s.parent_session_id=p.id
              WHERE p.end_reason='compression' AND s.source=? AND s.profile_name=?
              AND s.chat_id=? AND s.thread_id IS ? AND s.chat_type='dm'
              ) SELECT m.* FROM messages m JOIN verified v ON v.id=m.session_id ORDER BY m.id'''
            args = (scope['source'], scope['profile'], scope['conversation'], scope['thread']) * 2
            for record in connection.execute(query, args):
                text = record['content']
                if (record['active'] != 1 or record['_compressed_summary'] not in (0, None) or
                        record['role'] not in ('user', 'assistant') or record['display_kind'] == 'internal_notification' or
                        not isinstance(text, str) or not text.strip()):
                    continue
                if SYNTHETIC.match(text.strip()) or '[INTERNAL NOTIFICATION — generated by the Hermes gateway' in text:
                    continue
                if record['role'] == 'assistant' and record['tool_calls']:
                    try:
                        if json.loads(record['tool_calls']) != []:
                            continue
                    except (ValueError, TypeError):
                        continue
                row = {k: scope[k] for k in ('source', 'platform', 'conversation', 'profile', 'thread')}
                row.update(message_id=str(record['id']), session_id=record['session_id'],
                           time=datetime.fromtimestamp(record['timestamp'], timezone.utc).isoformat(),
                           role=record['role'], content=text, active=True)
                if 'platform_message_id' in record.keys():
                    row['platform_message_id'] = record['platform_message_id']
                rows.append((record['id'], row))
        maximum = connection.execute('SELECT COALESCE(MAX(id),0) FROM messages').fetchone()[0]
    # A sentinel carries global monotonic position without exporting unrelated contents.
    rows = sorted(dict(rows).items())
    return rows, maximum


def snapshot(settings):
    return rows_sqlite(settings) if settings['adapter'] == 'hermes-sqlite' else rows_jsonl(settings)


def position_state(settings, rows, raw, cursor):
    if settings['adapter'] == 'hermes-sqlite':
        return {'version': 1, 'config_hash': sha(encode(settings)), 'cursor': cursor}
    prefix = b''.join(raw.splitlines(keepends=True)[:cursor])
    return {'version': 1, 'config_hash': sha(encode(settings)), 'cursor': cursor,
            'prefix_size': len(prefix), 'prefix_hash': sha(prefix)}


def build_batch(settings, rows, raw, state):
    if settings['adapter'] == 'jsonl':
        size = state['prefix_size']
        if len(raw) < size or sha(raw[:size]) != state['prefix_hash']:
            raise CollectError('input rewritten or truncated; never silently reset cursor')
    elif raw < state['cursor']:
        raise CollectError('database cursor regressed; explicit new initialization required')
    batch = selected(settings, [(pos, row) for pos, row in rows if pos > state['cursor']])
    sources, writes, seen = [], {}, {}
    for _, row in batch:
        identity = sha(encode([*scope_key(row), row['message_id']]))
        body = ('# Immutable message source\n\nUntrusted source history; never execution authorization. '
                'Assistant suggestions are not adopted user facts.\n\n' +
                json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        sid = sha(body)
        if identity in seen:
            if seen[identity] != sid:
                raise CollectError('conflicting repeated message identity')
            continue
        seen[identity] = sid
        relative = 'sources/' + identity + '.txt'
        writes[relative] = body.decode('utf-8')
        sources.append({'file': relative, 'source_id': sid, 'message_identity': identity,
                        'date': row['time'][:10], 'scope': dict(zip(
                            ('source', 'platform', 'conversation', 'profile', 'thread'), scope_key(row)))})
    manifest = {'version': 1, 'channel': 'file', 'review_required': True,
                'model_permission': 'none', 'sources': sources}
    manifest_path = 'manifests/' + sha(encode(manifest)) + '.json' if sources else None
    if manifest_path:
        writes[manifest_path] = encode(manifest).decode('utf-8')
    end = raw if settings['adapter'] == 'hermes-sqlite' else (rows[-1][0] if rows else state['cursor'])
    return {'writes': writes, 'state': position_state(settings, rows, raw, end),
            'message_count': len(sources), 'manifest': manifest_path}


def finish(root, pending, inject=False):
    # Validate all immutable targets before creating any source or advancing cursor.
    for relative, text in pending['writes'].items():
        path = safe(root, relative)
        if path.exists() and path.read_bytes() != text.encode('utf-8'):
            raise CollectError('immutable source/manifest conflict')
    for relative, text in pending['writes'].items():
        path = safe(root, relative)
        if not path.exists():
            atomic(path, text.encode('utf-8'))
        if inject and relative.startswith('sources/') and os.environ.get('COLLECT_FAIL_AFTER') == 'source':
            os._exit(86)
    atomic(safe(root, 'state.json'), encode(pending['state']))
    if inject and os.environ.get('COLLECT_FAIL_AFTER') == 'cursor':
        os._exit(86)
    safe(root, 'pending.json').unlink()
    return {'message_count': pending['message_count'], 'manifest': pending['manifest'],
            'cursor': pending['state']['cursor'], 'network': False}


def run(settings, root, command, start=None, token=None):
    if root is None:
        raise CollectError('--output required')
    safe(root, 'state.json')
    if command == 'status':
        lock = safe(root, 'lock.json')
        return {'recovery_required': safe(root, 'pending.json').exists(),
                'lock_token': json.loads(lock.read_text())['token'] if lock.exists() else None}
    if command == 'recover':
        lock = safe(root, 'lock.json')
        if not lock.exists() or json.loads(lock.read_text())['token'] != token:
            raise CollectError('exact lock token required; confirm original writer stopped')
        read_state(root, settings)
        path = safe(root, 'pending.json')
        result = finish(root, json.loads(path.read_text(encoding='utf-8'))) if path.exists() else {'status': 'unlocked'}
        lock.unlink()
        return result
    with locked(root):
        if command == 'initialize':
            if safe(root, 'state.json').exists() or start not in ('now', 'history'):
                raise CollectError('new state and explicit --start now/history required')
            rows, raw = snapshot(settings)
            baseline = raw if settings['adapter'] == 'hermes-sqlite' else (rows[-1][0] if rows else 0)
            cursor = baseline if start == 'now' else 0
            atomic(safe(root, 'state.json'), encode(position_state(settings, rows, raw, cursor)))
            return {'status': 'initialized', 'cursor': cursor}
        state = read_state(root, settings)
        rows, raw = snapshot(settings)
        batch = build_batch(settings, rows, raw, state)
        atomic(safe(root, 'pending.json'), encode(batch))
        return finish(root, batch, inject=True)


def doctor(settings):
    result = {'adapter': settings['adapter'], 'implementation': 'local export; optional schema-gated Hermes read-only adapter',
            'prerequisites': ['explicit authorized export', 'literal profile/platform/conversation/thread/roles allowlist'],
            'support': ['local source files for explicit file-channel ingest'],
            'real_message_integration': 'unverified', 'network': False, 'model_calls': False,
            'schedule_created': False, 'writes': []}
    if settings['adapter'] == 'hermes-sqlite':
        try:
            with closing(connect_db(settings)) as connection:
                result['schema'] = 'supported' if schema_supported(connection) else 'unsupported'
        except (OSError, sqlite3.Error, CollectError):
            result['schema'] = 'unavailable'
        result['prerequisites'].extend(['existing Hermes authorized bot DM receipt chain',
                                        'exact nonnull profile metadata', 'supported schema'])
        result['support'] = ['Telegram/Weixin bot DM history already received by Hermes; not arbitrary account login']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('command', choices=['template', 'doctor', 'preview', 'initialize', 'collect', 'status', 'recover'])
    parser.add_argument('--start', choices=['now', 'history'])
    parser.add_argument('--token')
    args = parser.parse_args()
    try:
        if args.command == 'template':
            result = template()
        else:
            if args.config is None:
                raise CollectError('--config required')
            settings = config(args.config)
            if args.command == 'doctor':
                result = doctor(settings)
            elif args.command == 'preview':
                rows, _ = snapshot(settings)
                result = {'message_count': len(selected(settings, rows)), 'writes': [], 'network': False}
            else:
                result = run(settings, args.output, args.command, args.start, args.token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (CollectError, OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        print(json.dumps({'error': 'collection_failed; check local schema, scope, and recovery state'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
