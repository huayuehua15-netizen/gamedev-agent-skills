# Blender MCP 操作手册（bpy 代码片段库）

> 目录：1. 执行约定 → 2. 导入导出 → 3. 检查与清洗 → 4. 材质与贴图通道 → 5. 减面与 LOD → 6. 碰撞与命名 → 7. 截图验证 → 8. 脚本使用说明
> 所有片段通过 `execute_blender_code` 执行；每条都会真正改场景，改前先备份。

## 1. 执行约定

- 每块代码都以 `import bpy` 开头；需要数学用 `from mathutils import ...`。
- 用 `print()` 输出结果，AI 用返回文本做判断；输出结构化 JSON 更稳。
- 优先用数据 API（`bpy.data`/`obj.data`），`bpy.ops` 依赖上下文，偶尔失败；必须用 ops 时先 `bpy.context.view_layer.objects.active = obj` 并选中。
- 坐标/尺寸单位：Blender 用公制米，1 单位 = 1m，与 Unity 一致；资产导入后用 `obj.dimensions` 核真实尺寸。

## 2. 导入与导出

```python
import bpy
# 清空当前独立场景（仅在专用导入场景里做）
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()

# 按格式导入（选其一）
bpy.ops.import_scene.fbx(filepath=r"C:\Imports\chair.fbx")
bpy.ops.wm.obj_import(filepath=r"C:\Imports\chair.obj")          # Blender 4.x：wm.obj_import
bpy.ops.import_scene.gltf(filepath=r"C:\Imports\chair.glb")
# .blend 用：bpy.ops.wm.append / link；.max Blender 原生无法打开，见 03/07

# 打印导入后的对象与整体尺寸
for o in bpy.context.scene.objects:
    print(o.name, o.type, tuple(round(v,3) for v in o.dimensions))
```

导出见 `scripts/blender_prep_unity.py`（已内置 Unity 正确 FBX 参数），核心参数（自己写时照抄）：

```python
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True,
    apply_unit_scale=True, global_scale=1.0,
    axis_forward='-Z', axis_up='Y',          # Unity FBX 标准轴向
    apply_scale_options='FBX_SCALE_ALL',
    mesh_smooth_type='FACE', use_mesh_modifiers=True,
    use_tspace=True,                          # 切线空间，法线贴图正确
    add_leaf_bones=False,                     # 去掉末端叶子骨，Unity Avatar 更干净
    bake_anim=False)                          # 带动画资产改 True，见 06
```

## 3. 检查与清洗（高频操作）

```python
import bpy, bmesh
# 应用全部变换（缩放/旋转必须应用，否则 Unity 里比例/轴错乱）
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# 原点移到几何中心（底部类资产用 cursor 到最低点再 origin to cursor）
for o in bpy.context.selected_objects:
    if o.type == 'MESH':
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# 重算法线（修复黑面/翻面）
for o in bpy.context.selected_objects:
    if o.type == 'MESH':
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)  # 4.1+ 旧版为 recalculate_normals
        bpy.ops.object.mode_set(mode='OBJECT')

# 删除松散点、合并重复点（去脏数据）
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.mesh.delete_loose()
bpy.ops.object.mode_set(mode='OBJECT')

# 清理孤立项（贴图/材质/网格残留）
bpy.ops.outliner.orphans_purge(do_recursive=True)

# 列出网格三角面数（评估预算）
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        print(o.name, 'tris=', sum(len(p.vertices)-2 for p in o.data.polygons))
```

## 4. 材质与贴图通道

- 外来素材先确认渲染器：导入的 glTF/Blender 资产用 Principled BSDF 即可；3ds Max 系 V-Ray/Corona 材质**不会**带过来，FBX 里常常只剩颜色，需要重新连 Principled BSDF。

