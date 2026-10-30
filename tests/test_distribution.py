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

    def test_skill_metadata_supports_explicit_host_invocation(self):
        skill_text = (PACKAGE / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('name: personal-wiki', skill_text)
        self.assertIn('version: "0.2.0-rc.2"', skill_text)
        self.assertIn('platforms: [linux, macos, windows]', skill_text)
        self.assertIn('reviewed personal Wiki', skill_text)

        openai_text = (PACKAGE / 'agents/openai.yaml').read_text(encoding='utf-8')
        self.assertIn('$personal-wiki', openai_text)
        self.assertIn('allow_implicit_invocation: false', openai_text)

        plugin_path = PACKAGE / '.claude-plugin/plugin.json'
        marketplace_path = PACKAGE / '.claude-plugin/marketplace.json'
        if plugin_path.is_file() and marketplace_path.is_file():
            plugin = json.loads(plugin_path.read_text(encoding='utf-8'))
            marketplace = json.loads(marketplace_path.read_text(encoding='utf-8'))
            self.assertEqual(plugin['name'], 'personal-wiki')
            self.assertEqual(plugin['version'], '0.2.0-rc.2')
            self.assertEqual(plugin['skills'], ['./skills/personal-wiki'])
            self.assertEqual(marketplace['plugins'][0]['source'], './skills/personal-wiki')

    def test_reader_docs_lead_with_install_invoke_and_visible_result(self):
        readme = (PACKAGE / 'README.md').read_text(encoding='utf-8')
        for marker in ['三步开始使用', '什么时候用', '怎么说', '你会得到',
                       '显式调用', '$personal-wiki', '/personal-wiki', '/personal-wiki:personal-wiki',
                       '/skill personal-wiki', '命令没有出现', '正式知识']:
            self.assertIn(marker, readme)
        self.assertNotIn('不做宿主全局注册', readme)

    def test_install_verification_script_is_shipped(self):
        script = PACKAGE / 'scripts/verify_skill_install.py'
        self.assertTrue(script.is_file())
        p = subprocess.run(
            [sys.executable, '-B', str(script), '--source', str(PACKAGE), '--static-only'],
            text=True,
            capture_output=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['skill'], 'personal-wiki')
        self.assertEqual(result['status'], 'ok')
