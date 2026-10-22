"""CLI regression tests; fixtures never use a real wiki."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wiki_tool.py"
FILES = (
    "SCHEMA.md", "index.md", "log.md", "资料导入规范.md", "AGENTS.md",
    "00-基础信息/个人概况.md", "01-工作与项目/当前项目.md",
    "02-生活/时间安排与兴趣.md",
)
DIRECTORIES = (
    "99-收件箱/待导入", "99-收件箱/待审核",
    "99-收件箱/原始资料", "99-收件箱/处理记录",
)


class WikiToolTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get("TMPDIR")
        if not scratch or not Path(scratch).is_dir():
            self.fail("Set TMPDIR to an existing scratch directory before running tests")
        self.temp = tempfile.TemporaryDirectory(prefix="wiki-tool-test-", dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.template = self.base / "templates" / "wiki"
        self.template.mkdir(parents=True)
        for name in FILES:
            path = self.template / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Blank template\n", encoding="utf-8")
        for name in DIRECTORIES:
            (self.template / name).mkdir(parents=True)
        self.target = self.base / "new-wiki"

    def run_cli(self, command, root=None, template=None):
        args = [sys.executable, str(SCRIPT), command, "--root", str(root or self.target)]
        if command == "init":
            args += ["--template-root", str(template or self.template)]
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.stderr, "", result.stderr)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"Expected JSON stdout, received: {result.stdout!r}")
        self.assertIsInstance(data.get("ok"), bool)
        self.assertEqual(result.returncode, 0 if data["ok"] else 1)
        return data

    def snapshot(self, root):
        return {
            str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
            for path in root.rglob("*")
        }

    def test_check_reports_reference_and_angle_title_links(self):
        self.assertTrue(self.run_cli("init")["ok"])
        (self.target / "index.md").write_text(
            '[page][guide]\n[guide]: missing-reference.md "Guide"\n'
            '[page](<missing page.md> "Page")\n', encoding="utf-8")
        result = self.run_cli("check")
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        self.assertIn("missing-reference.md", errors)
        self.assertIn("missing page.md", errors)

    def test_check_accepts_valid_links_and_ignores_examples_and_external_urls(self):
        self.assertTrue(self.run_cli("init")["ok"])
        (self.target / "space page.md").write_text("# Page\n", encoding="utf-8")
        (self.target / "index.md").write_text(
            "[topic](00-基础信息/个人概况.md#heading)\n"
            "[space](space%20page.md)\n[space](<space page.md> \"Title\")\n"
            "[web](https://example.invalid/unreachable)\n"
            "[mail](mailto:example@example.invalid)\n[section](#heading)\n"
            "`[inline sample](never.md)`\n"
            "```markdown\n[example](never.md)\n```\n"
            "<!-- [commented](never.md) -->\n", encoding="utf-8")
        self.assertTrue(self.run_cli("check")["ok"])

    def test_cli_failures_are_json(self):
        self.assertFalse(self.run_cli("init", template=self.base / "absent")["ok"])
        self.assertFalse(self.target.exists())
        (self.template / "index.md").write_bytes(b"\xff")
        self.assertTrue(self.run_cli("init")["ok"])
        self.assertFalse(self.run_cli("check")["ok"])
        for arguments in ([], ["unknown"], ["check"], ["check", "--root", str(self.target), "--unknown"]):
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, str(SCRIPT), *arguments],
                                        capture_output=True, text=True)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.returncode, 1)
                self.assertFalse(json.loads(result.stdout)["ok"])

    def test_check_refuses_symlinks_without_following(self):
        self.assertTrue(self.run_cli("init")["ok"])
        alias = self.base / "wiki-alias"
        alias.symlink_to(self.target, target_is_directory=True)
        self.assertFalse(self.run_cli("check", root=alias)["ok"])
        outside = self.base / "outside.md"
        outside.write_bytes(b"\xff")
        (self.target / "linked.md").symlink_to(outside)
        self.assertFalse(self.run_cli("check")["ok"])
        (self.target / "linked.md").unlink()
        (self.target / "99-收件箱/原始资料/linked.md").symlink_to(outside)
        self.assertFalse(self.run_cli("check")["ok"])

    def test_check_does_not_read_raw_material_bodies(self):
        self.assertTrue(self.run_cli("init")["ok"])
        raw = self.target / "99-收件箱" / "原始资料"
        (raw / "invalid.md").write_bytes(b"\xff\xfe\x00")
        (raw / "source.md").write_text("[broken](never-exists.md)\n", encoding="utf-8")
        self.assertTrue(self.run_cli("check")["ok"])

    def test_check_reports_broken_relative_links_without_fixing(self):
        self.assertTrue(self.run_cli("init")["ok"])
        (self.target / "index.md").write_text(
            "[missing](missing.md)\n![image](assets/missing.png)\n"
            "[encoded](missing%20page.md#section)\n"
            "[escape](../outside.md)\n", encoding="utf-8")
        before = self.snapshot(self.target)
        result = self.run_cli("check")
        self.assertFalse(result["ok"])
        errors = "\n".join(result["errors"])
        for name in ("missing.md", "assets/missing.png", "missing%20page.md", "../outside.md"):
            self.assertIn(name, errors)
        self.assertIn("index.md", errors)
        self.assertEqual(before, self.snapshot(self.target))

    def test_check_reports_each_missing_required_file_or_directory(self):
        self.assertTrue(self.run_cli("init")["ok"])
        for name in (*FILES, *DIRECTORIES):
            with self.subTest(name=name):
                path = self.target / name
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                result = self.run_cli("check")
                self.assertFalse(result["ok"])
                self.assertIn(name, "\n".join(result["errors"]))
                if name in DIRECTORIES:
                    path.mkdir()
                else:
                    path.write_text("# Restored\n", encoding="utf-8")
        self.assertFalse(self.run_cli("check", root=self.base / "missing")["ok"])

    def test_check_accepts_complete_wiki_without_writing(self):
        self.assertTrue(self.run_cli("init")["ok"])
        before = self.snapshot(self.target)
        result = self.run_cli("check")
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(before, self.snapshot(self.target))

    def test_init_rejects_symbolic_links(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.base / "alias"
        link.symlink_to(outside, target_is_directory=True)
        dangling = self.base / "dangling"
        dangling.symlink_to(self.base / "absent", target_is_directory=True)
        for root in (link, link / "child", dangling):
            with self.subTest(root=root.name):
                self.assertFalse(self.run_cli("init", root=root)["ok"])
        source_alias = self.base / "template-alias"
        source_alias.symlink_to(self.template, target_is_directory=True)
        self.assertFalse(self.run_cli("init", template=source_alias)["ok"])
        (self.template / "hidden-link").symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.run_cli("init")["ok"])
        self.assertFalse(self.target.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_empty_target_is_allowed(self):
        self.target.mkdir()
        self.assertTrue(self.run_cli("init")["ok"])
        self.assertEqual(self.snapshot(self.target), self.snapshot(self.template))

    def test_second_init_refused_without_changes(self):
        self.assertTrue(self.run_cli("init")["ok"])
        before = self.snapshot(self.target)
        self.assertFalse(self.run_cli("init")["ok"])
        self.assertEqual(before, self.snapshot(self.target))

    def test_template_overlap_refused_without_changes(self):
        before = self.snapshot(self.template)
        for root in (self.template, self.template.parent, self.template / "child"):
            with self.subTest(root=root.name):
                self.assertFalse(self.run_cli("init", root=root)["ok"])
        self.assertEqual(before, self.snapshot(self.template))

    def test_nonempty_target_is_preserved(self):
        self.target.mkdir()
        (self.target / "private.md").write_bytes(b"private sentinel")
        before = self.snapshot(self.target)
        self.assertFalse(self.run_cli("init")["ok"])
        self.assertEqual(before, self.snapshot(self.target))

    def test_fresh_init_copies_entire_template(self):
        extra = self.template / "assets" / "empty"
        extra.mkdir(parents=True)
        (extra.parent / "example.bin").write_bytes(b"\x00\xff")
        result = self.run_cli("init")
        self.assertTrue(result["ok"])
        self.assertEqual(self.snapshot(self.target), self.snapshot(self.template))


if __name__ == "__main__":
    unittest.main()
