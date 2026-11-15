"""Open-source quality audit v2 - focused on what would actually hurt users.

The v1 scan produced false positives (it flagged `references/01` shorthand and
the literal placeholder `xxx.py`). This version checks things that are
unambiguously wrong, and separates "definitely broken" from "worth a look":

  BLOCKER  - a user following the docs hits a dead end
  WARN     - inconsistent, or fragile on other platforms
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
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
blockers, warns = [], []


def B(msg):
    blockers.append(msg)


def W(msg):
    warns.append(msg)


# ---------------------------------------------------------------- 1. refs
print("== 1. 精确引用检查（要求带扩展名）==")
for sk in sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")):
    base = sk.parent
    text = sk.read_text(encoding="utf-8")
    for m in re.finditer(r"`((?:scripts|references|assets)/[^`\s]*\.(?:py|md|cs|csv))`", text):
        rel = m.group(1)
        if not (base / rel).exists():
            B(f"{base.name}: SKILL.md 引用了不存在的文件 {rel}")
print("   done")

# ---------------------------------------------------------------- 2. scripts
print("== 2. 脚本能否被导入（语法与依赖）==")
import subprocess
for py in sorted(ROOT.glob("plugins/*/skills/*/scripts/*.py")):
    if py.name.startswith("_"):
        continue
    # Blender 脚本只能在 Blender 的 Python 里 import（bpy/mathutils 不是 pip 包）。
    # 对它们只做语法检查；真正的运行验证在 check_toolchain.py 里用真 Blender 跑。
    is_blender = "blender" in str(py.parent.parent.parent).lower()
    if is_blender:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(py)],
                           capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            B(f"{py.relative_to(ROOT)}: 语法错误\n{(r.stderr or '')[-400:]}")
        continue

    r = subprocess.run([sys.executable, str(py), "--help"],
                       capture_output=True, text=True, timeout=60,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if "Traceback" in out and "SystemExit" not in out:
        B(f"{py.relative_to(ROOT)}: --help 崩溃\n{out[-500:]}")
print("   done")

# ---------------------------------------------------------------- 3. json
print("== 3. 所有 JSON 可解析 ==")
for p in ROOT.rglob("*.json"):
    if ".git" in p.parts or "dist" in p.parts:
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        B(f"{p.relative_to(ROOT)}: JSON 解析失败 {e}")
print("   done")

# ---------------------------------------------------------------- 4. BOM
print("== 4. 编码：BOM 与不可解码字节 ==")
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or "dist" in p.parts:
        continue
    if p.suffix not in (".md", ".py", ".cs", ".json", ".csv", ".asmdef", ".mdc"):
        continue
    raw = p.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        B(f"{p.relative_to(ROOT)}: 带 UTF-8 BOM")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        B(f"{p.relative_to(ROOT)}: 非 UTF-8 ({e})")
print("   done")

# ---------------------------------------------------------------- 5. links
print("== 5. Markdown 相对链接 ==")
for md in sorted(list(ROOT.glob("*.md"))):
    text = md.read_text(encoding="utf-8")
    for m in re.finditer(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", text):
        target = m.group(1).split("#")[0]
        if target and not (md.parent / target).exists():
            B(f"{md.name}: 链接指向不存在的 {target}")
print("   done")

# ---------------------------------------------------------------- 6. version
print("== 6. 版本一致性 ==")
cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", cl, re.M)
if not m:
    B("CHANGELOG.md 找不到版本号")
else:
    ver = m.group(1)
    for mp in [ROOT / "marketplace.json"] + sorted(ROOT.glob("plugins/*/.zcode-plugin/plugin.json")):
        d = json.loads(mp.read_text(encoding="utf-8"))
        vs = {d.get("version")} | {p.get("version") for p in d.get("plugins", [])}
        vs.discard(None)
        if vs and vs != {ver}:
            B(f"{mp.relative_to(ROOT)}: 版本 {sorted(vs)} != CHANGELOG {ver}")
print("   done")

# ---------------------------------------------------------------- 7. license
print("== 7. 许可证与元数据 ==")
for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md"):
    if not (ROOT / name).exists():
        B(f"缺少 {name}")
lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
if "MIT" not in lic:
    W("LICENSE 不是 MIT（与 manifest 声明的 license 不符？）")
for mp in sorted(ROOT.glob("plugins/*/.claude-plugin/plugin.json")):
    d = json.loads(mp.read_text(encoding="utf-8"))
    if d.get("license") != "MIT":
        W(f"{mp.relative_to(ROOT)}: license 不是 MIT")

# ---------------------------------------------------------------- report
print()
print("=" * 72)
print(f"BLOCKER {len(blockers)}   WARN {len(warns)}")
print("=" * 72)
for b in blockers:
    print("[BLOCKER]", b)
    # GitHub Actions 的 job 日志需要 admin 权限才能下载，所以把失败细节
    # 以 ::error:: 注解输出，这样可以免认证通过 API 读到。
    for line in str(b).splitlines()[:6]:
        print(f"::error title=check_repo::{line[:900]}")
for w in warns:
    print("[WARN]   ", w)
if not blockers and not warns:
    print("未发现问题。")
sys.exit(1 if blockers else 0)
