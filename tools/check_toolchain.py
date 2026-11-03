"""Final quality gate: re-verify the whole shipped toolchain end to end.

Not a re-read of the code. Runs the actual gates on freshly built assets
and asserts the exit codes and numbers the README promises.
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
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Blender 可执行文件：优先环境变量 BLENDER，其次 PATH，最后才回退到本机常用路径。
# 写死单一平台路径会让 CI（Linux）和其他人的机器直接跑不起来。
BLENDER = os.environ.get("BLENDER") or "blender"
if not Path(BLENDER).exists():
    for cand in (r"D:\blender\blender.exe",
                 r"C:\Program Files\Blender Foundation\Blender\blender.exe"):
        if Path(cand).exists():
            BLENDER = cand
            break

ROOT = Path(__file__).resolve().parent.parent
SK = ROOT / "plugins/blender-modeling-craft/skills/blender-modeling-craft/scripts"
TOPOLOGY = SK / "topology_audit.py"
GATE = SK / "qa_render.py"
TMP = ROOT / "_finalcheck"

if TMP.exists():
    import shutil
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)

BUILD = r'''
import bpy, math, sys
tmp = sys.argv[sys.argv.index('--') + 1]

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for b in list(c): c.remove(b)

def prep(o, name):
    o.name = name
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True
    o.data.materials.append(m)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# good crate: correct proportions, proper topology
clear()
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,0.45))
c = bpy.context.object; c.scale = (0.6, 0.6, 0.9); prep(c, "Good")
bpy.ops.wm.save_as_mainfile(filepath=tmp + "/good.blend")

# bad proportions: squashed, everything else fine
clear()
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,0.225))
b = bpy.context.object; b.scale = (1.05, 0.95, 0.45); prep(b, "BadProp")
bpy.ops.wm.save_as_mainfile(filepath=tmp + "/bad.blend")

# unapplied transform: the imported-asset bug
clear()
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,0.45))
u = bpy.context.object; u.scale = (2.5, 2.5, 2.5); u.rotation_euler = (0,0,math.radians(37))
bpy.ops.wm.save_as_mainfile(filepath=tmp + "/unapplied.blend")

# 参考剪影不再在这里渲染。
# 早先这段用 bpy.ops.render.render 生成 ref.png，而 CI 的 ubuntu runner 缺
# libEGL，渲染直接抛 "Couldn't open libEGL.so.1"，连 fixture 构建都失败，
# 于是所有检查被误报为失败。参考图纯用 numpy 合成即可，不依赖 GL。
print("BUILT")
'''

(TMP / "build.py").write_text(BUILD, encoding="utf-8")


def make_reference_png(path):
    """用 numpy 直接合成一张参考剪影，避免依赖 OpenGL。

    剪影门禁只需要一张"纯色前景 + 透明背景"的 PNG。用渲染去生成它，
    等于让一个本可以纯数学的步骤依赖 GPU，在无头 CI 上必挂。
    """
    import struct
    import zlib

    w = h = 512
    # 中央一个宽高比 0.6:0.9 的实心矩形，模拟好箱子的正视图
    bw, bh = int(w * 0.6 * 0.75), int(h * 0.9 * 0.75)
    x0, y0 = (w - bw) // 2, (h - bh) // 2

    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            inside = x0 <= x < x0 + bw and y0 <= y < y0 + bh
            row += b"\xff\xff\xff\xff" if inside else b"\x00\x00\x00\x00"
        rows.append(bytes(row))

    raw = b"".join(b"\x00" + r for r in rows)  # filter byte 0 per scanline

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


LAST = {}   # 最近一次子进程输出，失败时用于诊断
DETAIL = {}  # name -> 输出快照


def run(script, args):
    r = subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
         "--python", str(script), "--"] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    LAST["stdout"] = r.stdout
    LAST["stderr"] = r.stderr
    return r


def add(results, name, ok, detail):
    """登记一项结果，并保存刚才那次子进程输出，供失败时打印。"""
    results.append((name, ok, detail))
    DETAIL[name] = dict(LAST)


def jload(s):
    try:
        return json.loads(s[s.index("{"):s.rindex("}") + 1])
    except Exception:
        return None


def has_gl(tmpdir):
    """检测本机能否真正渲染 Workbench 剪影。

    必须按真实使用条件探测：早先用 32x32 探测，在小图上通过了，
    但真正的 512x512 剪影渲染仍然失败（CI 的 runner 上正是如此），
    于是探测结果与后续检查不一致，报出一堆无意义的 FAIL。
    现在按门禁实际用的分辨率和色深探测，并检查 PNG 是否真的落盘。
    """
    if os.environ.get("BLENDER_SKIP_RENDER") == "1":
        return False
    out = str(Path(tmpdir) / "_glprobe.png").replace("\\", "/")
    probe = (
        "import bpy\n"
        "try:\n"
        "    s = bpy.context.scene\n"
        "    s.render.engine = 'BLENDER_WORKBENCH'\n"
        "    s.render.film_transparent = True\n"
        "    s.render.resolution_x = s.render.resolution_y = 512\n"
        "    s.render.image_settings.file_format = 'PNG'\n"
        "    s.render.image_settings.color_mode = 'RGBA'\n"
        f"    s.render.filepath = {out!r}\n"
        "    bpy.ops.render.render(write_still=True)\n"
        "    print('GL_OK')\n"
        "except Exception as e:\n"
        "    print('GL_FAIL', type(e).__name__, e)\n"
    )
    r = subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-exit-code", "0",
         "--python-expr", probe],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "GL_OK" not in r.stdout:
        return False
    # 能渲染不代表能存盘，两头都要确认。
    return (Path(tmpdir) / "_glprobe.png").exists()


RENDER_OK = has_gl(TMP)
if not RENDER_OK:
    print("NOTE: no usable OpenGL context (headless GPU-less runner).")
    print("      Rendering-dependent checks will be skipped.\n")

p = run(TMP / "build.py", [TMP])
if "BUILT" not in p.stdout:
    print("fixture build FAILED"); print(p.stdout[-1200:]); print(p.stderr[-1200:]); sys.exit(1)

results = []

# --- topology gate -------------------------------------------------------
r = run(TOPOLOGY, [TMP / "good.blend", "--budget-tris", "5000"])
add(results, "topology: good asset passes", r.returncode == 0, f"exit={r.returncode}")

r = run(TOPOLOGY, [TMP / "unapplied.blend", "--budget-tris", "5000"])
add(results, "topology: unapplied transform rejected", r.returncode == 1, f"exit={r.returncode}")

r = run(TOPOLOGY, [TMP / "nope.blend"])
add(results, "topology: missing file exits 2", r.returncode == 2, f"exit={r.returncode}")

# Everything below drives a render, so it needs a GL context.
if RENDER_OK:
    # 参考图用 numpy 合成，不经过 Blender 渲染：
    # 这是本检查唯一的"外部输入"，用渲染生成它会让整条链路依赖 GPU。
    make_reference_png(TMP / "ref.png")

    # --- silhouette gate -------------------------------------------------
    r = run(GATE, [TMP / "good.blend", "--gate", "--stage", "final",
                   "--ref-front", TMP / "ref.png", "--outdir", TMP / "g1"])
    d = jload(r.stdout)
    iou = d["views"][0]["iou"] if d and d.get("views") else None
    ok = r.returncode == 0 and iou is not None and iou >= 0.85
    add(results, "silhouette: matching asset passes (IoU>=0.85)", ok, f"exit={r.returncode} iou={iou}")

    r = run(GATE, [TMP / "bad.blend", "--gate", "--stage", "final",
                   "--ref-front", TMP / "ref.png", "--outdir", TMP / "g2"])
    d = jload(r.stdout)
    iou = d["views"][0]["iou"] if d and d.get("views") else None
    ok = r.returncode == 1 and iou is not None and iou < 0.85
    add(results, "silhouette: wrong proportions rejected", ok, f"exit={r.returncode} iou={iou}")

    # --- turntable still works ------------------------------------------
    r = run(GATE, [TMP / "good.blend", "--outdir", TMP / "tt"])
    imgs = list((TMP / "tt").glob("*.png")) if (TMP / "tt").exists() else []
    add(results, "turntable: renders 4 views", r.returncode == 0 and len(imgs) == 4, f"exit={r.returncode} images={len(imgs)}")

# 参数校验在解析阶段就该失败，不需要渲染出图，所以放在渲染开关之外——
# 这样即使 CI 没有 GL 上下文，也能验证"拼错参数不会被静默忽略"。
r = run(GATE, [TMP / "good.blend", "--gate=1"])
add(results, "silhouette: typo'd flag exits 2 (no silent skip)", r.returncode == 2, f"exit={r.returncode}")

r = run(GATE, [TMP / "good.blend", "--stage", "blockuot"])
add(results, "silhouette: misspelled stage errors", r.returncode == 2, f"exit={r.returncode}")


print()
print("=" * 74)
print("FINAL TOOLCHAIN CHECK")
print("=" * 74)
fails = 0
for name, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:48} {detail}")
    if not ok:
        fails += 1
print()
print(f"{len(results) - fails}/{len(results)} passed")

import shutil
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fails else 0)


