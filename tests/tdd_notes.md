# TDD verification notes

Run from the repository root with Python 3.10+ and an existing, writable scratch directory in `TMPDIR`:

```sh
python3 -m unittest discover -s tests -v
```

The tests refuse to run without `TMPDIR`; every fixture is created beneath it and removed afterward. No real wiki is used. There are no third-party dependencies.

## Observed red / green sequence

Each new behavior below was run before its implementation, then the complete suite was rerun after the minimal change. Failure summaries omit interpreter and machine paths.

| Slice | Observed RED | Observed GREEN |
| --- | --- | --- |
| Fresh init, full recursive copy | CLI entry point did not exist | 1 test OK |
| Preserve nonempty target | `True is not false` | 2 tests OK |
| Reject template parent/self/child overlap | Child target was accepted and changed the template fixture | 5 tests OK |
| Reject init symlinks | Linked targets and source alias accepted; dangling link raised a traceback | 6 tests OK |
| Read-only successful check | `check` was not a recognized command | 7 tests OK |
| Validate required files and directories | Missing required entries incorrectly returned success | 8 tests OK |
| Broken relative Markdown links | Broken links incorrectly returned success | 9 tests OK |
| Skip raw-material bodies | Invalid UTF-8 raw fixture caused a traceback | 10 tests OK |
| Reject symlinks during check | Linked wiki root incorrectly returned success | 11 tests OK |
| JSON failures | Missing template caused a traceback | 12 tests OK |
| Ignore code examples/comments; allow valid/external links | Example links caused false failures | 13 tests OK |
| Reference-definition links | Missing reference destination was absent from the error report | 14 tests OK |

Existing-empty-target and second-init tests were added as explicit regressions for the already implemented fresh/empty and nonempty rules; they passed on first run and are not presented as separate RED cycles.

## Final actual output

Python used for execution: **3.14.7**. Python 3.10 syntax compatibility is checked separately; a Python 3.10 interpreter was not used.

```text
Ran 14 tests in 3.508s

OK
```

A separate smoke run copied the actual repository `templates/wiki` into a temporary scratch fixture and checked that copy, using the default template path:

```text
REAL TEMPLATE INIT: {"ok": true, "command": "init", "errors": []}
REAL TEMPLATE CHECK: {"ok": true, "command": "check", "errors": []}
```

## Intentional scope

- `init --root PATH` copies the entire template; `--template-root` allows isolated test fixtures.
- `check --root PATH` reads Markdown outside `99-收件箱/原始资料`, validates the fixed structure, and reports relative link destinations that are missing or escape the root.
- Symlink metadata is inspected even beneath raw materials; their bodies are never opened by `check`.
- Link checks cover ordinary inline/image links, angle-bracket destinations, optional titles and reference definitions. This is a small standard-library checker, not a full CommonMark parser. Fragments and external URLs are not validated or fetched.
- Successful commands exit 0; failed commands exit 1. Both emit one JSON object. `--help` retains normal argparse help output.
- No AI extraction, approval, collection, network calls, scheduled tasks or automatic repairs are implemented.
