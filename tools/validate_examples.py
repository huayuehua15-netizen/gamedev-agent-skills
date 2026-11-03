"""Validate every example against its template: sections, DoD, cross-refs."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / "plugins/aaa-game-gdd/skills/aaa-game-gdd"
TPL = SK / "assets/templates"
EX = SK / "assets/examples"

PAIRS = [
    ("scene-sheet.md", "SC_01_外科楼二层走廊_示例.md"),
    ("scene-sheet.md", "SC_07_断桥瞭望台_示例.md"),
    ("level-sheet.md", "LV_01_走廊初遇_示例.md"),
    ("character-sheet.md", "EN_01_缝合者_示例.md"),
    ("prop-sheet.md", "PR_017_缺轮轮椅_示例.md"),
    ("animation-sheet.md", "AN_EN01_Slash_01_示例.md"),
    ("dialogue-sheet.md", "DL_07_护士长录音_示例.md"),
    ("system-sheet.md", "SYS_04_抓取挣脱_示例.md"),
]


def norm(s):
    """Strip numbering and parenthetical suffixes so '7. 空间供给' == '空间供给'."""
    s = re.sub(r"^\d+\.\s*", "", s.strip())
    s = re.sub(r"（.*?）|\(.*?\)", "", s)
    return s.strip()


def sections(p):
    return [norm(m) for m in re.findall(r"^## (.+)$", p.read_text(encoding="utf-8"), re.M)]


problems = []
print(f"{'example':40} {'sections':10} {'result'}")
print("-" * 72)

for tname, ename in PAIRS:
    t, e = TPL / tname, EX / ename
    if not t.exists():
        problems.append(f"missing template {tname}")
        print(f"{ename:40} {'-':10} MISSING TEMPLATE")
        continue
    if not e.exists():
        problems.append(f"missing example {ename}")
        print(f"{ename:40} {'-':10} MISSING EXAMPLE")
        continue

    ts, es = sections(t), sections(e)
    # example may add 变更记录 (locked docs) but must cover every template section
    missing = [s for s in ts if s not in es]
    status = "OK" if not missing else f"MISSING {missing}"
    if missing:
        problems.append(f"{ename}: missing sections {missing}")
    print(f"{ename:40} {len(es):>3}/{len(ts):<5} {status}")

print()
print("=" * 72)
print("cross-reference integrity (does every TZ_/EV_/ID referenced exist?)")
print("=" * 72)

all_ids = {}
for _, ename in PAIRS:
    p = EX / ename
    if not p.exists():
        continue
    txt = p.read_text(encoding="utf-8")
    for kind in ("TZ", "EV", "SC", "LV", "EN", "PR", "SYS", "AN", "DL", "CH", "NPC"):
        for m in re.findall(rf"\b{kind}_\d{{2}}", txt):
            all_ids.setdefault(kind, set()).add(m)

for kind in sorted(all_ids):
    ids = sorted(all_ids[kind])
    print(f"  {kind+'_':6} {len(ids):2}  {', '.join(ids)}")

print()
print("dangling check: TZ_ used but never defined as a table row in a scene example")
tz_defined = set()
for _, ename in PAIRS:
    p = EX / ename
    if not p.exists() or not ename.startswith("SC_"):
        continue
    for m in re.findall(r"^\|\s*(TZ_\d{2})\s*\|", p.read_text(encoding="utf-8"), re.M):
        tz_defined.add(m)
tz_used = all_ids.get("TZ", set())
dangling = tz_used - tz_defined
if dangling:
    problems.append(f"TZ_ referenced but not defined: {sorted(dangling)}")
    print("  DANGLING TZ_:", sorted(dangling))
else:
    print("  all TZ_ defined:", sorted(tz_defined))

if problems:
    print("\nPROBLEMS:")
    for x in problems:
        print("  -", x)
    sys.exit(1)
print("\nall examples valid")
