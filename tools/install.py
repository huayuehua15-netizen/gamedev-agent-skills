#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨平台安装器：把 dist/ 产物装到各宿主的技能目录。

Windows 用户也可以用 tools/install.ps1；本脚本在 Windows / macOS / Linux 都能跑。

用法：
    python tools/install.py --target cursor --path /path/to/project
    python tools/install.py --target trae   --path ~/.trae-cn/skills
    python tools/install.py --target generic --path ~/.config/agent/skills
    python tools/install.py --target zcode          # 只打印说明
    python tools/install.py --target claude         # 只打印说明
    python tools/install.py --list                  # 看有哪些 target
"""

import argparse
import shutil
import sys
# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

# 技能装到项目内时的相对位置（与 tools/build.py 的 REL_SKILLS 保持一致）
REL_SKILLS = Path("skills") / "game-dev"

TARGETS = ("trae", "claude", "cursor", "codex", "zcode", "generic")


def require_dist():
    if not DIST.is_dir() or not (DIST / "skills").is_dir():
        print("[错误] 还没有生成产物。先运行： python tools/build.py")
        return False
    return True


def install_skills(dest: Path):
    """把 dist/skills/<name>/ 逐个复制到 dest/。"""
    dest.mkdir(parents=True, exist_ok=True)
    src = DIST / "skills"
    for skill in sorted(p for p in src.iterdir() if p.is_dir()):
        target = dest / skill.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print("  + %s" % skill.name)


def do_trae(path: Path):
    print("安装到 Trae 技能目录：%s" % path)
    install_skills(path)


def do_project(target: str, path: Path):
    dest = path / REL_SKILLS
    print("安装到项目：%s" % path)
    install_skills(dest)

    if target == "cursor":
        rules_src = DIST / "cursor" / ".cursor" / "rules"
        rules_dst = path / ".cursor" / "rules"
        rules_dst.mkdir(parents=True, exist_ok=True)
        for f in sorted(rules_src.glob("*.mdc")):
            shutil.copy2(f, rules_dst / f.name)
            print("  + .cursor/rules/%s" % f.name)
    elif target == "codex":
        agents = path / "AGENTS.md"
        new = DIST / "codex" / "AGENTS.md"
        if agents.exists():
            out = path / "AGENTS.game-dev.md"
            shutil.copy2(new, out)
            print("  已存在 AGENTS.md，索引写到 AGENTS.game-dev.md，请手动合并")
        else:
            shutil.copy2(new, agents)
            print("  + AGENTS.md")


def main() -> int:
    ap = argparse.ArgumentParser(description="game-dev-skills 跨平台安装器")
    ap.add_argument("--target", choices=TARGETS, help="目标宿主")
    ap.add_argument("--path", default=".", help="目标目录（项目根或技能目录）")
    ap.add_argument("--list", action="store_true", help="列出支持的 target")
    args = ap.parse_args()

    if args.list or not args.target:
        print("可用 target：%s" % ", ".join(TARGETS))
        print("例：python tools/install.py --target cursor --path /path/to/project")
        return 0

    if not require_dist():
        return 1

    if args.target == "claude":
        print("Claude Code 走插件市场，先推到 Git 远程，然后：\n")
        print("  /plugin marketplace add <你的仓库地址>")
        print("  /plugin install aaa-game-gdd")
        print("  /plugin install unity-blender-mcp")
        print("  /plugin install blender-modeling-craft")
        print("  /plugin install unity-gameplay-dev")
        print("\n清单在仓库根目录的 .claude-plugin/marketplace.json（python tools/build.py 生成）")
        return 0

    if args.target == "zcode":
        print("ZCode 使用仓库自带的插件市场，无需复制技能：")
        print("  %s" % (ROOT / "marketplace.json"))
        print("\n每个插件都带 .zcode-plugin/plugin.json，导入市场即可。")
        return 0

    path = Path(args.path).expanduser().resolve()
    if args.target == "trae":
        do_trae(path)
    else:
        if not path.is_dir():
            print("[错误] 目标目录不存在：%s" % path)
            return 1
        do_project(args.target, path)

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
