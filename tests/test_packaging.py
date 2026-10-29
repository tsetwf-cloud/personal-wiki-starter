import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills" / "personal-wiki"
FILES = ROOT / "distribution-files.json"


class PackagingTests(unittest.TestCase):
    def test_installable_package_is_exact_allowlisted_copy(self):
        manifest = json.loads(FILES.read_text(encoding="utf-8"))
        expected = set(manifest["files"])
        actual = {
            path.relative_to(PACKAGE).as_posix()
            for path in PACKAGE.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(actual, expected | {"distribution-manifest.json"})
        self.assertNotIn(".claude-plugin/plugin.json", actual)
        self.assertFalse(any(path.startswith("legacy/") for path in actual))

        built = json.loads((PACKAGE / "distribution-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(built["version"], "0.2.0-rc.2")
        self.assertEqual(set(built["files"]), expected)
        for relative in sorted(expected):
            source = ROOT / relative
            installed = PACKAGE / relative
            self.assertTrue(source.is_file(), relative)
            self.assertTrue(installed.is_file(), relative)
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(installed.read_bytes(), source.read_bytes(), relative)
            self.assertEqual(built["sha256"][relative], source_hash)

    def test_claude_plugin_exposes_only_current_personal_wiki(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["skills"], ["./skills/personal-wiki"])
        self.assertEqual(marketplace["plugins"][0]["source"], "./skills/personal-wiki")

    def test_public_install_uses_versioned_package_path(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        pinned = "https://github.com/tsetwf-cloud/personal-wiki-starter/tree/v0.2.0-rc.2/skills/personal-wiki"
        self.assertIn(pinned, readme)
        self.assertNotIn("add https://github.com/tsetwf-cloud/personal-wiki-starter \\", readme)


if __name__ == "__main__":
    unittest.main()
