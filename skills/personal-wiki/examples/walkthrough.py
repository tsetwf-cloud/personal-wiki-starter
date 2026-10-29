#!/usr/bin/env python3
"""Execute a fictional deterministic workflow, not an LLM extraction demo."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def walkthrough(output):
    output.mkdir(parents=True, exist_ok=False)
    cli = Path(__file__).resolve().parents[1] / 'scripts/wiki.py'
    root = output / 'wiki'
    transcript = []

    def run(*args):
        p = subprocess.run([sys.executable, '-B', str(cli), '--root', str(root), *args], text=True, encoding='utf-8', capture_output=True)
        if p.returncode:
            raise RuntimeError(p.stderr)
        result = json.loads(p.stdout)
        transcript.append({'args': list(args), 'result': result})
        return result

    def data_file(name, value):
        path = output / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

    run('doctor')
    run('init')
    run('configure', '--channels', 'file', '--scope', 'Only this fictional note; no live data', '--model-permission', 'none')
    note = output / 'fictional-note.txt'
    note.write_text('虚构人物林舟自述：我计划每周六留一小时读书，目前只是试行计划。\n', encoding='utf-8')
    source = run('ingest', '--file', str(note), '--channel', 'file', '--scope', 'Only fictional-note.txt', '--date', '2026-01-02')
    sid = source['source_id']
    proposal = {'source_id': sid, 'claim_key': 'weekly-reading-trial', 'kind': 'plan', 'quote': '我计划每周六留一小时读书，目前只是试行计划', 'text': '# 阅读安排\n\n林舟的自述试行计划：每周六留一小时读书，尚未确认持续执行。', 'target': '02-生活/阅读.md', 'sensitive': False, 'operation': 'create', 'expected_hash': None}
    submitted = run('submit', '--file', data_file('fictional-candidates.json', {'candidates': [proposal]}))
    cid = submitted['candidate_ids'][0]
    # Fixed fictional user approval; never an inference from a real user message.
    run('decide', '--file', data_file('fictional-approval.json', {'decisions': [{'id': cid, 'action': 'approve', 'approve_structure': True}]}))
    duplicate = run('ingest', '--file', str(note), '--channel', 'file', '--scope', 'Same explicitly selected fictional file', '--date', '2026-01-02')
    context = run('context', '--query', '阅读')
    checked = run('check')
    result = {'fictional_only': True, 'source_id': sid, 'candidate_id': cid, 'duplicate': duplicate, 'context': context, 'check': checked}
    (output / 'execution.json').write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Must not already exist')
    args = parser.parse_args()
    print(json.dumps(walkthrough(args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
