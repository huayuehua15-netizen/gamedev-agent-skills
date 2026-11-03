"""Validate the skill packages: manifests, frontmatter, examples.

Originally this lived as inline heredocs in the CI workflow. That broke on
Windows runners (the default shell there is pwsh, which has no `python - <<PY`
heredoc support) and depended on PyYAML being preinstalled, which it is not
guaranteed to be. A real file plus an explicit dependency is portable.

Usage:
    python tools/validate_skills.py            # run all checks
    python tools/validate_skills.py --no-yaml  # skip checks needing PyYAML
"""

# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

# Expected skill count, so a deleted skill fails the build rather than
# silently shrinking the suite.
EXPECTED_SKILLS = 4


def fail(msg):
    print(f"FAIL: {msg}")
    return 1


def check_json():
    bad = []
    for p in ROOT.rglob("*.json"):
        if ".git" in p.parts or "dist" in p.parts:
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append(f"  {p.relative_to(ROOT)}: {exc}")
    if bad:
        print("invalid JSON:")
        print("\n".join(bad))
        return 1
    print("all JSON valid")
    return 0


def check_frontmatter(use_yaml=True):
    skills = sorted(PLUGINS.rglob("SKILL.md"))
    if len(skills) != EXPECTED_SKILLS:
        return fail(f"expected {EXPECTED_SKILLS} SKILL.md, found {len(skills)}")

    yaml = None
    if use_yaml:
        try:
            import yaml  # noqa: F401
        except ImportError:
            print("PyYAML not installed; falling back to pattern checks")
            return check_frontmatter(use_yaml=False)

    for p in skills:
        rel = p.relative_to(ROOT)
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
        if not m:
            return fail(f"{rel}: missing frontmatter")
        block = m.group(1)

        if yaml is not None:
            meta = yaml.safe_load(block)
            if not isinstance(meta, dict):
                return fail(f"{rel}: frontmatter is not a mapping")
            for key in ("name", "description"):
                if not meta.get(key):
                    return fail(f"{rel}: missing {key}")
            desc = meta["description"]
            name = meta["name"]
        else:
            nm = re.search(r"^name:\s*(\S+)", block, re.M)
            dm = re.search(r'^description:\s*"?(.+)"?\s*$', block, re.M)
            if not nm or not dm:
                return fail(f"{rel}: missing name/description")
            name, desc = nm.group(1), dm.group(1)

        # The name must match the directory, or plugin hosts get confused.
        if p.parent.name != name:
            return fail(f"{rel}: name '{name}' != directory '{p.parent.name}'")

        # English clause: semantic skill matching is often done in English.
        if "English:" not in desc:
            return fail(f"{rel}: description needs an English clause")

        # Path convention: scripts are invoked relative to SKILL.md.
        if "路径" not in text[:1500]:
            return fail(f"{rel}: should state the path convention near the top")

    print(f"{len(skills)} skills OK")
    return 0


def check_examples():
    """Examples must cover their template and reference real ids."""
    sys.path.insert(0, str(ROOT / "tools"))
    import validate_examples  # noqa: F401  (module runs its checks on import? no)
    # validate_examples is a script; invoke it as a subprocess-free call:
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "validate_examples.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        return fail("examples do not match templates")
    print((r.stdout.strip().splitlines() or ["examples OK"])[-1])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-yaml", action="store_true",
                    help="skip checks that require PyYAML")
    args = ap.parse_args()

    rc = 0
    rc |= check_json()
    rc |= check_frontmatter(use_yaml=not args.no_yaml)
    if rc == 0:
        rc |= check_examples()
    return rc


if __name__ == "__main__":
    sys.exit(main())
