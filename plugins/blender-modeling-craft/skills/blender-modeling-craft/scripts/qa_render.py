"""
qa_render.py — 多角度质检渲染 + 剪影几何门禁（Blender 4.x / 5.x）

用法：
  # 1) 常规质检渲染：4 个角度，中性灰背景 + 三点布光
  blender --background --python scripts/qa_render.py -- model.blend --outdir C:/tmp/qa

  # 2) 剪影门禁（blockout 阶段，阈值宽）：把"像不像参考图"变成一个数字
  blender --background --python scripts/qa_render.py -- model.blend --gate \
      --ref-front refs/front.png --ref-side refs/side.png \
      --stage blockout --outdir C:/tmp/qa

  # 3) 剪影门禁（成品阶段，阈值严）
  blender --background --python scripts/qa_render.py -- model.blend --gate \
      --ref-front refs/front.png --stage final --outdir C:/tmp/qa

退出码：
  0 = 通过（或未启用 gate）
  1 = 门禁不通过（不许导出）
  2 = 参数或文件问题（缺参考图 / 找不到对象 / 渲染失败）

判定口径：
  - 正交渲染（Workbench 单色 + 透明背景），得到纯剪影，不受材质和灯光影响；
  - 按包围盒等比归一后算 IoU（不拉伸到整帧，避免掩盖比例错误）；
  - 宽高比单独校验，与 IoU 同时达标才算通过；
  - 阈值：blockout IoU 0.70 / 宽高比 10%；final IoU 0.85 / 宽高比 5%。
"""

import bpy
import math
import os
import sys
import json

import numpy as np
from mathutils import Vector

RENDER_RES = (1280, 720)
SIL_RES = 512
SAFE_MARGIN = 1.22
ELEVATION = math.radians(22.0)
AZIMUTHS = [35.0, 125.0, 215.0, 305.0]
NAMES = ["front_34", "side", "back_34", "rear"]

STAGE_DEFAULTS = {
    "blockout": {"iou_min": 0.70, "aspect_tol": 0.10},
    "final": {"iou_min": 0.85, "aspect_tol": 0.05},
}


# ---------------------------------------------------------------- 场景与渲染

def _set_engine(scene):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            return engine
        except TypeError:
            continue
    return scene.render.engine


def _collect_targets(target_name=None, collection_name=None):
    if collection_name:
        col = bpy.data.collections.get(collection_name)
        if col is None:
            raise RuntimeError("找不到集合：%s" % collection_name)
        return [o for o in col.objects if o.type == "MESH" and not o.hide_render]
    if target_name:
        obj = bpy.data.objects.get(target_name)
        if obj is None:
            raise RuntimeError("找不到对象：%s" % target_name)
        return [obj]
    return [o for o in bpy.context.scene.objects
            if o.type == "MESH" and not o.hide_render and not o.name.startswith("REF_")]


def _combined_bbox(objects):
    """合并世界空间包围盒（min/max 角点）。"""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            lo.x = min(lo.x, world.x); lo.y = min(lo.y, world.y); lo.z = min(lo.z, world.z)
            hi.x = max(hi.x, world.x); hi.y = max(hi.y, world.y); hi.z = max(hi.z, world.z)
    return lo, hi


def _world_corners(objects):
    pts = []
    for obj in objects:
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    return pts


def _fit_camera(cam, center, az, elev, corners, scene):
    """
    角点法迭代取景：从较近距离开始，把全部包围盒角点投影到 NDC，
    只要有角点超出 22% 安全边距（半幅 0.82）就后退 15%，直到全部入画。
    """
    from bpy_extras.object_utils import world_to_camera_view
    direction = Vector((
        math.cos(az) * math.cos(elev),
        math.sin(az) * math.cos(elev),
        math.sin(elev),
    )).normalized()
    # 相机在高处俯视：机位 = center + dir*dist，相机 -Z 对准 -dir
    eul = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler = eul
    radius = max((p - center).length for p in corners)
    dist = max(radius * 2.0, 0.5)
    limit = 1.0 / SAFE_MARGIN  # 0.82
    for _ in range(60):
        cam.location = center + direction * dist
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        ok = True
        for p in corners:
            ndc = world_to_camera_view(scene, cam, p)
            if ndc.z <= 0.001:
                ok = False
                break
            if abs(ndc.x - 0.5) * 2.0 > limit or abs(ndc.y - 0.5) * 2.0 > limit:
                ok = False
                break
        if ok:
            return dist
        dist *= 1.15
    return dist


