"""Guard against the encoding bug recurring: every tool that prints must be safe.

This has now happened three times in this repo: a script prints Chinese, the
Windows console decodes as cp1252/cp936, and the script dies with
UnicodeEncodeError - but only on Windows, so local runs pass and CI goes red.

Rather than rely on remembering to add the guard, this check enforces it:
any Python file under tools/ or plugins/ that calls print() with non-ASCII
text must carry the stdout/stderr reconfigure guard.
"""
import pathlib
import re
import sys

# -*- coding: utf-8 -*-
import io

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUARD_MARK = "_sys.stdout"
CJK = re.compile(r"[\u4e00-\u9fff]")

problems = []

for d in (ROOT / "tools", ROOT / "tests", *ROOT.glob("plugins/*/skills/*/scripts")):
    if not d.is_dir():
        continue
    for p in sorted(d.glob("*.py")):
        if p.name.startswith("_utf8"):
            continue
        text = p.read_text(encoding="utf-8")
        has_cjk_print = any(
            CJK.search(line) for line in text.splitlines() if "print(" in line
        ) or (CJK.search(text) and "print(" in text)
        if not has_cjk_print:
            continue
        if GUARD_MARK not in text:
            problems.append(str(p.relative_to(ROOT)))

print(f"检查了会打印中文的脚本，缺失 UTF-8 守卫的有 {len(problems)} 个")
for p in problems:
    print("  MISSING GUARD:", p)

if problems:
    print()
    print("这些脚本在 Windows 上会抛 UnicodeEncodeError（cp1252/cp936 无法编码中文）。")
    print("修复：在首个 import 之前加入")
    print('    import sys as _sys')
    print('    for _s in (_sys.stdout, _sys.stderr):')
    print('        if _s is not None and hasattr(_s, "reconfigure"):')
    print('            try: _s.reconfigure(encoding="utf-8", errors="replace")')
    print('            except Exception: pass')
    sys.exit(1)

print("全部安全。")
sys.exit(0)
