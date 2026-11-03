"""
topology_audit.py — 网格拓扑深度审计（Blender 5.x / 4.x）

用法：
  blender --background --python scripts/topology_audit.py -- model.blend
  blender --background --python scripts/topology_audit.py -- model.blend --budget-tris 3000 --selection-only
  blender --background --python scripts/topology_audit.py -- model.blend --budget-tris 3000 --require-bevel
MCP 内：粘贴代码后调用 audit_scene()，返回 JSON。

检查项：
  V/E/F 数量、三角面/四边面/N-gon、松散顶点、非流形边、开放边、
  非均匀缩放（变换未应用）、最小/最大面面积、UV 层、材质槽、
  倒角（bevel）修改器/倒角权重（加 --require-bevel 时强制）、面数预算。
"""

import bpy
import bmesh
import sys
import json
import os


def audit_mesh(obj, budget_tris=None, require_bevel=False):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    n_v, n_e, n_f = len(bm.verts), len(bm.edges), len(bm.faces)
    tris = quads = ngons = 0
    n_face_loops = 0
    min_area = None
    max_area = 0.0
    ngon_samples = []
    for f in bm.faces:
        loops = len(f.loops)
        n_face_loops += loops
        if loops == 3:
            tris += 1
        elif loops == 4:
            quads += 1
        else:
            ngons += 1
            if len(ngon_samples) < 5:
                ngon_samples.append(f.index)
        area = f.calc_area()
        min_area = area if min_area is None else min(min_area, area)
        max_area = max(max_area, area)

    loose_verts = [v.index for v in bm.verts if not v.link_edges]
    # 非流形边：连接面数 != 2（边界边连接面数=1，单独列出）
    boundary_edges = 0
    non_manifold_edges = []
    for e in bm.edges:
        linked = len(e.link_faces)
        if linked == 1:
            boundary_edges += 1
        elif linked == 0 or linked > 2:
            if len(non_manifold_edges) < 10:
                non_manifold_edges.append(e.index)

    scale = tuple(round(v, 4) for v in obj.scale)
    scale_ok = all(abs(s - 1.0) < 1e-4 for s in scale)
    rotation = tuple(round(v, 6) for v in obj.rotation_euler)

    bevel_mods = [m.type for m in obj.modifiers if m.type == "BEVEL"]
    # 倒角权重：5.x 是 float 自定义层 "bevel_weight_edge"；旧版为 BMEdge.bevel_weight 属性
    bw_layer = bm.edges.layers.float.get("bevel_weight_edge")
    if bw_layer is not None:
        bevel_weight_edges = sum(1 for e in bm.edges if e[bw_layer] > 0.001)
    else:
        try:
            bevel_weight_edges = sum(1 for e in bm.edges if e.bevel_weight > 0.001)
        except AttributeError:
            bevel_weight_edges = 0
    has_uv = len(me.uv_layers) > 0
    materials = [m.name if m else None for m in me.materials]

    # 三角面总数（用于引擎面数预算）
    tri_count = n_face_loops - 2 * n_f

    dims = tuple(round(v, 4) for v in obj.dimensions)

    problems = []
    if ngons > 0:
        problems.append("存在 %d 个 N-gon（样例面索引 %s）" % (ngons, ngon_samples))
    if loose_verts:
        problems.append("松散顶点 %d 个" % len(loose_verts))
    if non_manifold_edges:
        problems.append("非流形边（样例 %s）" % non_manifold_edges)
    if not scale_ok:
        problems.append("缩放未应用：scale=%s" % (scale,))
    if not has_uv:
        problems.append("没有 UV 层（无法贴图）")
    if not materials:
        problems.append("没有材质槽")
    bevel_missing = not bevel_mods and bevel_weight_edges == 0
    # 只有硬表面资产才强制要求倒角：有机模型/雕像本来就没有可倒的硬边
    if require_bevel and bevel_missing and n_v > 8:
        problems.append("硬表面资产未发现倒角（bevel 修改器/倒角权重均无）：硬边在引擎里不会反光，显廉价")
    if budget_tris is not None and tri_count > budget_tris:
        problems.append("三角面 %d 超预算 %d" % (tri_count, budget_tris))
    if min_area is not None and min_area < 1e-8:
        problems.append("存在极小面（最小面积 %.2e），可能是穿插/重复顶点" % min_area)

    bm.free()

    return {
        "name": obj.name,
        "verts": n_v, "edges": n_e, "faces": n_f,
        "tris": tris, "quads": quads, "ngons": ngons,
        "tri_count": tri_count,
        "boundary_edges": boundary_edges,
        "non_manifold_edges_sample": non_manifold_edges,
        "loose_vert_count": len(loose_verts),
        "min_face_area": round(min_area, 8) if min_area is not None else None,
        "max_face_area": round(max_area, 8),
        "scale": scale,
        "rotation": rotation,
        "dims_xyz_m": dims,
        "has_uv": has_uv,
        "materials": materials,
        "bevel_required": require_bevel,
        "bevel_missing": bevel_missing,
        "bevel_modifiers": len(bevel_mods),
        "bevel_weighted_edges": bevel_weight_edges,
        "problems": problems,
        "pass": len(problems) == 0,
    }


def audit_scene(budget_tris=None, selection_only=False, include_refs=False,
                require_bevel=False):
    if selection_only:
        targets = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    else:
        targets = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not include_refs:
        # 默认跳过人体标尺/参考集合与不参与渲染的对象
        targets = [o for o in targets
                   if not o.hide_render and not o.name.startswith("REF_")]
    return [audit_mesh(o, budget_tris, require_bevel) for o in targets]


def _argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    args = _argv()
    blend = next((a for a in args if a.endswith(".blend")), None)
    if blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    budget = None
    if "--budget-tris" in args:
        budget = int(args[args.index("--budget-tris") + 1])
    selection_only = "--selection-only" in args
    include_refs = "--include-refs" in args
    require_bevel = "--require-bevel" in args
    report = audit_scene(budget, selection_only, include_refs, require_bevel)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    failed = [r for r in report if not r["pass"]]
    print("[审计] %d 个网格，%d 个有问题" % (len(report), len(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
