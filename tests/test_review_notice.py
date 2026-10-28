"""Synthetic candidate snapshots; no host Wiki or delivery endpoints."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/review_notice.py'


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.base = Path(self.tmp.name)
        self.snapshot = self.base / 'candidates.json'
        self.output = self.base / 'notice.json'
        self.item = {'id': 'a' * 64, 'status': 'pending', 'text': '虚构阅读安排',
                     'target': '02-生活/阅读.md', 'kind': 'plan', 'sensitive': True,
                     'operation': 'create', 'source_id': 'b' * 64}
        self.snapshot.write_text(json.dumps({'candidates': {self.item['id']: self.item}}), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, '-B', str(CLI), '--snapshot', str(self.snapshot), *args],
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0)
        return p

    def test_local_notice_has_content_destination_and_item_copy_approval(self):
        preview = self.cli('preview')
        self.assertFalse(self.output.exists())
        self.assertFalse(preview['sent'])
        item = preview['items'][0]
        self.assertEqual(item['content'], self.item['text'])
        self.assertEqual(item['destination'], self.item['target'])
        self.assertIn(self.item['id'], item['copy_approval'])
        self.assertIn('敏感', item['copy_approval'])
        self.assertTrue(item['decision']['approve_sensitive'])
        self.assertTrue(item['decision']['approve_structure'])
        self.assertEqual(item['decision']['action'], 'approve')
        self.cli('render', '--output', str(self.output))
        self.assertEqual(json.loads(self.output.read_text(encoding='utf-8')), preview)
        self.cli('render', '--output', str(self.output), ok=False)

    def test_only_pending_items_and_template_doctor_are_honest(self):
        other = dict(self.item, id='c' * 64, status='approved')
        self.snapshot.write_text(json.dumps({'candidates': {self.item['id']: self.item, other['id']: other}}), encoding='utf-8')
        self.assertEqual(len(self.cli('preview')['items']), 1)
        report = self.cli('doctor')
        self.assertFalse(report['network'])
        self.assertEqual(report['delivery'], 'not implemented')
        self.assertFalse(report['schedule_created'])


if __name__ == '__main__':
    unittest.main()
