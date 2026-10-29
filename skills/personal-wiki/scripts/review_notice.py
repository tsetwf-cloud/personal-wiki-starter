#!/usr/bin/env python3
"""Render a local-only review notice from an explicit Wiki status JSON snapshot."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys


def notice(snapshot):
    payload = json.loads(snapshot.read_text(encoding='utf-8'))
    candidates = payload['candidates']
    if not isinstance(candidates, dict):
        raise ValueError('candidate mapping required')
    items = []
    for cid, candidate in candidates.items():
        if candidate['status'] != 'pending':
            continue
        if not re.fullmatch('[0-9a-f]{64}', cid) or candidate['id'] != cid:
            raise ValueError('exact candidate ID required')
        if not isinstance(candidate['text'], str) or not candidate['text'].strip():
            raise ValueError('nonblank content required')
        if candidate['operation'] not in ('create', 'replace') or type(candidate['sensitive']) is not bool:
            raise ValueError('invalid candidate approval fields')
        target = candidate['target']
        p = PurePosixPath(target)
        if (not isinstance(target, str) or p.is_absolute() or '..' in p.parts or '\\' in target or
                len(p.parts) < 2 or p.suffix != '.md' or p.parts[0] not in
                ('00-基础信息', '01-认知', '02-生活', '03-工作', '04-创业')):
            raise ValueError('invalid formal destination')
        decision = {'id': cid, 'action': 'approve'}
        qualifications = []
        if candidate['sensitive']:
            decision['approve_sensitive'] = True
            qualifications.append('该项敏感内容')
        if candidate['operation'] == 'create':
            decision['approve_structure'] = True
            qualifications.append('新建该路径')
        else:
            decision['approve_replace'] = True
            qualifications.append('整页替换（须核对当前页及原哈希）')
        approval = '我逐项批准候选 ' + cid + ' 写入 ' + target + '，包括' + '、'.join(qualifications) + '。'
        items.append({'id': cid, 'content': candidate['text'], 'destination': target,
                      'kind': candidate['kind'], 'source_id': candidate['source_id'],
                      'sensitive': candidate['sensitive'], 'operation': candidate['operation'],
                      'copy_approval': approval, 'decision': decision})
    return {'version': 1, 'local_only': True, 'sent': False, 'notification_destination': 'local file/stdout only',
            'warning': 'This is not approval. Review full text, evidence, sensitivity and destination per item. '
                       'Copying text does not execute a decision; explicitly submit only selected decisions through wiki.py decide.',
            'items': items}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('command', choices=['doctor', 'preview', 'render'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            result = {'network': False, 'delivery': 'not implemented', 'schedule_created': False,
                      'support': 'explicit status JSON snapshot to local review notice only',
                      'real_message_integration': 'unverified', 'writes': []}
        else:
            if args.snapshot is None or args.snapshot.is_symlink():
                raise ValueError('explicit nonsymlink snapshot required')
            result = notice(args.snapshot)
            if args.command == 'render':
                if args.output is None:
                    raise ValueError('--output required')
                for node in (args.output, *args.output.absolute().parents):
                    if node.is_symlink():
                        raise ValueError('symlink output path')
                # Exclusive create never overwrites a previous review or candidate file.
                with args.output.open('xb') as handle:
                    handle.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
                    handle.flush()
                    os.fsync(handle.fileno())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'error': 'notice_failed; check explicit snapshot and unused local output path'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
