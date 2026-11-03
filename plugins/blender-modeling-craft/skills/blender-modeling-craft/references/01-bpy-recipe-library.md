# 01 · bpy 建模配方库（MCP 内可直接粘贴的代码）

> 所有代码片段按"自包含、可重复执行"编写。每段独立运行，靠名字重新选择对象，不依赖上一段内存变量。Blender 5.2 实测：渲染引擎枚举 `BLENDER_EEVEE`；节点一律按类型查找（`n.type=="BSDF_PRINCIPLED"`），不要用名字。

## 0. 通用准备

```python
import bpy, math
from mathutils import Vector

def sel(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

def get(name):
    return bpy.data.objects.get(name)
```

## 1. 单位与人体标尺

```python
import sys
sys.path.insert(0, r"<技能路径>/scripts")
import model_helpers as mh
mh.ensure_units_metric()
rig = mh.build_human_scale_rig(1.70)          # 7.5 头身标尺，hide_render
box = mh.add_dim_box("SM_Crate", (0.5,0.5,0.5), (0,0,0.25))
print(mh.compare_to_known(box, "crate"))
```

## 2. 镜像（左右对称件，先开 Clipping）

```python
def add_mirror(obj, clipping=True):
    m = obj.modifiers.new("Mirror", "MIRROR")
    m.use_clip = clipping
    m.use_clip_merge_distance = 0.0001
    return m
```

## 3. 倒角（品质感的第一来源）

```python
def add_bevel(obj, width=0.002, segments=2, angle_limit=True):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE" if angle_limit else "NONE"
    m.angle_limit = math.radians(30)
    m.harden_normals = True                    # 倒角面之间硬化法线
    return m

def add_weighted_normals(obj):
    wn = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    return wn
```

修改器顺序：Mirror → Bevel → WeightedNormal → Subdivision（细分通常在倒角之后，按需）。

## 4. 细分曲面建模（卡线）

- 加 Subdivision Surface（Levels=2, Render=2）；细分前所有需要保持硬边的边缘加 Bevel 权重或环切卡线。
- 卡线距离 = 期望倒角宽度的 1.5–2 倍。
- 平面区域内不要留无意义的分段（Catmull-Clark 会把平面变鼓）。

```python
def add_subd(obj, levels=2):
    s = obj.modifiers.new("Subdivision", "SUBSURF")
    s.levels = levels; s.render_levels = levels
    return s

# 环切卡线（Edit 模式；clamp 0.9 防止越过）
def edge_loop_cut(obj, x_frac):
    sel([obj]); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.loopcut_slide(
        MESH_OT_loopcut={"number_cuts":1, "smoothness":0, "falloff":'INVERSE_SQUARE'},
        TRANSFORM_OT_edge_slide={"value":0, "clamp":True})
    bpy.ops.object.mode_set(mode="OBJECT")
```

## 5. 布尔：可以用，但必须善后

```python
def boolean_cut(target, cutter, op="DIFFERENCE"):
    m = target.modifiers.new("BoolCut", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"               # FAST 经常漏面
    sel([target]); bpy.ops.object.modifier_apply(modifier=m.name)
    # 善后：删除切割体、合并重复点、重算法线、清理 N-gon
    bpy.data.objects.remove(cutter, do_unlink=True)
    sel([target]); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0002)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
```

- 布尔后通常用以下两种方式修面：
  1. **三角化 N-gon → 手连四边面**（洞周围重新走线）。
  2. **Voxel remesh（≥1mm）→ Decimate(planar) 或 Quad Remesh**（复杂交错件最快）。
- 洞口边缘记得补倒角，否则洞边锐利显假。

## 6. 厚度（Solidify，防纸片）

```python
def add_solidify(obj, thickness=0.005):
    s = obj.modifiers.new("Solidify", "SOLIDIFY")
    s.thickness = thickness
    s.offset = -1.0                  # 向内加厚，不改外轮廓
    s.use_even_offset = True
    return s
```

## 7. 从高模到低模（Subdivision/高模 → 游戏面数）

- 细分模型不直接进引擎：先复制为 `_subd` 收藏，再做低模（Decimate 或手建），烘焙法线（见 04）。

```python
# Decimate 方案（规则硬表面慎用 Planar，有机件用 Collapse）
def decimate_collapse(obj, ratio=0.25):
    d = obj.modifiers.new("Decimate", "DECIMATE")
    d.decimate_type = "COLLAPSE"; d.ratio = ratio
    sel([obj]); bpy.ops.object.modifier_apply(modifier=d.name)
```

## 8. UV 展开

```python
def smart_uv(obj, angle_limit=66):
    sel([obj]); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(angle_limit),
        island_margin=0.003, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")

def mark_seams_from_sharp(obj):
    sel([obj]); bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(30))
    bpy.ops.mesh.mark_seam(clear=False)
    bpy.ops.object.mode_set(mode="OBJECT")
```

## 9. PBR 材质（按类型找节点，避免本地化坑）

```python
def make_pbr_material(name, base_color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

def connect_texture(mat, image_path, kind="BC"):
    """kind: BC 颜色 / N 法线 / RMA 金属粗糙度"""
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path)
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if kind == "BC":
        tex.image.colorspace_settings.name = "sRGB"
        nt.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])
    elif kind == "N":
        tex.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nmap.inputs["Color"], tex.outputs["Color"])
        nt.links.new(bsdf.inputs["Normal"], nmap.outputs["Normal"])
    elif kind == "RMA":
        tex.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateRGB")
        nt.links.new(sep.inputs["Image"], tex.outputs["Color"])
        nt.links.new(bsdf.inputs["Metallic"], sep.outputs["R"])
        nt.links.new(bsdf.inputs["Roughness"], sep.outputs["G"])
```

## 10. 应用变换、原点、命名（导出前必做）

```python
def finalize(obj, name, origin="BOTTOM_CENTER"):
    obj.name = name; obj.data.name = name
    sel([obj]); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # 原点：道具统一到底部几何中心（x,y 中心，z 最低点）
    if origin == "BOTTOM_CENTER":
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        obj.location.z = obj.location.z - obj.dimensions.z/2
    elif origin == "GEOMETRY":
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location.x = obj.location.y = 0.0
```

## 11. 分件与组织

- 每个零件独立命名（`SM_Chair_Leg_FL` 用前后左右后缀），材质/贴图分件按需合并。
- 全部零件放进一个 Collection，命名与资产一致；参考与标尺放 `REF_*`。
- 最终 join 前，每个零件先 Apply 全部修改器（join 只烘焙非活动对象的修改器，容易丢倒角）。

## 12. 常见 API 坑

| 坑 | 正确做法 |
|---|---|
| `primitive_cube_add(size=1)` 以为是 2m | 边长就是 1m；缩放值即尺寸（米），别除以 2 |
| 5.2 没有 `BLENDER_EEVEE_NEXT` | 用 `BLENDER_EEVEE` |
| 节点名中文环境 KeyError | 按 `n.type` 查找，不按名字 |
| 5.2 BMEdge 没有 bevel_weight | `bm.edges.layers.float.get("bevel_weight_edge")` |
| bpy.ops 报 context 错误 | 先 `sel([obj])` 并设 active；必要时包 `try/except` 并改用 data API |
| MCP 粘贴 180s 超时 | 拆成多块；每块按名字重选对象 |
| 中文路径贴图 | 导出前全部转英文命名 |
