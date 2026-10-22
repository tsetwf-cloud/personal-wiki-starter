"""Zero-dependency entry point for a blank personal wiki (Python 3.10+)."""
import argparse
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit


REQUIRED_FILES = (
    "SCHEMA.md", "index.md", "log.md", "资料导入规范.md", "AGENTS.md",
    "00-基础信息/个人概况.md", "01-工作与项目/当前项目.md",
    "02-生活/时间安排与兴趣.md",
)
REQUIRED_DIRECTORIES = (
    "00-基础信息", "01-工作与项目", "02-生活",
    "99-收件箱/待导入", "99-收件箱/待审核",
    "99-收件箱/原始资料", "99-收件箱/处理记录",
)


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def reject_links(path, recursive=False):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Symbolic links are not allowed")
    if recursive:
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError("Symbolic links are not allowed")


def check_wiki(root):
    errors = []
    reject_links(root.absolute(), recursive=True)
    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            errors.append("Missing required file: " + name)
    for name in REQUIRED_DIRECTORIES:
        if not (root / name).is_dir():
            errors.append("Missing required directory: " + name)
    for page in sorted(root.rglob("*.md")):
        if Path("99-收件箱/原始资料") in page.relative_to(root).parents:
            continue
        text = page.read_text(encoding="utf-8")
        text = re.sub(r"<!--[\s\S]*?-->", "", text)
        text = re.sub(r"(?ms)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[ \t]*$", "", text)
        text = re.sub(r"(`+)[\s\S]*?\1", "", text)
        inline = re.finditer(r"!?\[[^\]\n]*\]\(\s*(<[^>\n]*>|[^\s)]+)(?:\s+[^)\n]*)?\)", text)
        references = re.finditer(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(<[^>\n]*>|\S+)", text)
        for match in (*inline, *references):
            link = match.group(1).strip("<>")
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (page.parent / unquote(parsed.path)).resolve()
            if (destination != root.resolve() and root.resolve() not in destination.parents
                    or not destination.exists()):
                errors.append(f"Broken relative link in {page.relative_to(root).as_posix()}: {link}")
    return errors


def init_wiki(root, template):
    reject_links(root.absolute())
    reject_links(template.absolute(), recursive=True)
    source = template.resolve()
    target = root.resolve()
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Target and template must not overlap")
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("Target must be new or empty")
    shutil.copytree(template, root, dirs_exist_ok=True)


def main():
    command = None
    try:
        parser = JsonParser(description=__doc__)
        parser.add_argument("command", choices=("init", "check"))
        parser.add_argument("--root", required=True, type=Path)
        parser.add_argument("--template-root", type=Path,
                            default=Path(__file__).resolve().parents[1] / "templates" / "wiki")
        args = parser.parse_args()
        command = args.command
        if command == "check":
            errors = check_wiki(args.root)
        else:
            init_wiki(args.root, args.template_root)
            errors = []
    except UnicodeError:
        errors = ["Markdown must be valid UTF-8"]
    except OSError as error:
        errors = [f"Filesystem operation failed ({type(error).__name__})"]
    except ValueError as error:
        errors = [str(error)]
    print(json.dumps({"ok": not errors, "command": command, "errors": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