```python
import bpy
mats = bpy.data.materials
for o in bpy.context.selected_objects:
    if o.type != 'MESH': continue
    for s in o.data.materials:
        if s and not s.use_nodes:
            s.use_nodes = True
        nt = s.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        # 自动把贴图节点按文件名接到 BSDF（_BC/_N/_RMA 等）
        for n in nt.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                nm = n.image.name.upper()
                if '_BC' in nm or '_D' in nm or '_ALBEDO' in nm:
                    nt.links.new(n.outputs['Color'], bsdf.inputs['Base Color'])
                elif '_N' in nm or '_NORMAL' in nm:
                    n.image.colorspace_settings.name = 'Non-Color'
                elif '_RMA' in nm or '_M' in nm or '_ORM' in nm:
                    n.image.colorspace_settings.name = 'Non-Color'
```

- 贴图色彩空间：颜色贴图（BaseColor/Albedo/Emissive）sRGB；法线、遮罩、粗糙度、金属、AO 一律 Non-Color（Linear）。
- 贴图文件路径改英文，避免中文路径导出后丢图。

## 5. 减面与 LOD

```python
import bpy
# 单资产减面（外来扫描/高模常用）
def decimate(obj, ratio):
    bpy.context.view_layer.objects.active = obj
    m = obj.modifiers.new('LOD', 'DECIMATE'); m.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=m.name)

# 生成 LOD 副本（不破坏原件）：LOD1=50% LOD2=25%
import copy
src = bpy.context.active_object
for i, ratio in enumerate([0.5, 0.25], start=1):
    dup = src.copy(); dup.data = src.data.copy()
    dup.name = src.name + f'_LOD{i}'
    bpy.context.collection.objects.link(dup)
    decimate(dup, ratio)
```

LOD 数量与百分比以 GDD 预算为准（常见三级：100%/50%/25%）；进 Unity 后挂 LODGroup（见 06）。

## 6. 碰撞与命名

- 简单碰撞在 Unity 里用 Box/Capsule 更省；复杂碰撞才需要网格。可在 Blender 里另建简化碰撞体并命名 `UCX_<网格名>`，Unity FBX 导入勾"Import Collision"会识别该前缀（多数版本）。
- 命名规范（与 GDD 一致）：
  - 网格 `SM_类别_名_01`；骨骼 `SK_名`；
  - 贴图 `T_名_BC`（颜色）、`T_名_N`（法线）、`T_名_M`（金属/平滑遮罩，URP）或 `T_名_RMA`（HDRP/AO-R-M）；
  - 材质 `M_名`、材质实例 `MI_名`；碰撞 `UCX_名`。

```python
import bpy
for o in bpy.context.selected_objects:
    if o.type == 'MESH' and not o.name.startswith('SM_'):
        o.name = 'SM_Prop_' + o.name
        o.data.name = o.name
```

## 7. 截图验证（每步必做）

```python
import bpy
# 框选所有对象到视角
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for region in area.regions:
            if region.type == 'WINDOW':
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_all()
```

之后调用 `get_viewport_screenshot(max_size=800)` 看图：比例、朝向、重叠、贴图是否就位。导入素材后还必须核对 `world_bounding_box`/`dimensions`，防止穿模或尺寸离谱。

## 8. 本技能脚本的两种用法

**MCP 内**：把 `scripts/blender_asset_audit.py` 全文粘贴进 `execute_blender_code` 执行（审计当前场景）；或粘贴 `blender_prep_unity.py` 后在同一代码块末尾调用 `prep_and_export(r"C:\...\SM_x.fbx", anim=False)`。

**命令行**（脚本已内置 argparse，支持 `--` 后传文件路径）：
```powershell
& "D:\Blender\blender.exe" --background --python scripts/blender_asset_audit.py -- "C:\Imports\chair.fbx"
& "D:\Blender\blender.exe" --background --python scripts/blender_prep_unity.py -- "C:\Imports\chair.fbx" "C:\Imports\clean\SM_chair.fbx"
```
