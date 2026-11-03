#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blender_asset_qa_render.py — 资产质检渲染（Beauty Shot）

用途：
  素材下载/清洗后，用统一灯光与取景自动出一张品质图，用来目检
  造型、贴图、金属/粗糙度、法线、比例是否正确。审计管数据，这个管眼睛。

命令行（headless，推荐）：
  blender --background --python blender_asset_qa_render.py -- "模型.fbx/glb/gltf/obj/blend" ["输出.png"] \
      [--hdri "C:/path/xxx.hdr"] [--res 1920x1080] [--az 42] [--el 14] [--lens 45] \
      [--samples 128] [--turntable 3]
  --hdri     可选，HDRI 路径；不给则用内置三点布光（无网络也能跑）
  --turntable N  可选，绕模型渲染 N 个角度（默认 1 个 3/4 视角）

MCP / execute_blender_code：
  全文粘贴，无参数时渲染「当前场景」，输出到 %TEMP%/qa_render.png；
  不修改用户场景，只加相机/补光（场景没有灯光时）。

兼容 Blender 4.2-5.x；EEVEE 引擎枚举、采样、光线追踪 API 跨版本做了容错。
"""

import argparse
import math
import os
import sys

from mathutils import Vector

# bpy 必须在模块级可见：mesh_objects/world_bounds/feet_on_ground/render_settings 都从
# 模块全局里找它。以前只在 __main__ 里 import，走 exec() 粘贴或 import 时就直接 NameError。
try:
    import bpy
except ImportError:  # 非 Blender 环境下允许被静态分析/测试导入
    bpy = None


# ---------------- 场景工具 ----------------

def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def world_bounds(objs):
    """返回 min/max/center/size（世界坐标）。"""
    from mathutils import Vector
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return (Vector(mn), Vector(mx),
            Vector([(mn[i] + mx[i]) / 2 for i in range(3)]),
            Vector([mx[i] - mn[i] for i in range(3)]))


def feet_on_ground(objs, z=0.0):
    """把无父级根对象整体平移，使网格最低点落到 z。"""
    bpy.context.view_layer.update()
    roots = [o for o in bpy.context.scene.objects if o.parent is None and o.type in
             ("MESH", "ARMATURE", "EMPTY")]
    if not roots:
        return
    mn, mx, _, _ = world_bounds(objs)
    dz = z - mn.z
    for o in roots:
        o.location.z += dz


def _background_node():
    return next((n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND"), None)


def set_neutral_world(gray=0.55, strength=1.0):
    """中性灰背景。"""
    if not bpy.context.scene.world:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    w = bpy.context.scene.world
    w.use_nodes = True
    bg = _background_node()
    if bg is None:
        out = next((n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD"), None)
        bg = w.node_tree.nodes.new("ShaderNodeBackground")
        if out:
            w.node_tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs[0].default_value = (gray, gray, gray, 1.0)
    bg.inputs[1].default_value = strength


def set_hdri_world(hdri_path, gray=0.55):
    """HDRI 照明+反射，相机射线看到中性灰背景。"""
    if not os.path.isfile(hdri_path):
        print("⚠ HDRI 不存在，改用三点布光: %s" % hdri_path)
        return False
    w = bpy.data.worlds.new("QA_World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg_env = nt.nodes.new("ShaderNodeBackground")
    bg_flat = nt.nodes.new("ShaderNodeBackground")
    bg_flat.inputs[0].default_value = (gray, gray, gray, 1.0)
    bg_flat.inputs[1].default_value = 1.0
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    img = bpy.data.images.load(hdri_path)
    img.colorspace_settings.name = "Linear Rec.709"
    env.image = img
    nt.links.new(env.outputs["Color"], bg_env.inputs["Color"])
    bg_env.inputs[1].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_env.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_flat.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return True


def add_ground(gray=0.55):
    """大尺寸哑光地面，与背景同色，边界自然衔接。"""
    name = "QA_Ground"
    if name in bpy.data.objects:
        return
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (gray, gray, gray, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = name
    g.data.materials.append(m)


def add_area(name, loc, rot, energy, size, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
    l = bpy.context.active_object
    l.name = name
    l.data.energy = energy
    l.data.shape = "DISK"
    l.data.size = size
    l.data.color = color
    return l


def add_three_point_lights():
    """无 HDRI 时的三点布光：主光（暖）、补光（冷）、轮廓光。"""
    if [o for o in bpy.context.scene.objects if o.type == "LIGHT"]:
        return
    add_area("QA_Key", (1.8, -2.2, 2.8), (math.radians(55), 0, math.radians(40)),
             350.0, 1.6, (1.0, 0.97, 0.92))
    add_area("QA_Fill", (-2.2, -1.2, 1.6), (math.radians(65), 0, math.radians(-45)),
             90.0, 3.0, (0.9, 0.95, 1.0))
    add_area("QA_Rim", (-1.2, 2.0, 2.6), (math.radians(40), 0, math.radians(200)),
             220.0, 1.2, (1.0, 1.0, 1.0))


def setup_camera(center, size, az_deg, el_deg, lens, res_x, res_y, bounds_objs=None):
    """按包围盒 8 个角点在相机空间的投影取景（含俯仰耦合），TrackTo 对准中心。"""
    az, el = math.radians(az_deg), math.radians(el_deg)
    sensor_x = 36.0
    sensor_y = sensor_x * res_y / res_x
    hfov = 2.0 * math.atan(sensor_x / (2.0 * lens))
    vfov = 2.0 * math.atan(sensor_y / (2.0 * lens))

    # 相机视线方向（朝 +Z 向的 -dir 看），用角点法精确取景
    dir_vec = Vector((math.sin(az) * math.cos(el),
                      -math.cos(az) * math.cos(el),
                      math.sin(el)))
    fwd = -dir_vec
    world_up = Vector((0, 0, 1))
    right = fwd.cross(world_up).normalized()
    cam_up = right.cross(fwd).normalized()

    if bounds_objs:
        mn, mx, _, _ = world_bounds(bounds_objs)
        corners = [
            Vector((x, y, z))
            for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)
        ]
        half_w = max(abs((c - center).dot(right)) for c in corners)
        half_h = max(abs((c - center).dot(cam_up)) for c in corners)
    else:
        half_w = max(size.x, size.y) / 2.0
        half_h = size.z / 2.0
    margin = 1.22
    d_w = half_w / math.tan(hfov / 2.0) * margin
    d_h = half_h / math.tan(vfov / 2.0) * margin
    dist = max(d_w, d_h)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=center)
    target = bpy.context.active_object
    target.name = "QA_Target"
    bpy.ops.object.camera_add(location=(center + dir_vec * dist))
    cam = bpy.context.active_object
    cam.name = "QA_Camera"
    cam.data.lens = lens
    c = cam.constraints.new("TRACK_TO")
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    c.target = target
    bpy.context.scene.camera = cam
    return cam


def render_settings(res_x, res_y, samples):
    scene = bpy.context.scene
    # EEVEE 的引擎标识符在 4.2 改名：4.2–4.5 是 BLENDER_EEVEE_NEXT，5.0+ 才回到
    # BLENDER_EEVEE。写死 "BLENDER_EEVEE" 在 4.2–4.5 会直接抛 TypeError。
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    try:
        scene.eevee.taa_render_samples = samples
    except Exception:
        pass
    for attr, val in [("use_gtao", True), ("use_shadow_jitter", True),
                      ("use_volumetric_shadows", True)]:
        try:
            setattr(scene.eevee, attr, val)
        except Exception:
            pass
    try:
        scene.eevee.ray_tracing_options.use_raytrace = True
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = -0.05


# ---------------- 主流程 ----------------

def qa_render(out_path, hdri=None, res=(1920, 1080), az=42, el=14, lens=45,
             samples=128, turntable=1, import_mode=False):
    objs = mesh_objects()
    if not objs:
        raise RuntimeError("场景里没有网格，无法渲染")

    if import_mode:
        # 导入的全新文件：落地、清场、打光
        feet_on_ground(objs)
        add_ground(0.55)
        if hdri and set_hdri_world(hdri):
            add_area("QA_Key", (1.8, -2.2, 2.8),
                     (math.radians(55), 0, math.radians(40)), 280.0, 1.6,
                     (1.0, 0.97, 0.92))
        else:
            set_neutral_world(0.55)
            add_three_point_lights()
    else:
        # MCP 当前场景：不改动用户的地/世界，只在没有灯时补三点光
        if not bpy.context.scene.world:
            set_neutral_world(0.55)
        add_three_point_lights()

    bpy.context.view_layer.update()
    mn, mx, center, size = world_bounds(objs)

    # 每个角度一张
    paths = []
    for i in range(turntable):
        angle = az + (360.0 / turntable) * i
        old = [o for o in bpy.context.scene.objects if o.name in ("QA_Camera", "QA_Target")]
        for o in old:
            bpy.data.objects.remove(o, do_unlink=True)
        setup_camera(center, size, angle, el, lens, res[0], res[1], bounds_objs=objs)
        render_settings(res[0], res[1], samples)
        if turntable == 1:
            p = out_path
        else:
            base, ext = os.path.splitext(out_path)
            p = "%s_%02d%s" % (base, i, ext)
        scene = bpy.context.scene
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
        print("已渲染 %s" % p)
    return paths


# ---------------- 入口（CLI / MCP 双模式） ----------------

def _import_model(path):
    """复用审计脚本的导入逻辑（支持 fbx/obj/glb/gltf/blend）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    audit_path = os.path.join(here, "blender_asset_audit.py")
    if os.path.isfile(audit_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("blender_asset_audit", audit_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.import_files([path])
    else:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".fbx",):
            bpy.ops.import_scene.fbx(filepath=path)
        elif ext in (".obj",):
            bpy.ops.wm.obj_import(filepath=path)
        elif ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".blend":
            bpy.ops.wm.open_mainfile(filepath=path)
        else:
            raise RuntimeError("不支持的格式: %s" % path)


def main():
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        argv = []

    if argv:
        ap = argparse.ArgumentParser(description="资产质检渲染")
        ap.add_argument("input", help="模型文件（fbx/glb/gltf/obj/blend）")
        ap.add_argument("output", nargs="?", default="", help="输出 PNG（默认与输入同目录）")
        ap.add_argument("--hdri", default=None, help="HDRI 路径（可选）")
        ap.add_argument("--res", default="1920x1080")
        ap.add_argument("--az", type=float, default=42.0, help="方位角（度）")
        ap.add_argument("--el", type=float, default=14.0, help="仰角（度）")
        ap.add_argument("--lens", type=float, default=45.0)
        ap.add_argument("--samples", type=int, default=128)
        ap.add_argument("--turntable", type=int, default=1, help="渲染角度数（默认 1）")
        a = ap.parse_args(argv)

        # 清场后导入
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                     bpy.data.cameras, bpy.data.images, bpy.data.worlds):
            for item in list(coll):
                coll.remove(item)
        _import_model(a.input)

        out = a.output or os.path.join(
            os.path.dirname(os.path.abspath(a.input)),
            os.path.splitext(os.path.basename(a.input))[0] + "_qa.png")
        rx, ry = (int(x) for x in a.res.lower().split("x"))
        qa_render(out, hdri=a.hdri, res=(rx, ry), az=a.az, el=a.el,
                  lens=a.lens, samples=a.samples, turntable=a.turntable,
                  import_mode=True)
        print("QA_RENDER_DONE")
    else:
        # MCP / execute_blender_code 粘贴模式：渲染当前场景
        out = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "qa_render.png")
        qa_render(out, import_mode=False)
        print("QA_RENDER_DONE %s" % out)


def _run_and_exit():
    """CLI 入口：任何异常都要变成非零退出码。

    Blender 的 --python-exit-code 默认是 0，异常只会打印 traceback 然后照样退 0，
    调用方（尤其是 CI / Agent）无法区分"渲染成功"和"炸了"。
    """
    try:
        main()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - 必须捕获一切才能保证退出码
        import traceback
        traceback.print_exc()
        print("[错误] 质检渲染失败：%s" % exc)
        sys.exit(1)


def _mcp_entry():
    """MCP execute_blender_code 粘贴模式：没有 __name__/argv，直接渲染当前场景。"""
    out = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "qa_render.png")
    qa_render(out, import_mode=False)
    print("QA_RENDER_DONE %s" % out)


if __name__ == "__main__":
    _run_and_exit()
else:
    # 被 exec() 粘贴执行时 __name__ 不存在，走兜底；被正常 import 时什么都不做。
    if globals().get("__name__") is None:
        _mcp_entry()
