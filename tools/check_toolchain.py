"""Final quality gate: re-verify the whole shipped toolchain end to end.

Not a re-read of the code. Runs the actual gates on freshly built assets
and asserts the exit codes and numbers the README promises.
"""
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

# reference silhouette of the good crate, orthographic front
clear()
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,0.45))
r = bpy.context.object; r.scale = (0.6, 0.6, 0.9)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = 512
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'
sh = sc.display.shading
sh.light='FLAT'; sh.color_type='SINGLE'; sh.single_color=(1,1,1)
sh.show_object_outline=False; sh.show_shadows=False
cd = bpy.data.cameras.new('C'); cd.type='ORTHO'; cd.ortho_scale = 1.15
cam = bpy.data.objects.new('C', cd); sc.collection.objects.link(cam)
cam.location = (0, -5, 0.45); cam.rotation_euler = (math.radians(90), 0, 0)
sc.camera = cam
sc.render.filepath = tmp + "/ref.png"
bpy.ops.render.render(write_still=True)
print("BUILT")
'''

(TMP / "build.py").write_text(BUILD, encoding="utf-8")


def run(script, args):
    return subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
         "--python", str(script), "--"] + [str(a) for a in args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")


def jload(s):
    try:
        return json.loads(s[s.index("{"):s.rindex("}") + 1])
    except Exception:
        return None


def has_gl(tmpdir):
    """CI 的 ubuntu runner 没有 GPU，Blender 的 Workbench/EEVEE 渲染需要一个
    OpenGL 上下文，在那种环境下必然失败。这不是脚本缺陷，是环境限制。
    用 BLENDER_SKIP_RENDER=1 或探测不到渲染能力时，只跑不依赖渲染的检查。

    探测本身要写到真实存在的目录：早先写成 '/tmp/_glprobe.png'，
    在 Windows 上这个路径不存在，于是渲染"失败"，被误判成"没有 GPU"。
    """
    if os.environ.get("BLENDER_SKIP_RENDER") == "1":
        return False
    probe_png = str(Path(tmpdir) / "_glprobe.png").replace("\\", "/")
    probe = (
        "import bpy\n"
        "try:\n"
        "    s = bpy.context.scene\n"
        "    s.render.engine = 'BLENDER_WORKBENCH'\n"
        "    s.render.resolution_x = s.render.resolution_y = 32\n"
        f"    s.render.filepath = {probe_png!r}\n"
        "    bpy.ops.render.render(write_still=True)\n"
        "    print('GL_OK')\n"
        "except Exception as e:\n"
        "    print('GL_FAIL', type(e).__name__, e)\n"
    )
    r = subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-exit-code", "0",
         "--python-expr", probe],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "GL_OK" in r.stdout


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
results.append(("topology: good asset passes", r.returncode == 0, f"exit={r.returncode}"))

r = run(TOPOLOGY, [TMP / "unapplied.blend", "--budget-tris", "5000"])
results.append(("topology: unapplied transform rejected", r.returncode == 1, f"exit={r.returncode}"))

r = run(TOPOLOGY, [TMP / "nope.blend"])
results.append(("topology: missing file exits 2", r.returncode == 2, f"exit={r.returncode}"))

# Everything below drives a render, so it needs a GL context.
if RENDER_OK:
    # --- silhouette gate -------------------------------------------------
    r = run(GATE, [TMP / "good.blend", "--gate", "--stage", "final",
                   "--ref-front", TMP / "ref.png", "--outdir", TMP / "g1"])
    d = jload(r.stdout)
    iou = d["views"][0]["iou"] if d and d.get("views") else None
    ok = r.returncode == 0 and iou is not None and iou >= 0.85
    results.append(("silhouette: matching asset passes (IoU>=0.85)", ok, f"exit={r.returncode} iou={iou}"))

    r = run(GATE, [TMP / "bad.blend", "--gate", "--stage", "final",
                   "--ref-front", TMP / "ref.png", "--outdir", TMP / "g2"])
    d = jload(r.stdout)
    iou = d["views"][0]["iou"] if d and d.get("views") else None
    ok = r.returncode == 1 and iou is not None and iou < 0.85
    results.append(("silhouette: wrong proportions rejected", ok, f"exit={r.returncode} iou={iou}"))

    # --- turntable still works ------------------------------------------
    r = run(GATE, [TMP / "good.blend", "--outdir", TMP / "tt"])
    imgs = list((TMP / "tt").glob("*.png")) if (TMP / "tt").exists() else []
    results.append(("turntable: renders 4 views", r.returncode == 0 and len(imgs) == 4,
                    f"exit={r.returncode} images={len(imgs)}"))

# 参数校验在解析阶段就该失败，不需要渲染出图，所以放在渲染开关之外——
# 这样即使 CI 没有 GL 上下文，也能验证"拼错参数不会被静默忽略"。
r = run(GATE, [TMP / "good.blend", "--gate=1"])
results.append(("silhouette: typo'd flag exits 2 (no silent skip)", r.returncode == 2, f"exit={r.returncode}"))

r = run(GATE, [TMP / "good.blend", "--stage", "blockuot"])
results.append(("silhouette: misspelled stage errors", r.returncode == 2, f"exit={r.returncode}"))


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
