#!/usr/bin/env python3
"""
Blender 素材清洗 + Unity 标准 FBX 导出脚本（Unity + Blender MCP 管线）

两种用法：
1. MCP 内：把本文件全文粘贴进 execute_blender_code（仅加载函数，不改动场景），
   然后在同一代码块或下一块选择对象并调用：
       prep_and_export(r"C:\\Imports\\SM_chair.fbx")                 # 静态
       prep_and_export(r"C:\\Imports\\SK_hero.fbx", anim=True)       # 角色/动画
   只处理传入对象（默认当前选中），绝不删除未选中的摄像机/灯光。

2. 命令行（会新建空白场景导入源文件、清洗后导出，原件不动）：
   blender --background --python blender_prep_unity.py -- 输入文件 [输出FBX] [--anim]
   例：
   blender --background --python blender_prep_unity.py -- "C:\\in\\chair.fbx"
   blender --background --python blender_prep_unity.py -- "C:\\in\\hero.fbx" "C:\\out\\SK_hero.fbx" --anim
"""

import bpy
import os
import sys

# 复用审计脚本的导入表（同目录），找不到时用本地兜底
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from blender_asset_audit import _reset_scene, import_files  # noqa: F401
except Exception:  # MCP 粘贴时没有文件路径，import 失败就用兜底
    import math  # noqa

    def _reset_scene():
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)

    def import_files(files):
        raise RuntimeError("命令行导入需要 blender_asset_audit.py 同目录，请检查技能文件")


def _mesh_objects(objs):
    return [o for o in objs if o.type in ("MESH", "ARMATURE", "EMPTY")]


def apply_transforms(objs):
    """应用旋转与缩放（位置不应用）。"""
    bpy.context.view_layer.update()  # 直接赋值过 scale/rotation 时必须先刷新依赖图
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        if o.type in ("MESH", "ARMATURE"):
            o.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def recalc_normals(objs):
    """重算法线 + 合并重复点 + 删松散点。"""
    for o in objs:
        if o.type != "MESH":
            continue
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.mesh.delete_loose()
        try:
            bpy.ops.mesh.normals_make_consistent(inside=False)
        except AttributeError:
            bpy.ops.mesh.recalculate_normals()  # 旧版 Blender
        bpy.ops.object.mode_set(mode="OBJECT")


def set_origins(objs, mode="GEOMETRY"):
    """
    GEOMETRY：道具，原点到几何中心（跳过蒙皮网格，避免破坏骨架绑定）。
    FEET：角色，整体（骨架+网格）原点移到底面中心，再把骨架根放到世界原点。
    注意：角色动作若已烘焙根运动，应在动画制作阶段就保证根在原点；本步骤只做静态归位。
    """
    import mathutils
    meshes = [o for o in objs if o.type == "MESH"]
    rig = next((o for o in objs if o.type == "ARMATURE"), None)

    if mode == "FEET" and rig is not None and meshes:
        # 只按网格（可见几何体）算包围盒，避免把骨头末端算进去
        mn = [float("inf")] * 3
        mx = [float("-inf")] * 3
        for o in meshes:
            for corner in o.bound_box:
                w = o.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    mn[i] = min(mn[i], w[i])
                    mx[i] = max(mx[i], w[i])
        bottom = ((mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0, mn[2])
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            if o.type in ("MESH", "ARMATURE"):
                o.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.context.scene.cursor.location = bottom
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        rig.location = (0.0, 0.0, 0.0)
        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
        return

    # GEOMETRY（道具）：蒙皮网格不单独动原点
    for o in meshes:
        if o.parent and o.parent_type == "ARMATURE":
            continue
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")


def purge_orphans():
    bpy.ops.outliner.orphans_purge(do_recursive=True)


def prep_and_export(out_path, anim=False, objs=None, origin="GEOMETRY",
                    normalize_names=False, clean=False):
    """
    清洗选中对象并导出 Unity FBX。
    - objs：要处理的对象列表，默认当前选中；选中为空时取全部网格/骨架。
    - origin：GEOMETRY（道具）或 FEET（角色）。
    - normalize_names：True 时给网格补 SM_ 前缀、骨架补 SK_ 前缀。
    - clean：仅命令行场景使用 True，会删除未选中的摄像机/灯光/空组；MCP 内不要开。
    返回导出参数说明文本。
    """
    if objs is None:
        objs = [o for o in bpy.context.selected_objects]
    if not objs:
        objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "ARMATURE")]
    if not objs:
        raise RuntimeError("没有可导出的网格/骨架对象")

    names = [o.name for o in objs]

    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]

    # 1. 清理未选中的杂项（仅 CLI 模式）
    if clean:
        for o in list(bpy.context.scene.objects):
            if o not in objs and o.type in ("CAMERA", "LIGHT", "EMPTY"):
                bpy.data.objects.remove(o, do_unlink=True)

    # 2. 应用变换、修法线、归位原点
    apply_transforms(objs)
    recalc_normals(objs)
    set_origins(objs, mode=origin)

    # 3. 规范化命名
    if normalize_names:
        for o in objs:
            if o.type == "MESH" and not o.name.startswith(("SM_", "UCX_")):
                o.name = "SM_Prop_" + o.name
                o.data.name = o.name
            elif o.type == "ARMATURE" and not o.name.startswith("SK_"):
                o.name = "SK_" + o.name

    # 4. 重新选中（origin_set 可能改变选择）
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    # 5. 导出 Unity 标准 FBX
    common = dict(
        filepath=out_path,
        use_selection=True,
        apply_unit_scale=True,
        global_scale=1.0,
        axis_forward="-Z",
        axis_up="Y",
        apply_scale_options="FBX_SCALE_ALL",
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        use_tspace=True,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
    )
    if anim:
        bpy.ops.export_scene.fbx(
            object_types={"ARMATURE", "MESH"},
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True,
            **common)
    else:
        bpy.ops.export_scene.fbx(
            object_types={"MESH", "EMPTY"},
            bake_anim=False,
            **common)

    purge_orphans()
    size = os.path.getsize(out_path) if os.path.isfile(out_path) else 0
    msg = (f"已导出 {out_path}（{size/1024:.0f} KB）\n"
           f"对象：{names}\n动画：{'烘焙' if anim else '不烘焙'}\n"
           f"轴向：-Z forward / Y up；global_scale=1；add_leaf_bones=False；use_tspace=True")
    print(msg)
    return msg


def main():
    argv = sys.argv
    if "--" not in argv:
        print("blender_prep_unity.py 已加载：在 MCP 中调用 prep_and_export(...)；"
              "命令行请用 -- 输入文件 [输出FBX] [--anim]")
        return
    args = argv[argv.index("--") + 1:]
    if not args:
        raise SystemExit("缺少输入文件")
    src = args[0]
    anim = "--anim" in args
    positional = [a for a in args[1:] if a != "--anim"]
    if positional:
        out = positional[0]
    else:
        base = os.path.splitext(os.path.basename(src))[0]
        prefix = "SK_" if anim else "SM_"
        out = os.path.join(os.path.dirname(os.path.abspath(src)),
                           prefix + base + ".fbx")

    _reset_scene()
    import_files([src])
    objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "ARMATURE")]
    prep_and_export(out, anim=anim, objs=objs,
                    origin="FEET" if anim else "GEOMETRY",
                    normalize_names=False, clean=True)


try:
    _name = __name__  # 兼容 MCP 插件 exec 时未注入 __name__ 的情况
except NameError:
    _name = ""

if _name == "__main__":
    main()
