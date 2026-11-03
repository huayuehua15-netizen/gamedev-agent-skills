#!/usr/bin/env python3
"""
Blender 素材审计脚本（Unity + Blender MCP 管线）

两种用法：
1. MCP 内：把本文件全文粘贴进 execute_blender_code 执行——审计当前场景并打印 JSON。
2. 命令行：
   blender --background --python blender_asset_audit.py -- "C:\\path\\asset.fbx"
   （支持 .fbx .obj .glb .gltf .stl .dae .blend，可一次传多个）

输出：===AUDIT_JSON_START=== 与 ===AUDIT_JSON_END=== 之间的 JSON 报告。
脚本只读，不修改场景。
"""

import bpy
import json
import math
import os
import sys

SUPPORTED_IMPORT = {
    ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
    ".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".stl": None,  # 4.2 起旧的 import_mesh.stl 下线，改用 wm.stl_import
    ".dae": lambda p: bpy.ops.wm.collada_import(filepath=p),
    ".obj": None,  # 4.x 用 wm.obj_import，3.x 用 import_scene.obj，运行时解析
}


def _stl_import(path):
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)


def _obj_import(path):
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.obj(filepath=path)


def _reset_scene():
    """清空场景与数据块（审计专用，先导入再审计）。"""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for block in list(coll):
            coll.remove(block)


def import_files(files):
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext == ".blend":
            # 直接打开工程文件（后续审计仍会执行）
            bpy.ops.wm.open_mainfile(filepath=f)
            continue
        if ext == ".obj":
            _obj_import(f)
        elif ext == ".stl":
            _stl_import(f)
        elif ext in SUPPORTED_IMPORT:
            SUPPORTED_IMPORT[ext](f)
        else:
            raise ValueError(f"不支持的格式: {ext} ({f})")


def _tri_count(mesh):
    return sum(max(len(p.vertices) - 2, 0) for p in mesh.polygons)


def _world_bounds(objects):
    import mathutils
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    found = False
    for o in objects:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            found = True
            for i in range(3):
                mn[i] = min(mn[i], wc[i])
                mx[i] = max(mx[i], wc[i])
    if not found:
        return None
    return {
        "min": [round(v, 4) for v in mn],
        "max": [round(v, 4) for v in mx],
        "size_m": [round(mx[i] - mn[i], 4) for i in range(3)],
    }


