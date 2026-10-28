#!/usr/bin/env python3
"""Local personal Wiki core; Python 3.10+, standard library only."""
import argparse
import base64
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import uuid

CATEGORIES = ['00-基础信息', '01-认知', '02-生活', '03-工作', '04-创业', '99-收件箱']

class WikiError(Exception):
    pass

def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def digest(body):
    return hashlib.sha256(body).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def safe(root, relative):
    p = PurePosixPath(relative)
    if not relative or p.is_absolute() or '\\' in relative or any(s in ('', '.', '..') for s in relative.split('/')):
        raise WikiError('unsafe relative path: ' + relative)
    root = root.absolute()
    for part in (root, *root.parents):
        if part.is_symlink():
            raise WikiError('symlink in root path')
    target = root.joinpath(*p.parts)
    walk = root
    for part in p.parts:
        walk = walk / part
        if walk.is_symlink():
            raise WikiError('symlink path: ' + relative)
    return target

def atomic(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('xb') as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def init(root):
    safe(root, '.wiki/state.json')
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise WikiError('init requires a nonexistent or empty nonsymlink directory')
    root.mkdir(parents=True, exist_ok=True)
    for name in CATEGORIES:
        (root / name).mkdir()
    atomic(root / '.wiki/state.json', dump({'version': 1, 'config': {}, 'sources': {}, 'candidates': {}}))
    return {'status': 'initialized', 'root': str(root.absolute()), 'categories': CATEGORIES}

def inspect(root):
    safe(root, '.wiki/state.json')
    issues = []
    if not root.is_dir():
        issues.append('existing directory required')
    elif safe(root, '.wiki').exists():
        issues.append('.wiki already exists; use status instead')
    else:
        for category in CATEGORIES:
            if not safe(root, category).is_dir():
                issues.append('missing category: ' + category)
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                if (Path(directory) / name).is_symlink():
                    issues.append('symlink: ' + (Path(directory) / name).relative_to(root).as_posix())
    return {'root': str(root.absolute()), 'categories': CATEGORIES, 'can_adopt': not issues, 'issues': issues, 'writes': []}

def adopt(root, args):
    report = inspect(root)
    if not report['can_adopt'] or args.confirm_root != str(root.absolute()):
        raise WikiError('adoption requires a compatible tree and exact absolute root confirmation')
    state_dir = safe(root, '.wiki')
    state_dir.mkdir(exist_ok=False)
    atomic(state_dir / 'state.json', dump({'version': 1, 'config': {}, 'sources': {}, 'candidates': {}, 'adopted': now()}))
    return {'status': 'adopted', 'root': str(root.absolute()), 'existing_pages_modified': False}

def load(root):
    path = safe(root, '.wiki/state.json')
    if not path.is_file():
        raise WikiError('not an initialized Wiki')
    return json.loads(path.read_text(encoding='utf-8'))

@contextmanager
def locked(root):
    load(root)
    path = safe(root, '.wiki/lock.json')
    token = uuid.uuid4().hex
    try:
        with path.open('xb') as f:
            f.write(dump({'token': token, 'created': now(), 'pid': os.getpid()}))
    except FileExistsError:
        raise WikiError('locked; inspect status and recover only with explicit exact token')
    try:
        if safe(root, '.wiki/journal.json').exists():
            raise WikiError('journal requires recovery')
        yield token
    finally:
        if not safe(root, '.wiki/journal.json').exists():
            path.unlink(missing_ok=True)

def replay(root, journal, inject=False):
    # Validate every destination before any roll-forward mutation.
    for entry in journal['writes']:
        path = safe(root, entry['path'])
        body = base64.b64decode(entry['body'], validate=True)
        current = digest(path.read_bytes()) if path.exists() else None
        if current not in (entry['old_hash'], digest(body)):
            raise WikiError('recovery conflict: ' + entry['path'])
    for i, entry in enumerate(journal['writes'], 1):
        path = safe(root, entry['path'])
        current = digest(path.read_bytes()) if path.exists() else None
        body = base64.b64decode(entry['body'], validate=True)
        if current not in (entry['old_hash'], digest(body)):
            raise WikiError('recovery conflict: ' + entry['path'])
        if current != digest(body):
            atomic(path, body)
        if inject and os.environ.get('WIKI_FAIL_AFTER') == str(i):
            os._exit(86)
    safe(root, '.wiki/journal.json').unlink()

def transaction(root, token, writes, event):
    writes = dict(writes)
    paths = [PurePosixPath(rel) for rel in writes]
    for i, path in enumerate(paths):
        destination = safe(root, str(path))
        if destination.exists() and not destination.is_file():
            raise WikiError('write destination is not a regular file: ' + str(path))
        for parent in destination.parents:
            if parent == root:
                break
            if parent.exists() and not parent.is_dir():
                raise WikiError('write parent is not a directory: ' + str(path))
        for other in paths[i + 1:]:
            if path in other.parents or other in path.parents:
                raise WikiError('ancestor/descendant write target conflict')
    audit = safe(root, '.wiki/events.jsonl')
    writes['.wiki/events.jsonl'] = (audit.read_bytes() if audit.exists() else b'') + json.dumps({'at': now(), 'token': token, **event}, ensure_ascii=False).encode() + b'\n'
    entries = []
    for rel, body in writes.items():
        path = safe(root, rel)
        old = path.read_bytes() if path.exists() else None
        if old is not None:
            backup = '.wiki/backups/' + token + '/' + rel
            atomic(safe(root, backup), old)
        entries.append({'path': rel, 'old_hash': digest(old) if old is not None else None, 'body': base64.b64encode(body).decode()})
    journal = {'token': token, 'writes': entries}
    atomic(safe(root, '.wiki/journal.json'), dump(journal))
    replay(root, journal, inject=True)

def doctor():
    return {'core': {'status': 'verified' if sys.version_info >= (3, 10) else 'unsupported', 'python': sys.version.split()[0]},
            'agent_host': {'status': 'unverified', 'reason': 'Host file/command tools and consent behavior require a real host test'},
            'channels': {name: {'status': 'verified' if name in ('current', 'file') else 'unsupported',
                                 'implementation': 'explicit file intake' if name in ('current', 'file') else 'manual export only; no live adapter shipped'}
                         for name in ('current', 'file', 'wechat', 'telegram', 'history')},
            'automation': {'status': 'unverified', 'enabled': False}}

def configure(root, args, token):
    state = load(root)
    channels = args.channels.split(',')
    if not channels or any(c not in ('current', 'file') for c in channels) or not args.scope.strip():
        raise WikiError('Only explicit current/file intake is supported; export other channels manually')
    state['config'] = {'channels': list(dict.fromkeys(channels)), 'scope': args.scope,
                       'model_permission': args.model_permission, 'schedule': 'manual'}
    transaction(root, token, {'.wiki/state.json': dump(state)}, {'action': 'configure'})
    return {'config': state['config']}

def ingest(root, args, token):
    state = load(root)
    if args.channel not in state['config'].get('channels', []) or not args.scope.strip():
        raise WikiError('channel/scope not authorized; configure first')
    date.fromisoformat(args.date)
    if args.file.is_symlink() or not args.file.is_file():
        raise WikiError('source must be an explicit regular nonsymlink file')
    body = args.file.read_bytes()
    if not body:
        raise WikiError('empty source')
    sid = digest(body)
    if sid in state['sources']:
        src = state['sources'][sid]
        if digest(safe(root, src['archive']).read_bytes()) != sid:
            raise WikiError('archived source corrupted')
        return {'status': 'duplicate', 'source_id': sid, 'source': src}
    archive = '99-收件箱/原始资料/' + sid + '.bin'
    src = {'archive': archive, 'sha256': sid, 'original_name': args.file.name, 'channel': args.channel, 'scope': args.scope, 'material_date': args.date, 'received': now()}
    state['sources'][sid] = src
    if safe(root, archive).exists():
        raise WikiError('unindexed archive collision')
    transaction(root, token, {archive: body, '.wiki/state.json': dump(state)}, {'action': 'ingest', 'source_id': sid})
    return {'status': 'archived', 'source_id': sid, 'source': src}

def target_path(root, relative):
    path = safe(root, relative)
    p = PurePosixPath(relative)
    if len(p.parts) < 2 or p.parts[0] not in CATEGORIES[:5] or p.suffix != '.md' or any(s.startswith('.') for s in p.parts):
        raise WikiError('formal target must be a nonhidden .md page in an approved category')
    if any(':' in s or s.endswith((' ', '.')) or s.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))} for s in p.parts):
        raise WikiError('reserved or nonportable path')
    return path

