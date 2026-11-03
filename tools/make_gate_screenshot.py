"""重新生成 README 里的门禁对比图。

README 中 `docs/images/silhouette-gate.png` 的作者不是手工拼图：它由本脚本
用真实门禁脚本跑出来，图上的数字是脚本返回的原值。改过门禁逻辑后应当重跑，
避免截图与代码脱节（"文档说 0.99，实际早就变了"）。

需求：Blender 在 PATH 或 --blender 指定；Python 侧需要 Pillow（仅用于拼图）。

用法：
    python tools/make_gate_screenshot.py
    python tools/make_gate_screenshot.py --blender "D:/blender/blender.exe"
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
BUILD = OUT / "_build"
GATE = (ROOT / "plugins/blender-modeling-craft/skills/blender-modeling-craft"
        / "scripts/qa_render.py")

FIXTURE = r'''
# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import bpy, math, sys

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for b in list(c):
            c.remove(b)

def build_crate(name, w=0.6, d=0.6, h=0.9):
    clear()
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h / 2))
    body = bpy.context.object
    body.scale = (w, d, h)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h + 0.03))
    lid = bpy.context.object
    lid.scale = (w * 1.08, d * 1.08, 0.06)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True); lid.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    mat = bpy.data.materials.new("M_" + name)
    mat.use_nodes = True
    obj.data.materials.append(mat)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66))
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj

def render_silhouette(path, obj_h, res=512):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.film_transparent = True
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sh = sc.display.shading
    sh.light = 'FLAT'; sh.color_type = 'SINGLE'
    sh.single_color = (1.0, 1.0, 1.0)
    sh.show_object_outline = False; sh.show_shadows = False
    cd = bpy.data.cameras.new('C'); cd.type = 'ORTHO'
    cd.ortho_scale = max(obj_h, 0.2) * 1.15
    cam = bpy.data.objects.new('C', cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -4, obj_h / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

mode = sys.argv[sys.argv.index('--') + 1]
tmp = sys.argv[sys.argv.index('--') + 2]

if mode == 'good':
    build_crate('Crate_Good')
    bpy.ops.wm.save_as_mainfile(filepath=tmp + '/good.blend')
    render_silhouette(tmp + '/good_ref.png', 0.96)
    print('GOOD_OK')
elif mode == 'bad':
    build_crate('Crate_Bad', w=1.05, d=0.95, h=0.45)
    bpy.ops.wm.save_as_mainfile(filepath=tmp + '/bad.blend')
    print('BAD_OK')
'''


def run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", default="blender", help="Blender 可执行文件路径")
    ap.add_argument("--keep-build", action="store_true", help="保留中间渲染产物")
    args = ap.parse_args()

    if not GATE.is_file():
        print("[错误] 找不到门禁脚本：%s" % GATE)
        return 1

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[错误] 需要 Pillow 才能拼图： python -m pip install pillow")
        return 1

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)

    fixture = BUILD / "fixture.py"
    fixture.write_text(FIXTURE, encoding="utf-8")

    for mode, marker in (("good", "GOOD_OK"), ("bad", "BAD_OK")):
        p = run([args.blender, "--background", "--factory-startup",
                 "--python-exit-code", "1", "--python", str(fixture),
                 "--", mode, str(BUILD)])
        if marker not in p.stdout:
            print("[错误] 生成样本失败（%s）" % mode)
            print(p.stdout[-1500:])
            print(p.stderr[-1500:])
            return 1
        print("  样本就绪：%s" % mode)

    results = {}
    for name in ("good", "bad"):
        p = run([args.blender, "--background", "--factory-startup",
                 "--python-exit-code", "1", "--python", str(GATE), "--",
                 str(BUILD / f"{name}.blend"), "--gate", "--stage", "final",
                 "--ref-front", str(BUILD / "good_ref.png"),
                 "--outdir", str(BUILD / f"gate_{name}")])
        try:
            s = p.stdout.index("{")
            data = json.loads(p.stdout[s:p.stdout.rindex("}") + 1])
            v = (data.get("views") or [{}])[0]
            results[name] = {
                "exit": p.returncode,
                "passed": data.get("passed"),
                "iou": v.get("iou"),
                "err": v.get("aspect_error"),
                "tol": v.get("aspect_tol_effective"),
            }
        except Exception:
            print("[错误] 无法解析门禁输出（%s）" % name)
            print(p.stdout[-1500:])
            return 1
        print("  %-5s exit=%s pass=%s iou=%s" %
              (name, results[name]["exit"], results[name]["passed"], results[name]["iou"]))

    # 截图必须展示"一个过、一个不过"，否则说明样本坏了
    if not (results["good"]["passed"] and not results["bad"]["passed"]):
        print("[错误] 样本没有形成 通过/拒绝 对比，请检查门禁或 fixture")
        return 1

    (BUILD / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")

    make_sheet(results, sys.modules[__name__])
    print("\n已生成 %s" % (OUT / "silhouette-gate.png"))

    if not args.keep_build:
        shutil.rmtree(BUILD)
    return 0


def make_sheet(res, mod):
    from PIL import Image, ImageDraw, ImageFont

    CELL, PAD, HEADER, ROWLABEL, FOOTER = 320, 28, 92, 250, 116
    W = PAD + ROWLABEL + CELL * 2 + PAD * 2 + PAD
    H = HEADER + (CELL + PAD) * 2 + FOOTER
    BG, FG, DIM = (24, 26, 30), (232, 234, 238), (150, 156, 166)
    GREEN, RED, PANEL = (74, 205, 128), (238, 96, 96), (36, 39, 45)

    def font(size, bold=False):
        for c in [r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
                  r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
                  "/System/Library/Fonts/Helvetica.ttc",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                  else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
        return ImageFont.load_default()

    f_title, f_sub = font(30, True), font(16)
    f_name, f_meta, f_small = font(22, True), font(16), font(15)
    f_verdict = font(24, True)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((PAD, 26), "Silhouette gate — same reference, two models", font=f_title, fill=FG)
    d.text((PAD, 62), "Orthographic silhouette IoU - reference is the model's own front view",
           font=f_sub, fill=DIM)

    y = HEADER
    for title, key, colour, verdict in (("Correct proportions", "good", GREEN, "PASS"),
                                        ("Wrong proportions", "bad", RED, "FAIL")):
        m = res[key]
        d.text((PAD, y + 4), title, font=f_name, fill=FG)
        d.text((PAD, y + 40), "IoU  %.4f" % m["iou"], font=f_meta, fill=FG)
        d.text((PAD, y + 64), "aspect err  %.4f" % m["err"], font=f_meta, fill=DIM)
        d.text((PAD, y + 88), "tolerance  %.4f" % m["tol"], font=f_meta, fill=DIM)
        d.text((PAD, y + 126), verdict, font=f_verdict, fill=colour)
        d.text((PAD, y + 160), "exit code %s" % m["exit"], font=f_meta, fill=DIM)

        for i, (lab, path) in enumerate((
                ("REFERENCE", BUILD / "good_ref.png"),
                ("RENDER", BUILD / f"gate_{key}" / "silhouette" / "silhouette_front.png"))):
            x = PAD + ROWLABEL + i * (CELL + PAD)
            d.rounded_rectangle([x, y, x + CELL, y + CELL], radius=8, fill=PANEL)
            if path.exists():
                src = Image.open(path).convert("RGBA")
                src.thumbnail((CELL - 16, CELL - 16), Image.LANCZOS)
                img.paste(src, (x + (CELL - src.width) // 2,
                                y + (CELL - src.height) // 2), src)
            d.text((x + 10, y + CELL - 26), lab, font=f_small, fill=(210, 214, 220))
        y += CELL + PAD

    d.text((PAD, H - FOOTER + 18),
           "Both rows judged by the same gate, stage=final, tolerance 5%.",
           font=f_small, fill=DIM)
    d.text((PAD, H - FOOTER + 42),
           "Numbers are the values the script returned - not a mock-up.",
           font=f_small, fill=DIM)
    d.text((PAD, H - FOOTER + 66),
           "Reproduce: python tools/make_gate_screenshot.py",
           font=f_small, fill=(110, 116, 126))

    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "silhouette-gate.png", "PNG", optimize=True)


if __name__ == "__main__":
    sys.exit(main())
