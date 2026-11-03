"""Verify both scaffolds produce correct, parseable output.

Extracted from the CI workflow. The original used inline bash heredocs, which
fail on Windows runners (default shell is pwsh) and were already fragile
because the heredoc terminators were mis-indented inside the YAML block.

Usage: python tools/check_scaffolds.py
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
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAMEPLAY = ROOT / "plugins/unity-gameplay-dev/skills/unity-gameplay-dev/scripts/new_gameplay.py"
GDD = ROOT / "plugins/aaa-game-gdd/skills/aaa-game-gdd/scripts/new_gdd.py"


def fail(msg):
    print(f"FAIL: {msg}")
    return 1


def unity_scaffold(tmp):
    """3D and 2D scaffolds must both emit parseable asmdefs and differ in packages."""
    for dim in ("3d", "2d"):
        proj = tmp / f"u_{dim}"
        (proj / "Assets").mkdir(parents=True)
        (proj / "Packages").mkdir(parents=True)
        (proj / "Packages" / "manifest.json").write_text(
            '{"dependencies":{}}', encoding="utf-8")

        r = subprocess.run(
            [sys.executable, str(GAMEPLAY), "--out", str(proj / "Assets" / "Game"),
             "--namespace", f"Game{dim}", "--dimension", dim],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(r.stdout[-1500:])
            return fail(f"scaffold failed for {dim}")

        for rel in ("Assets/Game/Game.asmdef", "Assets/Game.Tests/Game.Tests.asmdef"):
            f = proj / rel
            if not f.is_file():
                return fail(f"{dim}: missing {rel}")
            try:
                json.loads(f.read_text(encoding="utf-8"))
            except Exception as exc:
                return fail(f"{dim}: {rel} is not valid JSON ({exc})")

    d2 = json.loads((tmp / "u_2d/Packages/manifest.json").read_text(encoding="utf-8"))
    d3 = json.loads((tmp / "u_3d/Packages/manifest.json").read_text(encoding="utf-8"))
    if "com.unity.2d.sprite" not in d2["dependencies"]:
        return fail("2D scaffold did not add the 2D packages")
    if "com.unity.2d.sprite" in d3["dependencies"]:
        return fail("3D scaffold should not add 2D packages")

    # The scaffold must not emit 3D-only code into a 2D project: those files
    # reference Physics/AI built-ins that a 2D project may not enable.
    if (tmp / "u_2d/Assets/Game/Player/FirstPersonController.cs").exists():
        return fail("2D scaffold emitted FirstPersonController (needs Physics3D)")
    if (tmp / "u_2d/Assets/Game/AI/EnemyAI.cs").exists():
        return fail("2D scaffold emitted EnemyAI (needs the AI module)")
    if not (tmp / "u_2d/Assets/Game/Player/PlatformerController2D.cs").exists():
        return fail("2D scaffold did not emit PlatformerController2D")
    if (tmp / "u_3d/Assets/Game/Player/PlatformerController2D.cs").exists():
        return fail("3D scaffold should not emit the 2D controller")

    print("unity scaffolds OK (3D/2D split, asmdefs parse)")
    return 0


def gdd_scaffold(tmp):
    """Every engine must render with no placeholders, and outputs must differ."""
    for eng in ("unity", "unreal", "godot"):
        r = subprocess.run(
            [sys.executable, str(GDD), "init", "--name", f"T{eng}",
             "--out", str(tmp / f"g_{eng}"), "--engine", eng],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(r.stdout[-1500:])
            return fail(f"GDD scaffold failed for {eng}")

    texts = {}
    for eng in ("unity", "unreal", "godot"):
        p = tmp / f"g_{eng}" / f"T{eng}_GDD" / "11-技术与性能.md"
        if not p.is_file():
            return fail(f"{eng}: 11-技术与性能.md missing")
        text = p.read_text(encoding="utf-8")
        left = set(re.findall(r"\{\{[A-Z_]+\}\}", text))
        if left:
            return fail(f"{eng}: unresolved placeholders {left}")
        texts[eng] = text

    if texts["unity"] == texts["godot"]:
        return fail("--engine produces identical output; it is not wired through")

    print("gdd scaffolds OK (3 engines, no placeholders, outputs differ)")
    return 0


def main():
    # 用仓库内固定的工作目录，而不是 tempfile/系统 temp：
    # 受限环境（沙箱、只读 temp）下 mkdtemp 建出来的目录可能不可写，
    # 那会让本脚本在 CI 之外的地方误报"脚手架失败"。
    tmp = ROOT / "_scaffold_check"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        rc = 0
        rc |= unity_scaffold(tmp)
        if rc == 0:
            rc |= gdd_scaffold(tmp)
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