def review_bytes(item):
    return ('# Candidate ' + item['id'] + '\n\n' + json.dumps(item, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def submit(root, args, token):
    state = load(root)
    payload = json.loads(args.file.read_text(encoding='utf-8'))
    items = payload['candidates']
    if not isinstance(items, list) or not items:
        raise WikiError('nonempty candidates array required')
    writes, ids = {}, []
    required = {'source_id', 'claim_key', 'kind', 'quote', 'text', 'target', 'sensitive', 'operation', 'expected_hash'}
    for item in items:
        if not isinstance(item, dict) or set(item) != required:
            raise WikiError('candidate fields must exactly match schema')
        if any(not isinstance(item[k], str) or not item[k].strip() for k in ('source_id', 'claim_key', 'kind', 'quote', 'text', 'target', 'operation')):
            raise WikiError('required strings cannot be blank')
        if item['kind'] not in ('fact', 'judgment', 'plan', 'decision', 'conflict') or type(item['sensitive']) is not bool:
            raise WikiError('invalid kind/sensitive')
        src = state['sources'][item['source_id']]
        body = safe(root, src['archive']).read_bytes()
        if digest(body) != item['source_id'] or item['quote'] not in body.decode('utf-8'):
            raise WikiError('quote not in verified UTF-8 source')
        target = target_path(root, item['target'])
        cid = digest(dump([item['source_id'], item['claim_key']]))
        # A changed model-generated claim key cannot revive the same rejected evidence/target.
        for existing_id, existing in state['candidates'].items():
            if existing['status'] == 'rejected' and all(existing[k] == item[k] for k in ('source_id', 'quote')):
                cid = existing_id
                break
        if cid in state['candidates']:
            previous = state['candidates'][cid]
            if previous['status'] == 'pending' and any(previous[k] != item[k] for k in required):
                raise WikiError('candidate identity collision; edit via explicit decision, or reject and use distinct evidence')
            ids.append(cid)
            continue
        if item['operation'] == 'create':
            if item['expected_hash'] is not None or target.exists():
                raise WikiError('create cannot overwrite an existing page')
        elif item['operation'] == 'replace':
            if not target.is_file() or item['expected_hash'] != digest(target.read_bytes()):
                raise WikiError('replace requires exact current page hash')
        else:
            raise WikiError('operation must be create or replace')
        ids.append(cid)
        review = '99-收件箱/待审核/' + cid + '.md'
        record = {**item, 'id': cid, 'status': 'pending', 'review': review, 'created': now()}
        state['candidates'][cid] = record
        writes[review] = review_bytes(record)
    writes['.wiki/state.json'] = dump(state)
    transaction(root, token, writes, {'action': 'submit', 'candidate_ids': ids})
    return {'candidate_ids': ids, 'statuses': {cid: state['candidates'][cid]['status'] for cid in ids}}

def render_page(root, item, text):
    source = item['source_id']
    old_sources = []
    target = target_path(root, item['target'])
    if target.exists():
        lines = target.read_text(encoding='utf-8').splitlines()
        if lines[:1] == ['---']:
            for line in lines[1:]:
                if line == '---':
                    break
                if line.startswith('sources: '):
                    old_sources = json.loads(line[len('sources: '):])
    sources = list(dict.fromkeys([*old_sources, source]))
    header = ['---', 'updated: ' + now(), 'sources: ' + json.dumps(sources),
              'candidate_id: ' + item['id'], 'kind: ' + item['kind'],
              'material_date: ' + load(root)['sources'][source]['material_date'],
              'sensitive: ' + str(item['sensitive']).lower(), '---', '']
    return ('\n'.join(header) + text.rstrip() + '\n').encode('utf-8')

def decide(root, args, token):
    state = load(root)
    decisions = json.loads(args.file.read_text(encoding='utf-8'))['decisions']
    if not isinstance(decisions, list) or not decisions:
        raise WikiError('nonempty decisions array required')
    writes, seen, targets = {}, set(), set()
    rejected_evidence = {(c['source_id'], c['quote']) for c in state['candidates'].values() if c['status'] == 'rejected'}
    allowed = {'id', 'action', 'approve_structure', 'approve_sensitive', 'approve_replace', 'text', 'reason'}
    for decision in decisions:
        if not isinstance(decision, dict) or not set(decision) <= allowed:
            raise WikiError('invalid decision fields')
        cid, action = decision['id'], decision['action']
        if cid in seen:
            raise WikiError('duplicate decision ID')
        seen.add(cid)
        item = state['candidates'][cid]
        if item['status'] != 'pending':
            if (action == 'approve' and item['status'] == 'approved') or (action == 'reject' and item['status'] == 'rejected'):
                continue
            raise WikiError('resolved candidate cannot be revived')
        if action == 'approve':
            if (item['source_id'], item['quote']) in rejected_evidence:
                raise WikiError('same source evidence was rejected; queued duplicate cannot revive it')
            if item['sensitive'] and decision.get('approve_sensitive') is not True:
                raise WikiError('per-item sensitive approval required')
            target = target_path(root, item['target'])
            src = state['sources'][item['source_id']]
            if digest(safe(root, src['archive']).read_bytes()) != item['source_id']:
                raise WikiError('source integrity failed')
            if item['operation'] == 'create':
                if target.exists():
                    raise WikiError('create target now exists; submit a replacement conflict candidate')
                if decision.get('approve_structure') is not True:
                    raise WikiError('explicit new-path structure approval required')
            else:
                if decision.get('approve_replace') is not True:
                    raise WikiError('explicit whole-page replacement approval required')
                if not target.is_file() or digest(target.read_bytes()) != item['expected_hash']:
                    raise WikiError('stale target hash; re-read and resolve conflict')
            if item['target'] in targets:
                raise WikiError('multiple writes to one target: consolidate into one reviewed replacement')
            targets.add(item['target'])
            text = decision.get('text', item['text'])
            if not isinstance(text, str) or not text.strip():
                raise WikiError('approved text cannot be blank')
            writes[item['target']] = render_page(root, item, text)
            item.update(status='approved', approved_text=text, resolved=now(), decision=decision)
        elif action == 'reject':
            item.update(status='rejected', resolved=now(), decision=decision)
        elif action == 'later':
            item['decision'] = decision
        else:
            raise WikiError('action must be approve, reject or later')
        writes[item['review']] = review_bytes(item)
    writes['.wiki/state.json'] = dump(state)
    transaction(root, token, writes, {'action': 'decide', 'decisions': decisions})
    return {'decided_ids': list(seen), 'pending_ids': [cid for cid, c in state['candidates'].items() if c['status'] == 'pending'],
            'approved_ids': [cid for cid, c in state['candidates'].items() if c['status'] == 'approved'],
            'rejected_ids': [cid for cid, c in state['candidates'].items() if c['status'] == 'rejected']}

def formal_pages(root):
    load(root)
    if safe(root, '.wiki/lock.json').exists() or safe(root, '.wiki/journal.json').exists():
        raise WikiError('Wiki busy or recovery required; do not read a partial snapshot')
    for category in CATEGORIES[:5]:
        base = safe(root, category)
        for directory, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                if name.endswith('.md') and not name.startswith('.'):
                    path = Path(directory) / name
                    rel = path.relative_to(root).as_posix()
                    yield rel, target_path(root, rel).read_bytes().decode('utf-8')

def source_ids(text):
    if text.startswith('---\n'):
        for line in text.split('\n')[1:]:
            if line == '---':
                break
            if line.startswith('sources: '):
                ids = json.loads(line[len('sources: '):])
                if not isinstance(ids, list) or any(not isinstance(s, str) for s in ids):
                    raise WikiError('invalid sources metadata')
                return ids
    return []

def context(root, args):
    state, pages = load(root), []
    for rel, text in formal_pages(root):
        if args.query.casefold() not in (rel + '\n' + text).casefold():
            continue
        evidence = []
        for sid in source_ids(text):
            src = state['sources'][sid]
            if digest(safe(root, src['archive']).read_bytes()) != sid:
                raise WikiError('source integrity failed')
            evidence.append({'archive': src['archive'], 'sha256': sid, 'material_date': src['material_date']})
        pages.append({'path': rel, 'sha256': digest(text.encode('utf-8')), 'text': text, 'evidence': evidence})
    return {'pages': pages, 'boundary': 'formal pages only; evidence metadata not raw source bodies'}

def check(root):
    state, issues, paths = load(root), [], []
    for rel, text in formal_pages(root):
        paths.append(rel)
        ids = source_ids(text)
        if not ids:
            issues.append({'path': rel, 'issue': 'missing sources metadata'})
        for sid in ids:
            src = state['sources'].get(sid)
            if not src or not safe(root, src['archive']).is_file() or digest(safe(root, src['archive']).read_bytes()) != sid:
                issues.append({'path': rel, 'issue': 'missing or corrupt evidence', 'source_id': sid})
        for link in re.findall(r'\]\(([^)]+)\)', text):
            link = link.split('#')[0]
            if not link or '://' in link or link.startswith('mailto:'):
                continue
            try:
                destination = (PurePosixPath(rel).parent / link).as_posix()
                if not safe(root, destination).is_file():
                    issues.append({'path': rel, 'issue': 'broken link', 'target': link})
            except WikiError:
                issues.append({'path': rel, 'issue': 'unsafe link', 'target': link})
    return {'status': 'issues' if issues else 'ok', 'checked_paths': paths, 'issues': issues, 'excluded': ['99-收件箱', '.wiki']}

def status(root):
    state = load(root)
    lock = safe(root, '.wiki/lock.json')
    return {**state, 'recovery_required': safe(root, '.wiki/journal.json').exists(), 'lock_token': json.loads(lock.read_text())['token'] if lock.exists() else None}

def recover(root, args):
    lock = safe(root, '.wiki/lock.json')
    if not lock.exists() or json.loads(lock.read_text())['token'] != args.token:
        raise WikiError('exact lock token required')
    path = safe(root, '.wiki/journal.json')
    if path.exists():
        journal = json.loads(path.read_text(encoding='utf-8'))
        if journal['token'] != args.token:
            raise WikiError('journal token mismatch')
        replay(root, journal)
    lock.unlink()
    return {'status': 'recovered'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init', help='Create only in an empty/new directory')
    commands.add_parser('doctor', help='Report capabilities; does not touch the Wiki')
    commands.add_parser('status', help='Inspect exact IDs, pending state and recovery token')
    recovery = commands.add_parser('recover', help='Explicit roll-forward after confirming the writer has stopped')
    recovery.add_argument('--token', required=True)
    config = commands.add_parser('configure', help='Save explicit source/model scope; manual only')
    config.add_argument('--channels', required=True)
    config.add_argument('--scope', required=True)
    config.add_argument('--model-permission', choices=['local', 'remote', 'none'], required=True)
    intake = commands.add_parser('ingest', help='Archive one explicitly authorized file without changing its bytes')
    intake.add_argument('--file', type=Path, required=True)
    intake.add_argument('--channel', choices=['current', 'file'], required=True)
    intake.add_argument('--scope', required=True)
    intake.add_argument('--date', required=True)
    submission = commands.add_parser('submit', help='Validate Agent-extracted candidates; never writes formal pages')
    submission.add_argument('--file', type=Path, required=True)
    decision = commands.add_parser('decide', help='Apply explicit per-ID approval/edit/reject/later decisions atomically recoverably')
    decision.add_argument('--file', type=Path, required=True)
    commands.add_parser('check', help='Check formal pages only, excluding backups and raw materials')
    retrieval = commands.add_parser('context', help='Read formal knowledge and verified evidence metadata only')
    retrieval.add_argument('--query', default='')
    commands.add_parser('inspect', help='Read-only compatibility check of an existing library')
    adoption = commands.add_parser('adopt', help='Create state only after exact path confirmation; preserve existing knowledge')
    adoption.add_argument('--confirm-root', required=True)
    args = parser.parse_args()
    args.root = args.root.absolute()
    try:
        if args.command in ('init', 'doctor', 'status', 'recover', 'check', 'context', 'inspect', 'adopt'):
            result = {'init': lambda: init(args.root), 'doctor': doctor, 'status': lambda: status(args.root), 'recover': lambda: recover(args.root, args), 'check': lambda: check(args.root), 'context': lambda: context(args.root, args), 'inspect': lambda: inspect(args.root), 'adopt': lambda: adopt(args.root, args)}[args.command]()
        else:
            with locked(args.root) as token:
                result = {'configure': configure, 'ingest': ingest, 'submit': submit, 'decide': decide}[args.command](args.root, args, token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (WikiError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
