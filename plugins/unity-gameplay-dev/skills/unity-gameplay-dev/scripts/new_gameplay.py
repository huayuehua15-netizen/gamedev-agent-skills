#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_gameplay.py —— unity-gameplay-dev 玩法框架脚手架

把模板（C# 框架代码 + 测试）复制进 Unity 项目并完成本地装配：
  - 替换命名空间占位符 {{NS}}
  - 为 Game/Game.Tests 两个 asmdef 生成确定性 GUID 的 .meta
  - 解析项目中 Input System 包的 asmdef GUID 并写入引用
  - 可选：自动向 Packages/manifest.json 补 com.unity.inputsystem 依赖
        并把 ProjectSettings 的 activeInputHandler 设为 Both(2)

用法：
  python new_gameplay.py --out "D:/MyProject/Assets/Game" --namespace MyGame
  python new_gameplay.py --out "D:/MyProject/Assets/Game" --namespace MyGame --no-tests
  python new_gameplay.py --out "D:/MyProject/Assets/Game" --namespace MyGame \
      --add-packages --editor-data "D:/Unity/.../Editor/Data"

说明：
  --out 必须是项目内 Assets 下的 Game 文件夹（会自动创建）。
  --add-packages 未安装 Input System 时自动写 manifest（默认开启）；
  若解析不到编辑器自带的包版本号，会打印手动安装指引而不是乱填版本。
