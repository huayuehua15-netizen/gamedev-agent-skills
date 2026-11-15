"""Second-opinion audit: the problems a static scan cannot see.

Simulates a real user following the README, step by step, and records where
they would get stuck, be misled, or hit an undocumented requirement.
"""
# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
findings = []


def note(sev, msg):
    findings.append((sev, msg))


print("== A. README 的 30 秒上手是否真的能跑通 ==")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
cmds = re.findall(r"^\s*(python tools/\S+|python tests/\S+)", readme, re.M)
print(f"   README 里列出的命令: {len(set(cmds))}")
for c in sorted(set(cmds)):
    parts = c.split()
    script = ROOT / parts[1]
    if not script.exists():
        note("BLOCKER", f"README 让你运行 {c}，但 {parts[1]} 不存在")

print("== B. 安装脚本支持的目标是否都能用 ==")
# 必须用仓库**外部**的临时目录：install.py 会拒绝写入本仓库内部（防止覆盖源码），
# 建在 ROOT 下面只会得到预期的拒绝，测不出真实安装是否可用。
import tempfile
sandbox = pathlib.Path(tempfile.mkdtemp(prefix="install_probe_"))
try:
    for tgt in ("trae", "claude", "cursor", "codex", "zcode", "generic"):
        proj = sandbox / tgt
        proj.mkdir(exist_ok=True)
        r = subprocess.run([sys.executable, str(ROOT / "tools/install.py"),
                            "--target", tgt, "--path", str(proj)],
                           capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            note("WARN", f"install.py --target {tgt} 退出 {r.returncode}: "
                         f"{(r.stderr or r.stdout or '')[-200:]}")
        elif tgt in ("cursor", "generic"):
            got = list((proj / "skills/game-dev").glob("*/SKILL.md"))
            if len(got) != 4:
                note("BLOCKER", f"install --target {tgt} 装了 {len(got)} 个技能（应为 4）")
finally:
    shutil.rmtree(sandbox, ignore_errors=True)

print("== C. 每个技能目录是否自包含（可独立安装）==")
for sk in sorted(ROOT.glob("plugins/*/skills/*")):
    has_skill = (sk / "SKILL.md").exists()
    if not has_skill:
        note("BLOCKER", f"{sk.relative_to(ROOT)} 缺少 SKILL.md")
        continue
    # does it import anything from a sibling skill?
    for py in sk.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"from\s+([a-z_]+)\s+import", text):
            mod = m.group(1)
            if mod.startswith("blender_") or mod in ("new_gameplay", "new_gdd"):
                if not (sk / "scripts" / f"{mod}.py").exists():
                    note("BLOCKER",
                         f"{py.relative_to(ROOT)} 从 {mod} 导入，但该模块不在本技能内"
                         f"（独立安装会 ImportError）")

print("== D. 首次使用的失败路径是否被文档说明 ==")
sk = ROOT / "plugins/unity-gameplay-dev/skills/unity-gameplay-dev/SKILL.md"
if sk.exists():
    t = sk.read_text(encoding="utf-8")
    if "CS0234" not in t and "CS0246" not in t and "重跑" not in t:
        note("WARN", "unity-gameplay-dev 未说明首次编译会因 InputSystem 缺失而报错")
    else:
        print("   已说明首次编译失败属预期")

print("== E. 剪影门禁的参考图要求是否说清楚 ==")
for f in ("README.md", "plugins/blender-modeling-craft/skills/blender-modeling-craft/SKILL.md"):
    p = ROOT / f
    if p.exists():
        t = p.read_text(encoding="utf-8")
        if "正交" not in t and "orthographic" not in t.lower():
            note("WARN", f"{f} 未说明参考图必须是正交视图")

print("== F. 2D 与 3D 的脚手架是否会互相污染 ==")
tmp = ROOT / "_audit_tmp"
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir()
try:
    for dim in ("2d", "3d"):
        proj = tmp / dim
        (proj / "Assets").mkdir(parents=True)
        (proj / "Packages").mkdir(parents=True)
        (proj / "Packages/manifest.json").write_text('{"dependencies":{}}', encoding="utf-8")
        # encoding 必须显式指定：Windows 上 subprocess 默认用 GBK 解码子进程输出，
        # 而脚手架会打印中文，缺这一行会在读取输出时抛 UnicodeDecodeError。
        subprocess.run([sys.executable,
                        str(ROOT / "plugins/unity-gameplay-dev/skills/unity-gameplay-dev/scripts/new_gameplay.py"),
                        "--out", str(proj / "Assets/Game"), "--namespace", "T" + dim,
                        "--dimension", dim],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    p2 = tmp / "2d/Assets/Game/Player"
    p3 = tmp / "3d/Assets/Game/Player"
    if p2.exists() and (p2 / "FirstPersonController.cs").exists():
        note("BLOCKER", "2D 项目里出现了 FirstPersonController（需要 Physics3D）")
    if p3.exists() and (p3 / "PlatformerController2D.cs").exists():
        note("BLOCKER", "3D 项目里出现了 PlatformerController2D")
    print(f"   2D 控制器: {[x.name for x in p2.glob('*.cs')] if p2.exists() else 'n/a'}")
    print(f"   3D 控制器: {[x.name for x in p3.glob('*.cs')] if p3.exists() else 'n/a'}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("=" * 72)
if not findings:
    print("未发现使用者会踩的坑。")
    sys.exit(0)
for sev, msg in findings:
    print(f"[{sev}] {msg}")
sys.exit(1 if any(s == "BLOCKER" for s, _ in findings) else 0)