def audit_report():
    warnings = []
    objects_out = []
    total_tris = 0
    rigged = 0

    for o in bpy.context.scene.objects:
        # FBX / glTF 导入默认是 QUATERNION 旋转模式，此时 rotation_euler 恒为 0。
        # 只读 euler 会把"旋转未应用"这个最关键的导入问题全部漏掉，所以按模式取值。
        if o.rotation_mode == "QUATERNION":
            rot_deg = [round(math.degrees(a), 3) for a in o.rotation_quaternion.to_euler()]
        else:
            rot_deg = [round(math.degrees(a), 3) for a in o.rotation_euler]

        item = {
            "name": o.name,
            "type": o.type,
            "location": [round(v, 4) for v in o.location],
            "rotation_euler_deg": rot_deg,
            "scale": [round(v, 4) for v in o.scale],
            "dimensions_m": [round(v, 4) for v in o.dimensions],
        }
        if any(abs(s - 1.0) > 0.001 for s in o.scale):
            warnings.append(f"对象 {o.name} 缩放未应用（scale != 1）")
        if any(abs(v) > 0.001 for v in rot_deg):
            warnings.append(f"对象 {o.name} 旋转未应用（旋转角 != 0）")

        if o.type == "MESH":
            mesh = o.data
            tris = _tri_count(mesh)
            total_tris += tris
            mats = [m.name if m else None for m in o.data.materials]
            uvs = [uv.name for uv in mesh.uv_layers]
            mods = [m.type for m in o.modifiers]
            has_arm = any(m.type == "ARMATURE" for m in o.modifiers)
            if has_arm:
                rigged += 1
            if not uvs:
                warnings.append(f"网格 {o.name} 没有 UV 层")
            if tris > 100000:
                warnings.append(f"网格 {o.name} 三角面 {tris} 超过 10 万，需减面/LOD")
            item.update({
                "verts": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "tris": tris,
                "materials": mats,
                "uv_layers": uvs,
                "modifiers": mods,
                "rigged": has_arm,
            })
        elif o.type == "ARMATURE":
            item["bones"] = len(o.data.bones)
        objects_out.append(item)

    # 材质与贴图
    materials_out = []
    for m in bpy.data.materials:
        mat = {"name": m.name, "use_nodes": m.use_nodes, "textures": []}
        if m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    img = n.image
                    missing = bool(img.filepath) and not img.packed_file and not os.path.isfile(
                        bpy.path.abspath(img.filepath))
                    cs = img.colorspace_settings.name if img.colorspace_settings else "?"
                    lower = img.name.lower()
                    data_tex = any(k in lower for k in
                                   ("_n", "_normal", "_nrm", "_rma", "_orm", "_m", "_ao",
                                    "_rough", "_metal", "_mask"))
                    # Blender 4.x 的 OCIO 色彩空间名是 "sRGB" / "Non-Color" /
                    # "Linear Rec.709"，不是 ICC 的 "sRGB IEC61966-2.1"；
                    # 旧比较永远不成立，这条唯一的贴图校验形同虚设。
                    is_srgb = cs.lower().startswith("srgb")
                    if data_tex and is_srgb:
                        warnings.append(f"贴图 {img.name} 疑似数据贴图但色彩空间是 {cs}")
                    if missing:
                        warnings.append(f"材质 {m.name} 的贴图 {img.name} 文件丢失: {img.filepath}")
                    mat["textures"].append({
                        "image": img.name,
                        "filepath": img.filepath,
                        "colorspace": cs,
                        "packed": bool(img.packed_file),
                        "missing_on_disk": missing,
                    })
        materials_out.append(mat)

    # 动画片段
    actions = [
        {"name": a.name,
         "frame_start": round(a.frame_range[0], 2),
         "frame_end": round(a.frame_range[1], 2),
         "frames": round(a.frame_range[1] - a.frame_range[0], 2)}
        for a in bpy.data.actions
    ]

    mesh_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    report = {
        "blender_version": bpy.app.version_string,
        "unit": {
            "system": bpy.context.scene.unit_settings.system,
            "scale_length": bpy.context.scene.unit_settings.scale_length,
        },
        "counts": {
            "objects": len(bpy.context.scene.objects),
            "meshes": len(mesh_objs),
            "materials": len(bpy.data.materials),
            "armatures": len([o for o in bpy.context.scene.objects if o.type == "ARMATURE"]),
            "rigged_meshes": rigged,
            "actions": len(actions),
        },
        "total_tris": total_tris,
        "world_bounds_m": _world_bounds(bpy.context.scene.objects),
        "actions": actions,
        "objects": objects_out,
        "materials": materials_out,
        "warnings": warnings,
    }
    return report


AUDIT_JSON_START = "===AUDIT_JSON_START==="
AUDIT_JSON_END = "===AUDIT_JSON_END==="


def run_cli():
    """CLI 入口：无论成功失败都要给出确定的结果。

    - 没有 `--` 参数时直接报错退出，不再默默审计 Blender 启动场景（默认为一个
      Cube/Camera/Light），那会产出一份格式合法但内容完全错误的"体检通过"。
    - 有任何 warning 或导入失败 → 退出码 1，让 CI 和 Agent 能真的拦住问题。
    """
    argv = sys.argv
    files = argv[argv.index("--") + 1:] if "--" in argv else []
    if not files:
        print("[错误] 需要通过 `--` 传入至少一个模型文件，"
              "例如：blender --background --python blender_asset_audit.py "
              "-- --python-exit-code 1 -- asset.fbx")
        return 2
    try:
        _reset_scene()
        import_files(files)
        report = audit_report()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("[错误] 审计失败：%s" % exc)
        return 1
    print(AUDIT_JSON_START)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(AUDIT_JSON_END)
    return 1 if report.get("warnings") else 0


if __name__ == "__main__":
    sys.exit(run_cli())
