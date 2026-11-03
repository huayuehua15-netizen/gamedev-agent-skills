#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3A 级 GDD 脚手架：初始化整套游戏开发文档树，或为单个对象生成单页文档。

用法:
  python new_gdd.py init  --name "游戏名" --out "D:/MyGame" [--engine unity] [--genre "生存恐怖"]
  python new_gdd.py sheet --type scene --name "废弃医院" --out "D:/MyGame/游戏名_GDD"

  init  : 在 --out 下创建 <游戏名>_GDD/ 目录树（12 份核心文档 + 7 个实例子目录）
  sheet : 在已有 GDD 目录中生成单页（自动编号）
          --type: scene | level | character | prop | animation | dialogue | system

不依赖第三方库，标准库即可运行。
"""

import argparse
import datetime
import re
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

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "assets" / "templates"

# 核心文档：模板文件名 -> 生成后的文件名
CORE_DOCS = [
    ("README.md", "README.md"),
    ("01-vision-pitch.md", "01-愿景与Pitch.md"),
    ("02-art-bible.md", "02-美术圣经.md"),
    ("03-scene-level.md", "03-场景与关卡.md"),
    ("04-gameplay-systems.md", "04-玩法系统.md"),
    ("05-narrative-dialogue.md", "05-剧情与台词.md"),
    ("06-interaction-uiux.md", "06-交互与UIUX.md"),
    ("07-character-spec.md", "07-角色规格.md"),
    ("08-prop-modeling.md", "08-物品建模规格.md"),
    ("09-animation-spec.md", "09-动画规格.md"),
    ("10-audio-spec.md", "10-音频设计.md"),
    ("11-tech-performance.md", "11-技术与性能.md"),
    ("12-steam-qa-checklist.md", "12-质量与Steam验收.md"),
]

# 单页类型 -> (模板文件, 子目录, 默认编号前缀)
SHEET_TYPES = {
    "scene":     ("scene-sheet.md",     "scenes",     "SC"),
    "level":     ("level-sheet.md",     "levels",     "LV"),
    "character": ("character-sheet.md", "characters", "CH"),
    "prop":      ("prop-sheet.md",       "props",      "PR"),
    "animation": ("animation-sheet.md",  "animations", "AN"),
    "dialogue":  ("dialogue-sheet.md",   "dialogue",   "DL"),
    "system":    ("system-sheet.md",     "systems",    "SYS"),
    # 2D 专用
    "sprite":    ("sprite-sheet.md",     "sprites",    "SPR"),
    "tileset":   ("tileset-sheet.md",    "tilesets",   "TS"),
}

# 2D 项目建议的子目录（init --dimension 2d 时并入 SUBDIRS）
SUBDIRS_2D = ["sprites", "tilesets"]

# 可切换编号前缀的子类型：--subtype
SUBTYPES = {
    "character": {"player": "CH", "enemy": "EN", "npc": "NPC"},
    "prop":      {"item": "PR", "weapon": "WP"},
}

ENGINE_NAMES = {
    "unity": "Unity",
    "unreal": "Unreal Engine",
    "godot": "Godot",
    "agnostic": "未指定（引擎无关）",
}

# 引擎差异配置：这些字段会被真正写进模板，而不是只换一个显示名。
# 以前的 --engine 只影响封面上的一个字符串，其余全是 Unity 口径，写 GDD 的
# Godot/Unreal 用户会拿到一份"Unity 文档改了个封面"。
ENGINE_PROFILES = {
    "unity": {
        "EXCHANGE_FORMAT": "FBX",
        "AXIS_CONVENTION": "+Z 为前、+Y 为上（左手坐标系）",
        "COLLISION_PREFIX": "无前缀约定，导入后挂 Collider 组件",
        "NAV_SYSTEM": "NavMesh（烘焙 Navigation 数据）",
        "DATA_ASSET": "ScriptableObject",
        "LOD_MECHANISM": "LODGroup（阈值按屏幕相对高度占比）",
        "RENDER_PIPELINE": "Built-in / URP / HDRP",
        "NORMAL_MAP": "OpenGL（绿通道向上 Y+）",
        "TEST_FRAMEWORK": "Unity Test Framework（EditMode/PlayMode）",
    },
    "unreal": {
        "EXCHANGE_FORMAT": "FBX",
        "AXIS_CONVENTION": "+X 为前、+Z 为上（左手坐标系）",
        "COLLISION_PREFIX": "UCX_（凸包）/ UBX_（盒）/ USP_（球）/ UCP_（胶囊）",
        "NAV_SYSTEM": "NavMesh + Recast（NavMeshBoundsVolume）",
        "DATA_ASSET": "DataAsset / DataTable",
        "LOD_MECHANISM": "Static Mesh LOD Group + Nanite（视项目）",
        "RENDER_PIPELINE": "Deferred / Forward+（Lumen 视项目）",
        "NORMAL_MAP": "DirectX（绿通道向下 Y−）",
        "TEST_FRAMEWORK": "Automation Test Framework（Gauntlet）",
    },
    "godot": {
        "EXCHANGE_FORMAT": "glTF 2.0（首选）；FBX 需 4.3+ 的 ufbx 支持",
        "AXIS_CONVENTION": "-Z 为前、+Y 为上（右手坐标系，与 glTF 一致）",
        "COLLISION_PREFIX": "-col（三角碰撞）/ -convcol（凸包）/ -colonly",
        "NAV_SYSTEM": "NavigationRegion3D + NavigationMesh（运行时烘焙）",
        "DATA_ASSET": "Resource（.tres）",
        "LOD_MECHANISM": "自动 LOD / VisibilityRange 节点",
        "RENDER_PIPELINE": "Forward+ / Mobile / Compatibility",
        "NORMAL_MAP": "OpenGL（绿通道向上 Y+）",
        "TEST_FRAMEWORK": "GUT / GdUnit4（社区插件）",
    },
    "agnostic": {},  # 未指定引擎：全部留空由用户填
}

SUBDIRS = ["scenes", "levels", "characters", "props", "animations", "dialogue", "systems"]


def today() -> str:
    return datetime.date.today().isoformat()


def render(text: str, mapping: dict) -> str:
    for key, value in mapping.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def safe_filename(name: str) -> str:
    """Windows 文件名安全化：去掉非法字符，空格转下划线。"""
    name = re.sub(r'[\\/:*?"<>|]+', "", name)
    name = name.strip().replace(" ", "_")
    return name or "未命名"


def cmd_init(args) -> int:
    if not TEMPLATE_DIR.exists():
        print(f"[错误] 找不到模板目录：{TEMPLATE_DIR}")
        return 1

    safe_name = safe_filename(args.name)
    gdd_root = Path(args.out).expanduser().resolve() / f"{safe_name}_GDD"
    if gdd_root.exists():
        print(f"[错误] 目录已存在：{gdd_root}（如需增量生成单页，请用 sheet 子命令）")
        return 1

    gdd_root.mkdir(parents=True, exist_ok=False)
    subdirs = list(SUBDIRS)
    if getattr(args, "dimension", "3d") == "2d":
        subdirs += SUBDIRS_2D
    for d in subdirs:
        (gdd_root / d).mkdir(exist_ok=True)

    engine_key = (args.engine or "agnostic").lower()
    if engine_key not in ENGINE_NAMES:
        print(f"[错误] 未知引擎 {args.engine}，可选：{', '.join(ENGINE_NAMES)}")
        return 1

    mapping = {
        "GAME_NAME": args.name,
        "DATE": today(),
        "ENGINE": ENGINE_NAMES[engine_key],
        "GENRE": args.genre or "【待确认】",
        "ITEM_NAME": "",
        "PREFIX": "",
        "NUMBER": "",
    }
    # 把该引擎的差异字段真正写进模板；agnostic 时保留占位符让用户自己填。
    for key, value in ENGINE_PROFILES.get(engine_key, {}).items():
        mapping[key] = value

    for tpl_name, out_name in CORE_DOCS:
        tpl_path = TEMPLATE_DIR / tpl_name
        if not tpl_path.exists():
            print(f"[警告] 缺少模板：{tpl_name}，已跳过")
            continue
        content = render(tpl_path.read_text(encoding="utf-8"), mapping)
        (gdd_root / out_name).write_text(content, encoding="utf-8")
        print(f"  生成 {out_name}")

    print()
    print(f"[完成] GDD 文档树已创建：{gdd_root}（引擎口径：{ENGINE_NAMES[engine_key]}）")
    if engine_key == "agnostic":
        print("[提示] 未指定引擎，11-技术与性能.md 里的引擎相关字段仍是【待确认】。")
        print("       确定引擎后重跑：--engine unity|unreal|godot")
    print("下一步：")
    print("  1. 先填写 01-愿景与Pitch.md、02-美术圣经.md、11-技术与性能.md")
    print("  2. 用 `python new_gdd.py sheet --type scene --name \"场景名\" --out "
          f"\"{gdd_root}\"` 生成单页")
    return 0


def next_number(folder: Path, prefix: str) -> str:
    """扫描目录中同前缀文件，返回下一个两位数编号。"""
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{2,3}})_")
    max_no = 0
    if folder.exists():
        for f in folder.glob(f"{prefix}_*.md"):
            m = pattern.match(f.name)
            if m:
                max_no = max(max_no, int(m.group(1)))
    return f"{max_no + 1:02d}"


def cmd_sheet(args) -> int:
    if args.type not in SHEET_TYPES:
        print(f"[错误] 未知类型 {args.type}，可选：{', '.join(SHEET_TYPES)}")
        return 1

    gdd_root = Path(args.out).expanduser().resolve()
    if not gdd_root.exists():
        print(f"[错误] GDD 目录不存在：{gdd_root}（请先用 init 初始化）")
        return 1

    tpl_name, subdir, default_prefix = SHEET_TYPES[args.type]
    tpl_path = TEMPLATE_DIR / tpl_name
    if not tpl_path.exists():
        print(f"[错误] 模板缺失：{tpl_path}")
        return 1

    # 解析子类型前缀（character: player/enemy/npc；prop: item/weapon）
    allowed = SUBTYPES.get(args.type)
    if allowed:
        subtype = (args.subtype or "").lower()
        if subtype and subtype not in allowed:
            print(f"[错误] --subtype {subtype} 无效，{args.type} 可选：{', '.join(allowed)}")
            return 1
        prefix = allowed.get(subtype, default_prefix)
    elif args.subtype:
        print(f"[错误] --subtype 仅支持 character 与 prop 类型")
        return 1
    else:
        prefix = default_prefix

    folder = gdd_root / subdir
    folder.mkdir(exist_ok=True)

    number = next_number(folder, prefix)
    item_name = args.name.strip()
    file_name = f"{prefix}_{number}_{safe_filename(item_name)}.md"
    out_path = folder / file_name

    if out_path.exists():
        print(f"[错误] 文件已存在：{out_path}")
        return 1

    # 从目录名 <游戏名>_GDD 推断游戏名
    game_name = gdd_root.name
    if game_name.endswith("_GDD"):
        game_name = game_name[:-4]

    mapping = {
        "GAME_NAME": game_name,
        "DATE": today(),
        "ENGINE": "【见 11-技术与性能.md】",
        "GENRE": "",
        "ITEM_NAME": item_name,
        "NUMBER": number,
        "PREFIX": prefix,
    }
    content = render(tpl_path.read_text(encoding="utf-8"), mapping)
    out_path.write_text(content, encoding="utf-8")
    print(f"[完成] 单页已生成：{out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="3A 级 GDD 文档脚手架")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="初始化整套 GDD 文档树")
    p_init.add_argument("--name", required=True, help="游戏名")
    p_init.add_argument("--out", required=True, help="输出目录（会在其下建 <游戏名>_GDD）")
    p_init.add_argument("--engine", default="agnostic",
                        help="unity | unreal | godot | agnostic（默认）")
    p_init.add_argument("--genre", default="", help="游戏类型（可选）")
    p_init.add_argument("--dimension", choices=["3d", "2d"], default="3d",
                        help="2d 时额外创建 sprites/ tilesets/ 子目录")

    p_sheet = sub.add_parser("sheet", help="生成单个对象单页")
    p_sheet.add_argument("--type", required=True,
                         help="scene | level | character | prop | animation | dialogue | system | sprite | tileset")
    p_sheet.add_argument("--name", required=True, help="对象名称，如 \"废弃医院\"")
    p_sheet.add_argument("--out", required=True, help="GDD 根目录（<游戏名>_GDD）")
    p_sheet.add_argument("--subtype", default="",
                         help="character: player/enemy/npc（CH/EN/NPC）；prop: item/weapon（PR/WP）")

    args = parser.parse_args()
    if args.command == "init":
        return cmd_init(args)
    if args.command == "sheet":
        return cmd_sheet(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
