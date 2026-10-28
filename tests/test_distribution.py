import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]

class DistributionTests(unittest.TestCase):
    def test_fictional_walkthrough_executes_core_and_returns_checked_context(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            p = subprocess.run([sys.executable, '-B', str(PACKAGE / 'examples/walkthrough.py'), '--output', str(Path(temp) / 'demo')], text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            result = json.loads(p.stdout)
            self.assertEqual(result['check']['status'], 'ok')
            self.assertEqual(len(result['context']['pages']), 1)
            self.assertEqual(result['duplicate']['status'], 'duplicate')

    def test_distribution_has_real_procedure_license_and_no_host_dependency(self):
        skill = (PACKAGE / 'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(skill.startswith('---\n'))
        for marker in ['init', 'doctor', 'inspect', 'adopt', 'configure', 'ingest', 'submit', 'decide', 'recover', 'context', 'check', '未验证', '事实', '判断', '计划', '微信', 'Telegram']:
            self.assertIn(marker, skill)
        self.assertIn('tsetwf-cloud', (PACKAGE / 'LICENSE.personal-wiki').read_text())
        self.assertIn('MIT License', (PACKAGE / 'LICENSE').read_text())
        code = (PACKAGE / 'scripts/wiki.py').read_text()
        self.assertNotIn('import hermes', code)
        for document in ['README.md', 'references/boundaries.md', 'references/cli.md', 'references/channels.md']:
            self.assertTrue((PACKAGE / document).is_file(), document)
