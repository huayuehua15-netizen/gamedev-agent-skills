"""Rebuild dist/ and assert it matches plugins/ byte for byte.

dist/ is gitignored (it is generated), but releases and installed skills come
from it, so a drift between source and artifact is a real defect: users would
get stale skills. This runs the generator then compares hashes.

Usage: python tools/check_dist.py
"""

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

    if bad:
        for b in bad:
            print("FAIL:", b)
        return 1

    print(f"dist OK: {len(SKILLS)} skills byte-identical, {len(zips)} zips")
    return 0


if __name__ == "__main__":
    sys.exit(main())
