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
# --- UTF-8 输出守卫：Windows 控制台默认 cp1252/cp936，print 中文会抛 UnicodeEncodeError ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
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
    # FBX/glTF 导入默认是 QUATERNION 模式，此时 rotation_euler 恒为 0。
    if obj.rotation_mode == "QUATERNION":
        rotation = tuple(round(v, 6) for v in obj.rotation_quaternion.to_euler())
    else:
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

    # 三角面总数（用于引擎面数预算）。
    # 必须按"求值后"的网格算：FBX 导出走的是 use_mesh_modifiers=True，
    # 带 Bevel/Subsurf 的模型按基础网格算会严重低报——而 --require-bevel 恰好
    # 在鼓励挂 Bevel 修改器，两者原本是互相打脸的。
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    eval_mesh = evaluated.to_mesh()
    try:
        tri_count = sum(max(len(p.vertices) - 2, 0) for p in eval_mesh.polygons)
        base_tri_count = n_face_loops - 2 * n_f
    finally:
        evaluated.to_mesh_clear()

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
        problems.append("三角面 %d 超预算 %d（已计入修改器；基础网格 %d）"
                        % (tri_count, budget_tris, base_tri_count))
    # 极小面按世界尺度判断：局部尺度很小的对象会把未应用的缩放算进面积，误报
    if min_area is not None and min_area < 1e-8 and scale_ok:
        problems.append("存在极小面（最小面积 %.2e），可能是穿插/重复顶点" % min_area)

    bm.free()

    return {
        "name": obj.name,
        "verts": n_v, "edges": n_e, "faces": n_f,
        "tris": tris, "quads": quads, "ngons": ngons,
        "tri_count": tri_count,
        "tri_count_base_mesh": base_tri_count,
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
        if not os.path.isfile(blend):
            print("[错误] 找不到 .blend 文件：%s" % blend)
            sys.exit(2)
        try:
            bpy.ops.wm.open_mainfile(filepath=blend)
        except RuntimeError as exc:
            print("[错误] 打开文件失败：%s" % exc)
            sys.exit(2)

    budget = None
    if "--budget-tris" in args:
        pos = args.index("--budget-tris")
        if pos + 1 >= len(args):
            print("[错误] --budget-tris 缺少数值")
            sys.exit(2)
        try:
            budget = int(args[pos + 1])
        except ValueError:
            print("[错误] --budget-tris 需要整数，收到：%r" % args[pos + 1])
            sys.exit(2)
        if budget <= 0:
            print("[错误] --budget-tris 必须为正数，收到：%d" % budget)
            sys.exit(2)

    selection_only = "--selection-only" in args
    include_refs = "--include-refs" in args
    require_bevel = "--require-bevel" in args

    report = audit_scene(budget, selection_only, include_refs, require_bevel)

    # 空目标集不等于"通过"。--background 下 --selection-only 选不中任何东西，
    # 旧的写法会打印"0 个网格，0 个有问题"并退 0——一次什么都没检查的绿灯。
    if not report:
        hint = "（--selection-only 在 --background 下通常选不中对象，去掉该参数）" \
            if selection_only else ""
        print("[错误] 没有可审计的 MESH 对象%s" % hint)
        sys.exit(2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    failed = [r for r in report if not r["pass"]]
    print("[审计] %d 个网格，%d 个有问题" % (len(report), len(failed)))
    for r in failed:
        print("  - %s: %s" % (r["name"], "; ".join(r["problems"])))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