def _isolate(targets, keep_qa=True):
    """隐藏非目标的可渲染对象，返回被隐藏列表以便恢复。"""
    keep = {o.name for o in targets}
    hidden = []
    for o in bpy.context.scene.objects:
        if o.name in keep or o.type in ("CAMERA", "LIGHT"):
            continue
        if keep_qa and o.name.startswith("QA_"):
            continue
        if o.hide_render:
            continue
        if o.type in ("MESH", "CURVE", "SURFACE", "META", "FONT", "GPENCIL", "VOLUME"):
            o.hide_render = True
            hidden.append(o)
    return hidden


def _restore(hidden):
    for o in hidden:
        o.hide_render = False


def setup_world_and_lights(target, ground_z):
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = next((n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = (0.32, 0.32, 0.32, 1.0)
        bg.inputs[1].default_value = 1.0

    # 地面（阴影用，仅渲染、不参与模型）
    ground = bpy.data.objects.get("QA_Ground")
    if ground is None:
        bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, ground_z))
        ground = bpy.context.object
        ground.name = "QA_Ground"
        mat = bpy.data.materials.new("QA_Ground_Mat")
        mat.use_nodes = True
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.22, 0.22, 0.22, 1.0)
        ground.data.materials.append(mat)
    else:
        ground.location.z = ground_z

    def add_light(name, kind, energy, loc, rot):
        data = bpy.data.lights.new(name, type=kind)
        data.energy = energy
        if kind == "AREA":
            data.size = 3.0
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = rot
        return obj

    # 清理旧 QA 灯
    for o in list(bpy.data.objects):
        if o.name.startswith("QA_") and o.type == "LIGHT":
            bpy.data.objects.remove(o, do_unlink=True)
    r = 6.0
    add_light("QA_Key", "AREA", 1200, (r * 0.7, -r * 0.9, 6.0),
              (math.radians(55), 0, math.radians(35)))
    add_light("QA_Fill", "AREA", 500, (-r * 0.9, -r * 0.4, 3.5),
              (math.radians(65), 0, math.radians(-55)))
    add_light("QA_Rim", "AREA", 900, (r * 0.3, r * 0.9, 5.5),
              (math.radians(60), 0, math.radians(200)))


def render_turntable(blend=None, outdir=None, target_name=None, collection_name=None):
    if blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    scene = bpy.context.scene
    _set_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = RENDER_RES
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"

    targets = _collect_targets(target_name, collection_name)
    if not targets:
        raise RuntimeError("场景里没有 MESH 对象")
    lo, hi = _combined_bbox(targets)
    center = (lo + hi) * 0.5
    corners = _world_corners(targets)

    # 相机
    cam_data = bpy.data.cameras.new("QA_Cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("QA_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    setup_world_and_lights(center, lo.z)

    outdir = outdir or os.path.join(os.path.dirname(bpy.data.filepath) or ".", "qa_render")
    os.makedirs(outdir, exist_ok=True)

    # 只渲染目标：临时隐藏其他可渲染对象（渲染后恢复）
    hidden = _isolate(targets)

    outputs = []
    try:
        for az_deg, name in zip(AZIMUTHS, NAMES):
            az = math.radians(az_deg)
            dist = _fit_camera(cam, center, az, ELEVATION, corners, scene)
            print("[取景] %s 相机距离 %.2fm" % (name, dist))
            path = os.path.join(outdir, "qa_%s.png" % name)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            outputs.append(path)
    finally:
        _restore(hidden)
    return outputs


# ---------------------------------------------------------------- 剪影门禁

def _setup_workbench(scene):
    """Workbench 单色 + 透明背景：得到不受材质/灯光影响的纯剪影。"""
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_x = SIL_RES
    scene.render.resolution_y = SIL_RES
    scene.render.resolution_percentage = 100

    shading = scene.display.shading
    for attr, value in (
        ("light", "FLAT"),
        ("color_type", "SINGLE"),
        ("single_color", (0.0, 0.0, 0.0)),
        ("show_object_outline", False),
        ("show_shadows", False),
        ("show_cavity", False),
        ("show_specular_highlight", False),
        ("show_xray", False),
    ):
        try:
            setattr(shading, attr, value)
        except (AttributeError, TypeError):
            pass
    try:
        scene.display.render_aa = "8"
    except (AttributeError, TypeError):
        pass


def _make_ortho_camera(view, lo, hi):
    center = (lo + hi) * 0.5
    size = hi - lo
    max_dim = max(size.x, size.y, size.z, 0.1)

    data = bpy.data.cameras.new("QA_OrthoCam")
    data.type = "ORTHO"
    data.clip_start = 0.01
    data.clip_end = max_dim * 10.0
    cam = bpy.data.objects.new("QA_OrthoCam", data)
    bpy.context.scene.collection.objects.link(cam)

    if view == "front":
        # 从 -Y 看向 +Y：Blender 里 -Y 是朝向 Unity 的正面
        data.ortho_scale = max(size.x, size.z, 0.1) * 1.10
        cam.location = (center.x, lo.y - max_dim * 2.0, center.z)
        cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    else:
        # 从 +X 看向 -X：侧视
        data.ortho_scale = max(size.y, size.z, 0.1) * 1.10
        cam.location = (hi.x + max_dim * 2.0, center.y, center.z)
        cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(90.0))

    bpy.context.scene.camera = cam
    return cam


