"""Rebuild dist/ and assert it matches plugins/ byte for byte.

dist/ is gitignored (it is generated), but releases and installed skills come
from it, so a drift between source and artifact is a real defect: users would
get stale skills. This runs the generator then compares hashes.

Usage: python tools/check_dist.py
"""

# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build.py"
SKILLS = ("aaa-game-gdd", "blender-modeling-craft",
          "unity-blender-mcp", "unity-gameplay-dev")


def digest(base: pathlib.Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in base.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts):
        h.update(f.relative_to(base).as_posix().encode("utf-8"))
        h.update(f.read_bytes())
    return h.hexdigest()


def main() -> int:
    r = subprocess.run([sys.executable, str(BUILD)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-1500:])
        print("FAIL: build.py failed")
        return 1

    bad = []
    for name in SKILLS:
        src = ROOT / "plugins" / name / "skills" / name
        dst = ROOT / "dist" / "skills" / name
        if not src.is_dir():
            bad.append(f"missing source: {name}")
            continue
        if not dst.is_dir():
            bad.append(f"missing dist output: {name}")
            continue
        if digest(src) != digest(dst):
            bad.append(f"dist drift: {name}")

    # Also confirm the upload zips exist, since that is the path
    # upload-based hosts use.
    zips = sorted((ROOT / "dist" / "upload").glob("*.zip"))
    if len(zips) != len(SKILLS):
        bad.append(f"expected {len(SKILLS)} upload zips, found {len(zips)}")

    # 版本号必须与 CHANGELOG 一致。曾经十个清单全部停在 1.0.0，
    # 而内容已经到 1.2.0，插件市场会显示过期版本。
    import json
    import re
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", cl, re.M)
    if not m:
        bad.append("cannot parse version from CHANGELOG.md")
    else:
        want = m.group(1)
        manifests = [ROOT / "marketplace.json",
                     ROOT / ".claude-plugin" / "marketplace.json"]
        manifests += sorted(ROOT.glob("plugins/*/.claude-plugin/plugin.json"))
        manifests += sorted(ROOT.glob("plugins/*/.zcode-plugin/plugin.json"))
        for mp in manifests:
            if not mp.is_file():
                bad.append(f"missing manifest: {mp.relative_to(ROOT)}")
                continue
            try:
                d = json.loads(mp.read_text(encoding="utf-8"))
            except Exception as exc:
                bad.append(f"invalid JSON in {mp.relative_to(ROOT)}: {exc}")
                continue
            versions = set()
            if "version" in d:
                versions.add(d["version"])
            for p in d.get("plugins", []):
                if "version" in p:
                    versions.add(p["version"])
            if versions and versions != {want}:
                bad.append(f"{mp.relative_to(ROOT)}: version {sorted(versions)} "
                           f"!= CHANGELOG {want}")

    if bad:
        for b in bad:
            print("FAIL:", b)
        return 1

    print(f"dist OK: {len(SKILLS)} skills byte-identical, {len(zips)} zips")
    return 0


if __name__ == "__main__":
    sys.exit(main())