"""

import argparse
import json
import os
import re
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
import uuid

TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "templates")
GAME_DIRNAME = "Game"
TESTS_DIRNAME = "Game.Tests"
INPUT_PACKAGE = "com.unity.inputsystem"
UGUI_PACKAGE = "com.unity.ugui"
TEST_PACKAGE = "com.unity.test-framework"
NUNIT_PACKAGE = "com.unity.ext.nunit"

# 2D 项目必需包（Unity 6 的 3D/URP 模板不含，缺了 Tilemap/PixelPerfect 类直接不存在）
PACKAGES_2D = [
    "com.unity.2d.sprite",
    "com.unity.2d.tilemap",
    "com.unity.2d.animation",
    "com.unity.2d.pixel-perfect",
]

# 各 Unity 主线出厂/内置包版本回退表
FALLBACK_VERSIONS = {
    "com.unity.inputsystem": {6000: "1.11.2", 2022: "1.7.0"},
    # UGUI 2.0.0 随 Unity 6 内置；2022 为 1.0.0
    "com.unity.ugui": {6000: "2.0.0", 2022: "1.0.0"},
    "com.unity.test-framework": {6000: "1.6.0", 2022: "1.1.33"},
    "com.unity.ext.nunit": {6000: "2.0.5", 2022: "1.0.6"},
    # 2D 包（Unity 6 内置版本区间；解析失败时用这些兜底）
    "com.unity.2d.sprite": {6000: "1.0.0", 2022: "1.0.0"},
    "com.unity.2d.tilemap": {6000: "1.0.0", 2022: "1.0.0"},
    "com.unity.2d.animation": {6000: "10.1.4", 2022: "9.0.4"},
    "com.unity.2d.pixel-perfect": {6000: "5.0.3", 2022: "5.0.3"},
}


def log(msg):
    print(msg)


def warn(msg):
    print("[警告] " + msg)


# ---------------- 项目路径解析 ----------------

def resolve_project_paths(out_path):
    out_path = os.path.abspath(out_path)
    parts = out_path.replace("\\", "/").split("/")
    if "Assets" not in parts:
        return None
    idx = len(parts) - 1 - parts[::-1].index("Assets")
    project_root = "/".join(parts[:idx])
    # "D:/MyProject/Assets" -> project_root "D:/MyProject"；盘符根目录（"D:/Assets"）时为 "D:"
    # 需补回根斜杠，否则 os.path.join("D:", "Packages") 会拼出相对路径 "D:Packages"
    if project_root.endswith(":"):
        project_root += "/"
    assets_root = "/".join(parts[: idx + 1])
    return project_root, assets_root, out_path


def read_text(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# ---------------- Input System ----------------

def find_package_cache_asmdef_guid(project_root, package_name, asmdef_name):
    """从 Library/PackageCache 里找包的 asmdef .meta，读取 GUID。"""
    cache = os.path.join(project_root, "Library", "PackageCache")
    if not os.path.isdir(cache):
        return None
    for entry in os.listdir(cache):
        if not entry.startswith(package_name):
            continue
        package_dir = os.path.join(cache, entry)
        for root, dirs, files in os.walk(package_dir):
            if os.path.basename(root).startswith("Tests") or "Samples" in root:
                continue
            meta_path = os.path.join(root, asmdef_name + ".meta")
            if os.path.isfile(meta_path):
                match = re.search(r"guid:\s*([0-9a-f]{32})", read_text(meta_path))
                if match:
                    return match.group(1)
    return None


def input_system_installed(project_root):
    manifest_path = os.path.join(project_root, "Packages", "manifest.json")
    if not os.path.isfile(manifest_path):
        return False
    manifest = json.loads(read_text(manifest_path))
    return INPUT_PACKAGE in manifest.get("dependencies", {})


def resolve_package_version(package_name, editor_data, project_root_hint):
    """优先从编辑器内置包解析版本；失败时按项目 ProjectVersion 回退。"""
    # 1. 内置包（BuiltInPackages/<package>/package.json），如 ugui
    if editor_data and os.path.isdir(editor_data):
        builtin = os.path.join(
            editor_data, "Resources", "PackageManager", "BuiltInPackages",
            package_name, "package.json")
        if os.path.isfile(builtin):
            try:
                info = json.loads(read_text(builtin))
                if info.get("version"):
                    return info["version"]
            except Exception:
                pass

    # 2. 回退表：各 Unity 主线出厂版本
    #    项目还没打开过时 ProjectVersion.txt 不存在，此时按最新主线（Unity 6）取值，
    #    而不是直接放弃——否则全新项目一个包都写不进去，只能靠人手装。
    project_version = ""
    pv_path = os.path.join(project_root_hint, "ProjectSettings", "ProjectVersion.txt")
    if os.path.isfile(pv_path):
        project_version = read_text(pv_path)
    match = re.match(r"m_EditorVersion:\s*(\d{4})\.(\d+)", project_version)
    if not match:
        match = re.match(r"(\d{4})\.(\d+)", project_version)

    table = FALLBACK_VERSIONS.get(package_name, {})
    if match:
        major = int(match.group(1))
        if major in table:
            return table[major]
    # 版本未知（新项目首次生成）：用最高主线的默认版本兜底
    if table:
        newest = max(table)
        return table[newest]
    return None


def ensure_packages(project_root, editor_data, with_tests, dimension="3d"):
    """确保 manifest 含所需包；返回 Input System 是否就绪。"""
    manifest_path = os.path.join(project_root, "Packages", "manifest.json")
    manifest = json.loads(read_text(manifest_path))
    deps = manifest.setdefault("dependencies", {})
    changed = False

    packages = [INPUT_PACKAGE, UGUI_PACKAGE]
    if with_tests:
        packages += [TEST_PACKAGE, NUNIT_PACKAGE]
    if dimension == "2d":
        # Unity 6 的 3D/URP 模板不带 com.unity.2d.*，不装就没有 Tilemap/PixelPerfect/SpriteAtlas 类型
        packages += PACKAGES_2D
    for package in packages:
        if package in deps:
            continue
        version = resolve_package_version(package, editor_data, project_root)
        if version:
            deps[package] = version
            log("已写入 manifest.json：%s@%s" % (package, version))
            changed = True
        else:
            warn("未能解析 %s 版本，请在 Package Manager 手动安装后重跑本脚本。" % package)

    if changed:
        write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    input_ready = INPUT_PACKAGE in deps
    if input_ready:
        log("Input System 依赖已就绪。")
    return input_ready


def set_active_input_handler(project_root):
    """ProjectSettings：activeInputHandler 0=旧 1=新 2=Both；设置为 2 最稳妥。"""
    settings_path = os.path.join(project_root, "ProjectSettings", "ProjectSettings.asset")
    if not os.path.isfile(settings_path):
        warn("未找到 ProjectSettings.asset，跳过 activeInputHandler 设置（新工程首次打开后再设）。")
        return
    text = read_text(settings_path)
    if re.search(r"activeInputHandler:\s*[12]", text):
        return
    if re.search(r"activeInputHandler:\s*0", text):
        text = re.sub(r"activeInputHandler:\s*0", "activeInputHandler: 2", text, count=1)
    else:
        text = text.rstrip() + "\n  activeInputHandler: 2\n"
    write_text(settings_path, text)
    log("已将 activeInputHandler 设为 2（Both）。")


# ---------------- 复制与装配 ----------------

def deterministic_guid(seed):
    return uuid.uuid5(uuid.NAMESPACE_URL, seed).hex


# 维度专属文件：2D 项目不装 Physics/AI 模块，生成 3D 专用脚本会直接编译失败
# （CharacterController → UnityEngine.PhysicsModule、NavMeshAgent → UnityEngine.AIModule，
#  Unity 会报 CS1069 "type forwarded to assembly ... Enable the built in package"）。
FILES_3D_ONLY = {
    "Player/FirstPersonController.cs",
    "Player/PlayerLook.cs",
    "AI/EnemyAI.cs",
    "AI/EnemyPerception.cs",
    "Interaction/Interactor.cs",
    "Interaction/InteractableBase.cs",
    "Interaction/PickupItem.cs",
}

FILES_2D_ONLY = {
    "Player/PlatformerController2D.cs",
}


def copy_tree(src, dst, namespace, replacements, dimension="3d"):
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        for name in files:
            if name.endswith(".meta"):
                continue
            rel_posix = os.path.relpath(os.path.join(root, name), src).replace("\\", "/")
            if dimension == "2d" and rel_posix in FILES_3D_ONLY:
                log("  [2D] 跳过 3D 专用文件：%s" % rel_posix)
                continue
            if dimension == "3d" and rel_posix in FILES_2D_ONLY:
                log("  [3D] 跳过 2D 专用文件：%s" % rel_posix)
                continue
            src_file = os.path.join(root, name)
            content = read_text(src_file)
            content = content.replace("{{NS}}", namespace)
            for key, value in replacements.items():
                content = content.replace(key, value)
            if name.endswith(".asmdef"):
                content = strip_missing_guid_refs(content)
            write_text(os.path.join(target_dir, name), content)


def strip_missing_guid_refs(content):
    """包尚未导入时，引用里会留着全零 GUID 占位符；从 references 数组中摘掉。

    必须走 JSON 往返而不是按行过滤：按行删会把数组尾元素删成 "[...]," 这种
    非法 JSON，Unity 会直接报 asmdef 解析失败。解析失败时原样返回，交给人工看。
    """
    zero = "0" * 32
    try:
        data = json.loads(content)
    except ValueError:
        warn("asmdef 不是合法 JSON，无法清理零 GUID 引用，请人工检查。")
        return content
    refs = data.get("references")
    if isinstance(refs, list):
        data["references"] = [r for r in refs if zero not in str(r)]
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n"


def write_meta_for(path, guid):
    """asmdef 与 .cs 用不同的 importer 块；写错会触发重新导入并可能改写 GUID。"""
    if path.endswith(".asmdef"):
        body = ("fileFormatVersion: 2\n"
                "guid: %s\n"
                "AssemblyDefinitionImporter:\n"
                "  externalObjects: {}\n"
                "  userData: \n"
                "  assetBundleName: \n"
                "  assetBundleVariant: \n" % guid)
    else:
        body = ("fileFormatVersion: 2\n"
                "guid: %s\n"
                "MonoImporter:\n"
                "  externalObjects: {}\n"
                "  serializedVersion: 2\n"
                "  defaultReferences: []\n"
                "  executionOrder: 0\n"
                "  icon: {instanceID: 0}\n"
                "  userData: \n"
                "  assetBundleName: \n"
                "  assetBundleVariant: \n" % guid)
    write_text(path + ".meta", body)


def scaffold(out_path, namespace, with_tests, add_packages, editor_data,
             dimension="3d"):
    resolved = resolve_project_paths(out_path)
    if not resolved:
        log("[错误] --out 必须位于 Unity 项目的 Assets 目录内，例如 D:/MyProject/Assets/Game")
        return 1
    project_root, assets_root, game_target = resolved
    if os.path.basename(game_target) != GAME_DIRNAME:
        log("[提示] 输出目录建议命名为 Assets/Game（当前：%s），继续按你给的路径生成。"
            % game_target)

    game_src = os.path.join(TEMPLATE_ROOT, "Game")
    if not os.path.isdir(game_src):
        log("[错误] 模板目录不存在：%s" % game_src)
        return 1

    # 1. Input System
    input_ready = True
    if add_packages:
        input_ready = ensure_packages(project_root, editor_data, with_tests, dimension)
        set_active_input_handler(project_root)
    input_guid = find_package_cache_asmdef_guid(project_root, INPUT_PACKAGE, "Unity.InputSystem.asmdef")
    if not input_guid:
        input_guid = "00000000000000000000000000000000"
        if input_ready:
            warn("项目尚未导入包，读不到 InputSystem GUID；先打开一次 Unity 让包下载，"
                 "再重跑本脚本，或在 asmdef Inspector 里手动勾选 Unity.InputSystem。")
        input_ready = False

    # 2. GUID
    game_guid = deterministic_guid(namespace + ".Game")
    tests_guid = deterministic_guid(namespace + ".Game.Tests")
    replacements = {
        "__INPUT_GUID__": input_guid,
        "__GAME_ASMDEF_GUID__": game_guid,
    }

    # 3. 复制 Game
    if os.path.isdir(game_target):
        warn("目标目录已存在：%s，将覆盖其中同名文件（不会删除其他文件）。" % game_target)
    copy_tree(game_src, game_target, namespace, replacements, dimension)
    write_meta_for(os.path.join(game_target, "Game.asmdef"), game_guid)
    log("Game 框架已写入：%s" % game_target)

    # 4. 复制 Tests
    if with_tests:
        tests_src = os.path.join(TEMPLATE_ROOT, "Tests")
        tests_target = os.path.join(assets_root, TESTS_DIRNAME)
        copy_tree(tests_src, tests_target, namespace, replacements, dimension)
        write_meta_for(os.path.join(tests_target, "Game.Tests.asmdef"), tests_guid)
        log("测试程序集已写入：%s" % tests_target)

    # 5. 汇总
    log("")
    log("装配完成。下一步：")
    log("1. 打开 Unity 让其编译（或用 MCP refresh_unity），read_console 确认零报错。")
    if not input_ready:
        log("2. 安装 Input System（Package Manager / manage_packages），之后重跑本脚本修复 GUID。")
    if with_tests:
        log(("%s. 打开 Test Runner 运行 InventoryTests（MCP: run_tests / get_test_job）。"
             % ("3" if input_ready else "3")))
    log("4. 按 references/02-input-and-fp-controller.md 搭建 Player 预制体。")
    if dimension == "2d":
        log("   [2D] 控制器/物理/导航请改读 references/11-2d-gameplay.md，"
            "不要用 CharacterController + NavMesh。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Unity 玩法框架脚手架")
    parser.add_argument("--out", required=True, help="目标目录，如 D:/MyProject/Assets/Game")
    parser.add_argument("--namespace", required=True, help="C# 根命名空间，如 MyGame")
    parser.add_argument("--no-tests", action="store_true", help="不生成测试程序集")
    parser.add_argument("--no-add-packages", dest="add_packages", action="store_false",
                        help="不改写 manifest.json，只生成代码")
    parser.add_argument("--editor-data", default=os.environ.get("UNITY_EDITOR_DATA", ""),
                        help="Editor/Data 目录（解析包版本用），可选")
    parser.add_argument("--dimension", choices=["3d", "2d"], default="3d",
                        help="2d 时额外写入 com.unity.2d.* 包（Unity 6 的 3D 模板不带）")
    args = parser.parse_args()

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", args.namespace):
        log("[错误] 命名空间不合法：%s" % args.namespace)
        return 1
    return scaffold(args.out, args.namespace, not args.no_tests, args.add_packages,
                    args.editor_data or None, args.dimension)


if __name__ == "__main__":
    sys.exit(main())