def _drop_camera(cam):
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(data)


def _render_silhouettes(targets, outdir):
    scene = bpy.context.scene
    prev_engine = scene.render.engine
    prev_transparent = scene.render.film_transparent
    lo, hi = _combined_bbox(targets)
    hidden = _isolate(targets, keep_qa=False)

    paths = {}
    try:
        _setup_workbench(scene)
        os.makedirs(outdir, exist_ok=True)
        for view in ("front", "side"):
            cam = _make_ortho_camera(view, lo, hi)
            try:
                path = os.path.join(outdir, "silhouette_%s.png" % view)
                scene.render.filepath = path
                bpy.ops.render.render(write_still=True)
                paths[view] = path
                print("[剪影] %s -> %s" % (view, path))
            finally:
                _drop_camera(cam)
    finally:
        _restore(hidden)
        scene.render.engine = prev_engine
        scene.render.film_transparent = prev_transparent
    return paths


def _load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        if w == 0 or h == 0:
            raise RuntimeError("无法读取图片：%s" % path)
        buf = np.array(img.pixels[:], dtype=np.float32)
        return buf.reshape(h, w, 4)
    finally:
        bpy.data.images.remove(img)


def mask_from_rgba(arr, tol=0.12):
    """
    从 RGBA 取剪影 mask：
    - 有透明像素 → 用 alpha；
    - 不透明图（参考图 / 截图）→ 以四边中位色为背景，按颜色距离取前景。
    """
    alpha = arr[..., 3]
    if float(alpha.min()) < 0.99:
        return alpha > 0.5

    rgb = arr[..., :3]
    border = np.concatenate([rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0)
    bg = np.median(border, axis=0)
    dist = np.abs(rgb - bg).max(axis=2)
    return dist > tol


def _bbox_of(mask):
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _resize_nearest(mask, out_h, out_w):
    h, w = mask.shape
    ys = np.minimum((np.arange(out_h) * h / out_h).astype(np.int32), h - 1)
    xs = np.minimum((np.arange(out_w) * w / out_w).astype(np.int32), w - 1)
    return mask[np.ix_(ys, xs)]


def normalize_mask(mask, size=256, pad=0.05):
    """
    裁到包围盒 → 等比缩放到统一画布 → 居中。
    返回 (画布, 宽高比 w/h, 是否有效)。等比缩放是关键：拉伸会掩盖比例错误。
    """
    box = _bbox_of(mask)
    if box is None:
        return None, None, False
    x0, y0, x1, y1 = box
    cropped = mask[y0:y1, x0:x1]
    h, w = cropped.shape
    inner = max(1, int(round(size * (1.0 - 2.0 * pad)))
                )
    scale = inner / float(max(h, w))
    nh = max(1, int(round(h * scale)))
    nw = max(1, int(round(w * scale)))
    small = _resize_nearest(cropped, nh, nw)

    canvas = np.zeros((size, size), dtype=bool)
    oy = (size - nh) // 2
    ox = (size - nw) // 2
    canvas[oy:oy + nh, ox:ox + nw] = small
    return canvas, float(w) / float(h), True


def iou_score(mask_a, mask_b):
    union = np.logical_or(mask_a, mask_b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(mask_a, mask_b).sum()) / float(union)


def compare_view(view, render_mask, ref_mask, iou_min, aspect_tol):
    canvas_r, aspect_r, ok_r = normalize_mask(render_mask)
    canvas_ref, aspect_ref, ok_ref = normalize_mask(ref_mask)
    if not ok_r or not ok_ref:
        return {
            "view": view,
            "pass": False,
            "error": "剪影为空（渲染或参考图没有前景）",
            "iou": 0.0,
            "aspect_render": None,
            "aspect_ref": None,
            "aspect_error": None,
        }

    score = iou_score(canvas_r, canvas_ref)
    aspect_error = abs(aspect_r - aspect_ref) / aspect_ref
    passed = score >= iou_min and aspect_error <= aspect_tol
    return {
        "view": view,
        "pass": bool(passed),
        "iou": round(score, 4),
        "aspect_render": round(aspect_r, 4),
        "aspect_ref": round(aspect_ref, 4),
        "aspect_error": round(aspect_error, 4),
    }


def silhouette_gate(targets, outdir, refs, stage="final", iou_min=None, aspect_tol=None):
    defaults = STAGE_DEFAULTS.get(stage, STAGE_DEFAULTS["final"])
    iou_min = defaults["iou_min"] if iou_min is None else iou_min
    aspect_tol = defaults["aspect_tol"] if aspect_tol is None else aspect_tol

    paths = _render_silhouettes(targets, os.path.join(outdir, "silhouette"))

    views = []
    for view in ("front", "side"):
        ref = refs.get(view)
        if not ref:
            continue
        if not os.path.isfile(ref):
            raise RuntimeError("找不到参考图：%s" % ref)
        render_mask = mask_from_rgba(_load_rgba(paths[view]))
        ref_mask = mask_from_rgba(_load_rgba(ref))
        views.append(compare_view(view, render_mask, ref_mask, iou_min, aspect_tol))

    if not views:
        raise RuntimeError("没有可用的参考图（需要 --ref-front 或 --ref-side）")

    passed = all(v["pass"] for v in views)
    failures = [v for v in views if not v["pass"]]
    report = {
        "passed": bool(passed),
        "stage": stage,
        "thresholds": {"iou_min": iou_min, "aspect_tol": aspect_tol},
        "views": views,
        "failed_views": [v["view"] for v in failures],
        "reason": "；".join(
            "%s: iou %s (< %s) 或 宽高比误差 %s (> %s)" % (
                v["view"],
                v.get("iou"),
                iou_min,
                v.get("aspect_error"),
                aspect_tol,
            )
            for v in failures
        ),
    }

    report_path = os.path.join(outdir, "qa_gate.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("[门禁] 报告：%s" % report_path)
    return report


# ---------------------------------------------------------------- CLI

def _argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


VALUE_FLAGS = {
    "--outdir": "outdir",
    "--target": "target",
    "--collection": "collection",
    "--stage": "stage",
    "--iou-min": "iou_min",
    "--aspect-tol": "aspect_tol",
    "--ref-front": "ref_front",
    "--ref-side": "ref_side",
}


def parse_args(args):
    opts = {
        "blend": None,
        "outdir": None,
        "target": None,
        "collection": None,
        "gate": False,
        "stage": "final",
        "iou_min": None,
        "aspect_tol": None,
        "ref_front": None,
        "ref_side": None,
    }
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--gate":
            opts["gate"] = True
            i += 1
        elif arg in VALUE_FLAGS:
            if i + 1 >= len(args):
                raise RuntimeError("参数 %s 缺少值" % arg)
            key = VALUE_FLAGS[arg]
            value = args[i + 1]
            if key in ("iou_min", "aspect_tol"):
                value = float(value)
            opts[key] = value
            i += 2
        elif arg.endswith(".blend") and opts["blend"] is None:
            opts["blend"] = arg
            i += 1
        else:
            i += 1
    return opts


def main():
    try:
        opts = parse_args(_argv())
    except RuntimeError as exc:
        print("[错误] %s" % exc)
        sys.exit(2)

    if opts["blend"]:
        bpy.ops.wm.open_mainfile(filepath=opts["blend"])

    try:
        targets = _collect_targets(opts["target"], opts["collection"])
    except RuntimeError as exc:
        print("[错误] %s" % exc)
        sys.exit(2)
    if not targets:
        print("[错误] 场景里没有 MESH 对象")
        sys.exit(2)

    outdir = opts["outdir"] or os.path.join(
        os.path.dirname(bpy.data.filepath) or ".", "qa_render")
    os.makedirs(outdir, exist_ok=True)

    if opts["gate"]:
        refs = {}
        if opts["ref_front"]:
            refs["front"] = opts["ref_front"]
        if opts["ref_side"]:
            refs["side"] = opts["ref_side"]
        if not refs:
            print("[错误] --gate 需要至少一个参考图（--ref-front / --ref-side）")
            sys.exit(2)
        try:
            report = silhouette_gate(
                targets, outdir, refs,
                stage=opts["stage"],
                iou_min=opts["iou_min"],
                aspect_tol=opts["aspect_tol"],
            )
        except RuntimeError as exc:
            print("[错误] %s" % exc)
            sys.exit(2)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if report["passed"] else 1)

    for p in render_turntable(None, outdir, opts["target"], opts["collection"]):
        print("[渲染完成] %s" % p)


if __name__ == "__main__":
    main()
