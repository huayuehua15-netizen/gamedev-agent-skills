"""
model_helpers.py — 建模前期与比例控制工具（Blender 5.x / 4.x 通用）

两种用法：
1. MCP 内：整段粘贴执行，然后调用函数（参考图片、尺寸基元、人体标尺）。
2. 命令行：
   blender --background --python scripts/model_helpers.py -- --build-scale-rig
   blender --background --python scripts/model_helpers.py -- model.blend --measure
   blender --background --python scripts/model_helpers.py -- --reference front path/to/front.png

铁律：Blender 1 单位 = 1 米。primitive_cube_add(size=1) 的立方体边长就是 1m。
"""

import bpy
import math
import sys
# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
import json

# ---------------- 场景单位与集合 ----------------

def ensure_units_metric():
    """统一公制：单位米、1.0 比例；length 显示 m。"""
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    return scene


def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def move_to_collection(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


# ---------------- 参考图（必须先做） ----------------

def add_reference_image(filepath, view="front", alpha=0.5, size=2.0, location=None):
    """
    导入正投影视图参考图（Image Empty）。
    view：front / side / top
    - front：图像竖在 XZ 平面，法线朝 +Y（镜头从 -Y 看向 +Y）
    - side：竖在 YZ 平面，法线朝 +X
    - top：平铺 XY 平面
    location 不传时默认放在原点后方，不挡住建模。
    """
    img = bpy.data.images.load(filepath)
    empty = bpy.data.objects.new("REF_%s_%s" % (view.title(), img.name), None)
    empty.empty_display_type = "IMAGE"
    empty.data = img
    empty.empty_display_size = size
    empty.use_empty_image_alpha = True
    empty.color[3] = alpha
    if view == "front":
        empty.rotation_euler = (math.radians(90), 0.0, 0.0)
        location = location or (0.0, 1.0, size * 0.5)
    elif view == "side":
        empty.rotation_euler = (math.radians(90), 0.0, math.radians(90))
        location = location or (-1.0, 0.0, size * 0.5)
    else:
        empty.rotation_euler = (0.0, 0.0, 0.0)
        location = location or (0.0, 0.0, 0.0)
    empty.location = location
    col = get_collection("REF_References")
    col.objects.link(empty)
    empty.show_empty_image_perspective = False  # 正交显示，避免近大远小干扰比例
    return empty


# ---------------- 尺寸驱动的基元（blockout 阶段） ----------------

def add_dim_box(name, size, location=(0, 0, 0), collection=None, material=None):
    """边长 = size（米）的立方体。size 可为 (x, y, z) 或单值。"""
    if isinstance(size, (int, float)):
        sx = sy = sz = float(size)
    else:
        sx, sy, sz = size
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if material:
        _assign_material(obj, material)
    if collection:
        move_to_collection(obj, collection)
    return obj


def add_dim_cylinder(name, radius, depth, location=(0, 0, 0), vertices=24,
                     collection=None, material=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    if material:
        _assign_material(obj, material)
    if collection:
        move_to_collection(obj, collection)
    return obj


def add_dim_sphere(name, radius, location=(0, 0, 0), segments=24, rings=12,
                   collection=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    if collection:
        move_to_collection(obj, collection)
    return obj


def _assign_material(obj, mat):
    mat = mat if isinstance(mat, bpy.types.Material) else bpy.data.materials.get(mat)
    if mat:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)


# ---------------- 人体标尺（比例校验神器） ----------------

def build_human_scale_rig(height=1.70, at=(0, 0, 0), collection_name="REF_HumanScale"):
    """
    7.5 头身比例的简易人形标尺（头=身高/7.5）。
    用于和道具并排判断"真实比例"。默认不参与渲染（hide_render）。
    """
    col = get_collection(collection_name)
    head = height / 7.5
    hx, hy, hz = at
    # 名称, 尺寸(x,y,z), 中心高度, 左右偏移（0=居中）
    # 头顶必须正好落在 height 上：头部中心 = height - 头高/2。
    # （旧值是 7.0*head+0.10，实测算出 1.79m，比标称的 1.70m 高 9cm。）
    head_box_h = head * 0.90
    parts = [
        ("REF_Head",     (0.11, 0.13, head_box_h),   height - head_box_h / 2.0, 0.0),
        ("REF_Neck",     (0.07, 0.07, 0.10),         6.55 * head,       0.0),
        ("REF_Torso",    (0.40, 0.20, 2.4 * head),   5.1 * head,        0.0),
        ("REF_Pelvis",   (0.30, 0.18, 0.8 * head),   3.6 * head,        0.0),
        ("REF_LegUpper", (0.11, 0.12, 1.8 * head),   2.4 * head,        0.09),
        ("REF_LegLower", (0.09, 0.10, 1.7 * head),   0.9 * head,        0.09),
        ("REF_Foot",     (0.10, 0.27, 0.08),         0.04,              0.09),
        ("REF_ArmUpper", (0.09, 0.09, 1.3 * head),   5.6 * head,        0.26),
        ("REF_ArmLower", (0.08, 0.08, 1.2 * head),   4.35 * head,       0.26),
    ]
    created = []
    for name, dims, z, off in parts:
        obj = add_dim_box(name, dims, (hx - off, hy, hz + z), collection=col)
        obj.hide_render = True
        created.append(obj)
        if off > 0:
            mirror = obj.copy()
            mirror.data = obj.data
            mirror.name = name.replace("REF_", "REF_R", 1)
            mirror.location.x = hx + off
            mirror.hide_render = True
            col.objects.link(mirror)
            created.append(mirror)
    return created


# ---------------- 测量与对比 ----------------

def measure_object(obj):
    """返回世界空间尺寸（米）与缩放。"""
    return {
        "name": obj.name,
        "dims_xyz_m": tuple(round(v, 4) for v in obj.dimensions),
        "height_m": round(obj.dimensions.z, 4),
        "scale": tuple(round(v, 4) for v in obj.scale),
    }


# 常见真实尺寸（米）；权威完整表见 assets/real-world-dimensions.csv
KNOWN_DIMENSIONS = {
    "door":        (0.90, 0.05, 2.10),
    "chair":       (0.45, 0.45, 0.90),
    "desk":        (1.20, 0.60, 0.75),
    "crate":       (0.50, 0.50, 0.50),
    "barrel":      (0.58, 0.58, 0.90),
    "stairs_step": (0.28, 0.90, 0.17),
    "room_height": (4.0, 4.0, 2.70),
    "bottle":      (0.08, 0.08, 0.25),
    "mug":         (0.08, 0.08, 0.10),
    "sword":       (0.10, 0.04, 1.00),
    "rifle":       (0.08, 0.10, 0.95),
    "car":         (4.6, 1.8, 1.5),
}


def compare_to_known(obj, kind):
    """粗判比例是否离谱：每个维度偏离真实值 ±30% 给出警告。"""
    if kind not in KNOWN_DIMENSIONS:
        return None
    target = KNOWN_DIMENSIONS[kind]
    actual = obj.dimensions
    issues = []
    for axis, a, t in zip("xyz", actual, target):
        if t and (a < t * 0.7 or a > t * 1.3):
            issues.append("%s 轴 %.2fm，真实约 %.2fm" % (axis, a, t))
    return {"name": obj.name, "kind": kind, "ok": not issues, "issues": issues}


# ---------------- CLI ----------------

def _argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    args = _argv()
    blend = next((a for a in args if a.endswith(".blend")), None)
    if blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    ensure_units_metric()
    if "--build-scale-rig" in args:
        build_human_scale_rig()
        out = bpy.data.filepath.replace(".blend", "_scalerig.blend")
        if not out:
            out = "scale_rig.blend"
        bpy.ops.wm.save_as_mainfile(filepath=out)
        print("[完成] 已在 %s 建人体标尺集合 REF_HumanScale" % out)
    elif "--measure" in args:
        report = []
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and not obj.name.startswith("REF_"):
                report.append(measure_object(obj))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif "--reference" in args:
        i = args.index("--reference")
        view, path = args[i + 1], args[i + 2]
        obj = add_reference_image(path, view=view)
        print("[完成] 参考图已导入：%s" % obj.name)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
