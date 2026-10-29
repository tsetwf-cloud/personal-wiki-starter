#!/usr/bin/env python3
"""Verify Personal Wiki skill metadata and isolated Skills CLI installs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SKILL = "personal-wiki"
REQUIRED = (
    "SKILL.md",
    "scripts/wiki.py",
    "scripts/collect.py",
    "scripts/review_notice.py",
    "references/cli.md",
    "examples/walkthrough.py",
    "agents/openai.yaml",
    "distribution-manifest.json",
)


def check_copy(root: Path) -> list[str]:
    return [name for name in REQUIRED if not (root / name).is_file()]


def check_manifest(root: Path) -> list[str]:
    manifest_path = root / "distribution-manifest.json"
    if not manifest_path.is_file():
        return ["distribution-manifest.json"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    expected = set(manifest["files"])
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != expected | {"distribution-manifest.json"}:
        failures.append("file-set")
    for relative, expected_hash in manifest["sha256"].items():
        path = root / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            failures.append(relative)
    return failures


def run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / "distribution-manifest.json").is_file() and (source / "skills" / SKILL).is_dir():
        source = source / "skills" / SKILL

    missing = check_copy(source)
    manifest_failures = check_manifest(source)
    result: dict[str, object] = {
        "skill": SKILL,
        "source": str(source),
        "static_only": args.static_only,
        "missing": missing,
        "manifest_failures": manifest_failures,
    }
    if missing or manifest_failures:
        result["status"] = "failed"
        print(json.dumps(result, ensure_ascii=False))
        return 1

    skill_text = (source / "SKILL.md").read_text(encoding="utf-8")
    if "name: personal-wiki" not in skill_text or 'version: "0.2.0-rc.2"' not in skill_text:
        result["status"] = "failed"
        result["error"] = "unexpected skill name or version"
        print(json.dumps(result, ensure_ascii=False))
        return 1

    if args.static_only:
        result["status"] = "ok"
        print(json.dumps(result, ensure_ascii=False))
        return 0

    npx = shutil.which("npx")
    if not npx:
        result["status"] = "blocked"
        result["error"] = "npx is not available"
        print(json.dumps(result, ensure_ascii=False))
        return 2

    with tempfile.TemporaryDirectory(prefix="personal_wiki_install_") as temp_name:
        temp = Path(temp_name)
        home = temp / "home"
        project = temp / "project"
        npm_cache = temp / "npm-cache"
        home.mkdir()
        project.mkdir()
        npm_cache.mkdir()
        env = {
            "HOME": str(home),
            "PATH": str(Path(npx).parent) + os.pathsep + os.environ.get("PATH", ""),
            "TMPDIR": str(temp),
            "npm_config_cache": str(npm_cache),
            "CLAUDE_CONFIG_DIR": str(home / ".claude"),
            "CODEX_HOME": str(home / ".codex"),
            "HERMES_HOME": str(home / ".hermes"),
        }
        command = [
            npx,
            "--yes",
            "skills@1.7.4",
            "add",
            str(source),
            "--agent",
            "codex",
            "claude-code",
            "hermes-agent",
            "--skill",
            SKILL,
            "--copy",
            "-y",
            "--json",
        ]
        completed = run(command, project, env)
        result["installer_returncode"] = completed.returncode
        if completed.returncode:
            result["status"] = "failed"
            result["stderr"] = completed.stderr[-4000:]
            result["stdout"] = completed.stdout[-4000:]
            print(json.dumps(result, ensure_ascii=False))
            return 1

        installed = {
            "shared": project / ".agents" / "skills" / SKILL,
            "claude": project / ".claude" / "skills" / SKILL,
            "hermes": project / ".hermes" / "skills" / SKILL,
        }
        copy_results = {
            name: check_copy(path) + check_manifest(path) for name, path in installed.items()
        }
        result["installed"] = {name: str(path) for name, path in installed.items()}
        result["copy_missing"] = copy_results
        if any(copy_results.values()):
            result["status"] = "failed"
            print(json.dumps(result, ensure_ascii=False))
            return 1

        package = installed["shared"]
        tests = run(["python3", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], package, env)
        result["tests_returncode"] = tests.returncode
        if tests.returncode:
            result["status"] = "failed"
            result["test_stderr"] = tests.stderr[-4000:]
            print(json.dumps(result, ensure_ascii=False))
            return 1

        walkthrough_dir = temp / "fictional-wiki"
        walkthrough = run(
            ["python3", "-B", "examples/walkthrough.py", "--output", str(walkthrough_dir)],
            package,
            env,
        )
        result["walkthrough_returncode"] = walkthrough.returncode
        if walkthrough.returncode:
            result["status"] = "failed"
            result["walkthrough_stderr"] = walkthrough.stderr[-4000:]
            print(json.dumps(result, ensure_ascii=False))
            return 1

    result["status"] = "ok"
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
