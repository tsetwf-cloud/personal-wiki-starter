"""Keep the portable template and optional native skill installs identical."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortableAssetsTests(unittest.TestCase):
    def test_blank_wiki_includes_identical_portable_skills(self):
        for source in sorted((ROOT / 'skills').glob('*/SKILL.md')):
            with self.subTest(skill=source.parent.name):
                target = ROOT / 'templates/wiki/wiki_skills' / source.parent.name / 'SKILL.md'
                self.assertTrue(target.is_file(), str(target.relative_to(ROOT)))
                self.assertEqual(source.read_bytes(), target.read_bytes())

    def test_portable_skills_explain_equivalent_tools(self):
        for source in sorted((ROOT / 'skills').glob('*/SKILL.md')):
            text = source.read_text(encoding='utf-8')
            self.assertIn('工具适配', text)
            self.assertIn('Claude Code', text)
            self.assertIn('Codex', text)


if __name__ == '__main__':
    unittest.main()
