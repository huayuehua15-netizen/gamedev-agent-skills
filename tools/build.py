"""把 plugins/ 里的技能源生成各宿主可用的形态。

输出到 dist/：
  skills/<name>/                 通用 SKILL.md 形态（Trae、任何认 SKILL.md 的宿主）
  claude-code/                   Claude Code 插件市场（.claude-plugin 清单）
  cursor/.cursor/rules/*.mdc     Cursor 规则（指向项目内 skills/game-dev/）
  codex/AGENTS.md                Codex 指令入口（同一份技能索引）
  upload/<name>.zip              上传式宿主（Claude.ai 等）

用法：python tools/build.py
"""

import json
import os
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PLUGINS = ROOT / "plugins"
REL_SKILLS = "skills/game-dev"  # 安装到项目内时的相对位置

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def read_skill(skill_dir):
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("%s 缺少 frontmatter" % skill_dir)
    end = text.find("\n---", 3)
    block = text[3:end]
    meta = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    if "name" not in meta or "description" not in meta:
        raise ValueError("%s 缺少 name/description" % skill_dir)
    return meta


def short(text, limit=180):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "；", "，"):
        pos = cut.rfind(mark)
        if pos > limit * 0.5:
            return cut[:pos + 1]
    return cut.rstrip() + "…"


def collect():
    skills = []
    for plugin_dir in sorted(PLUGINS.iterdir()):
        if not plugin_dir.is_dir():
            continue
        skills_root = plugin_dir / "skills"
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(skills_root.iterdir()):
            if (skill_dir / "SKILL.md").is_file():
                meta = read_skill(skill_dir)
                skills.append({
                    "plugin": plugin_dir.name,
                    "name": meta["name"],
                    "description": meta["description"],
                    "dir": skill_dir,
                })
    return skills


def reset(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_generic(skills):
    out = DIST / "skills"
    reset(out)
    for skill in skills:
        shutil.copytree(skill["dir"], out / skill["name"], ignore=IGNORE)


def build_claude(skills):
    """Claude Code 的清单必须落在仓库根目录，才能用 /plugin marketplace add <git-url>。"""
    for plugin in sorted({s["plugin"] for s in skills}):
        pdir = PLUGINS / plugin
        (pdir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        desc = next((s["description"] for s in skills if s["plugin"] == plugin), "")
        manifest = {
            "name": plugin,
            "version": "1.0.0",
            "description": short(desc, 300),
            "license": "MIT",
            "skills": "./skills/",
        }
        (pdir / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    entries = []
    seen = set()
    for skill in skills:
        if skill["plugin"] in seen:
            continue
        seen.add(skill["plugin"])
        entries.append({
            "name": skill["plugin"],
            "source": "./plugins/%s" % skill["plugin"],
            "description": short(skill["description"], 300),
            "version": "1.0.0",
        })
    marketplace = {
        "name": "game-dev-skills",
        "owner": {"name": "game-dev-skills authors"},
        "plugins": entries,
    }
    out = ROOT / ".claude-plugin"
    out.mkdir(parents=True, exist_ok=True)
    (out / "marketplace.json").write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_cursor(skills):
    out = DIST / "cursor" / ".cursor" / "rules"
    reset(out.parent)
    out.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        body = (
            "---\n"
            "description: %s\n"
            "alwaysApply: false\n"
            "---\n\n"
            "# %s\n\n"
            "%s\n\n"
            "命中这类任务时，先读项目内的 `%s/%s/SKILL.md`，"
            "再按其中 references 索引按需读取，不要一次全读。\n\n"
            "技能里的 `scripts/` 需要手动执行（Blender headless 或 Python），"
            "Cursor 只负责提供规则，不会自动跑脚本。\n"
        ) % (short(skill["description"], 120), skill["name"],
             short(skill["description"], 300), REL_SKILLS, skill["name"])
        (out / ("game-dev-%s.mdc" % skill["name"])).write_text(body, encoding="utf-8")


def build_codex(skills):
    out = DIST / "codex"
    reset(out)
    lines = [
        "# Game Dev Skills",
        "",
        "本目录自带 4 个游戏开发技能。**按任务只读对应的 SKILL.md**，",
        "不要一次读完所有 references。",
        "",
        "## 技能索引",
        "",
        "| 任务 | 读取 |",
        "|---|---|",
    ]
    for skill in skills:
        lines.append("| %s | `%s/%s/SKILL.md` |" % (
            short(skill["description"], 90), REL_SKILLS, skill["name"]))
    lines += [
        "",
        "## 硬规则",
        "",
        "- 3D 资产先查现成的，再自建；自建必须跑剪影门禁，不通过不许导出。",
        "- 玩法代码以 GDD 数值为准，编译零错才算完成。",
        "- 脚本用 `blender --background --python` 或 `python` 手动执行。",
        "",
        "> 生成文件。安装脚本会把技能复制到 `%s/`。" % REL_SKILLS,
    ]
    (out / "AGENTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zips(skills):
    out = DIST / "upload"
    reset(out)
    for skill in skills:
        archive = out / ("%s.zip" % skill["name"])
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(skill["dir"].rglob("*")):
                if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                zf.write(path, os.path.join(skill["name"], path.relative_to(skill["dir"])))


def main():
    skills = collect()
    if not skills:
        raise SystemExit("没有找到任何技能")
    DIST.mkdir(parents=True, exist_ok=True)
    build_generic(skills)
    build_claude(skills)
    build_cursor(skills)
    build_codex(skills)
    build_zips(skills)
    print("技能：%d 个" % len(skills))
    for skill in skills:
        print("  - %s (%s)" % (skill["name"], skill["plugin"]))
    print("输出：%s" % DIST)


if __name__ == "__main__":
    main()
