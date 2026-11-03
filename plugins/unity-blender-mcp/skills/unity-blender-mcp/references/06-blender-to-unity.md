# Blender → Unity 标准管线

> 目录：1. 单位与比例 → 2. FBX 导出参数 → 3. 贴图通道（URP/HDRP 差异，重点）→ 4. 贴图打包脚本 → 5. Unity 模型导入设置 → 6. 材质接线 → 7. 碰撞与 LOD → 8. 角色/动画（Mixamo→Humanoid）→ 9. Lightmap UV 与静态 → 10. 目录结构

## 1. 单位与比例（90% 的"大小/朝向错乱"源于此）

- Blender：Metric，Unit Scale = 1.0；1 单位 = 1 米，与 Unity 一致。
- 导出前**应用 Rotation & Scale**（Location 不应用），原点归位。
- 资产真实尺寸参考：门 2.0m、门框 2.05-2.15m、椅子座高 0.45m、桌高 0.75m、栏杆 1.05m、成年男性 1.70-1.80m。
- 外来素材尺寸乱（Sketchfab 常见巨大化）：导入后用尺寸参照缩放再应用，不要靠 Unity 里的 Scale 补偿。

## 2. FBX 导出参数（脚本已固化，勿手改）

```python
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True,
    apply_unit_scale=True, global_scale=1.0,
    axis_forward='-Z', axis_up='Y',          # 自动把 Blender Z-up 转 Unity Y-up
    apply_scale_options='FBX_SCALE_ALL',
    mesh_smooth_type='FACE',                 # 按面输出平滑组
    use_mesh_modifiers=True,
    use_tspace=True,                         # 切线空间
    add_leaf_bones=False,                    # 不加叶子骨
    primary_bone_axis='Y', secondary_bone_axis='X',
    bake_anim=False)                         # 动画资产 True，见第 8 节
```

- 静态资产：`bake_anim=False`，只导网格（含碰撞体 UCX_ 前缀对象）。
- 只导选中对象：先在 Blender 选好要导出的集合，避免把摄像机灯光带进 Unity。

## 3. 贴图通道：URP 与 HDRP 不一样（重点，别接错）

- **法线**：Blender 是 OpenGL 约定（绿通道向上），Unity 也是 OpenGL——直接用没问题；如果素材是 DirectX 法线（绿向下），在 Blender 翻转绿色再导。
- **颜色贴图**：sRGB；法线/金属/粗糙度/AO/遮罩：Linear(Non-Color)。

### URP（Lit / Universal Render Pipeline）

| 贴图（命名） | 通道 | 连接 |
|---|---|---|
| `T_名_BC` | RGB 颜色 | `_BaseMap`（sRGB） |
| `T_名_M` | **R=Metallic，A=Smoothness（=1−Roughness）** | `_MetallicGlossMap`（Linear） |
| `T_名_AO` | G 通道放 AO | `_OcclusionMap`（Linear） |
| `T_名_N` | 法线 | `_BumpMap`（Linear） |
| `T_名_E` | 自发光 | `_EmissionMap`（sRGB） |

注意：URP 金属遮罩读 **R=金属、A=平滑**，不是 G！若 `_SmoothnessTextureChannel` 设为 1 才改读 BaseMap 的 Alpha。

### HDRP（Lit）

| 贴图（命名） | 通道 | 连接 |
|---|---|---|
| `T_名_BC` | RGB | `_BaseColorMap` |
| `T_名_Mask` | **R=Metallic，G=AO，B=Detail Mask（无则填 1），A=Smoothness（1−Roughness）** | `_MaskMap` |
| `T_名_N` | 法线 | `_NormalMap` |
| `T_名_E` | 自发光 | `_EmissiveColorMap` |

> ⚠️ HDRP 的 Mask Map 通道顺序与 URP **完全不同**，和平常说的 ORM 也不一样。照抄 URP 或 ORM 的顺序会把金属度和 AO 对调、把平滑度塞进 Detail Mask 槽，材质会明显发暗/发金属。以 [Unity HDRP 官方文档](https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@17.4/manual/Mask-Map-and-Detail-Map.html) 为准：**R=Metallic、G=Ambient Occlusion、B=Detail Mask、A=Smoothness**。

- 外部素材常见的 **glTF/ORM 贴图**是 R=AO、G=Roughness、B=Metallic（Blender 导出的标准）。进 URP/HDRP 都要重排通道：粗糙度要取反成平滑度。用第 4 节脚本一键转。

## 4. 贴图通道打包（bpy + numpy，零外部依赖）

```python
import bpy, numpy as np

def _load(p):
    img = bpy.data.images.load(p, check_existing=True)
    img.colorspace_settings.name = 'Non-Color'
    return img

def _arr(img):
    w, h = img.size
    return np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)

def pack_urp(base_dir, name, metal=None, rough=None, ao=None):
    # 金属/粗糙度/AO 可选；缺省金属=0、平滑=0.5、AO=1
    ch = 4
    metal_a = _arr(_load(metal))[...,0] if metal else np.zeros((1,1))
    rough_a = _arr(_load(rough))[...,0] if rough else np.full((1,1), 0.5)
    ao_a    = _arr(_load(ao))[...,0] if ao else np.ones((1,1))
    h, w = max(metal_a.shape, rough_a.shape, ao_a.shape)
    def fit(a):
        if a.shape == (h,w): return a
        im = bpy.data.images.new('t', w, h, alpha=False)
        src = bpy.data.images.new('s', *a.shape[::-1], alpha=False)
        src.pixels = np.repeat(a, 4, axis=1).flatten()
        src.scale(w, h)
        out = np.array(src.pixels[:]).reshape(h,w,4)[...,0]
        bpy.data.images.remove(src); return out
    rgba = np.zeros((h,w,4), dtype=np.float32)
    rgba[...,0] = fit(metal_a)            # R = Metallic
    rgba[...,1] = 1.0; rgba[...,2] = 0.0
    rgba[...,3] = 1.0 - fit(rough_a)      # A = Smoothness
    out = bpy.data.images.new(f'T_{name}_M', w, h, alpha=True, float_buffer=True)
    out.colorspace_settings.name = 'Non-Color'
    out.pixels = rgba.flatten()
    out.filepath_raw = f'{base_dir}/T_{name}_M.png'
    out.file_format = 'PNG'; out.save()
    # AO 单独出图（AO 写进 G 通道）
    ao_rgba = np.zeros((h,w,4), dtype=np.float32)
    ao_rgba[...,0] = 1.0; ao_rgba[...,1] = fit(ao_a); ao_rgba[...,2] = 1.0; ao_rgba[...,3] = 1.0
    aoimg = bpy.data.images.new(f'T_{name}_AO', w, h, alpha=True)
    aoimg.colorspace_settings.name = 'Non-Color'
    aoimg.pixels = ao_rgba.flatten()
    aoimg.filepath_raw = f'{base_dir}/T_{name}_AO.png'
    aoimg.file_format = 'PNG'; aoimg.save()
```

HDRP 的 `_Mask` 通道顺序不同，打包要改成：**R=Metallic、G=AO、B=Detail Mask（无则 1.0）、A=1−Roughness**。
```python
# HDRP 版本示意（复用上面的 fit/load，只需改这四行）
rgba[...,0] = fit(metal_a)                 # R = Metallic
rgba[...,1] = fit(ao_a)                    # G = AO
rgba[...,2] = 1.0                          # B = Detail Mask（无细节遮罩填 1）
rgba[...,3] = 1.0 - fit(rough_a)           # A = Smoothness
```

## 5. Unity 模型导入设置（Postprocessor 自动处理，或 MCP 手动）

| 项 | 静态道具 | 角色 |
|---|---|---|
| Scale Factor | 1 | 1 |
| Mesh Compression | 中/高（远景） | 关 |
| Read/Write | 关（需要合并/布料/蒙皮读取才开） | 按需要 |
| Normals | Import | Import |
| Tangents | Calculate Mikk | Calculate Mikk |
| Generate Collisions | 关（改用 Collider 组件） | 关 |
| Lightmap UV | 无第二套 UV 时勾 Generate Lightmap UVs | — |
| Animation Type | None | **Humanoid**（建 Avatar） |
| Import Animation | 否 | 是 |

## 6. 材质接线（MCP `manage_material`，示例）

URP 材质属性（以 `unity_reflect` 实时结果为准，以下为常用）：
`_BaseMap/_BaseColor/_MetallicGlossMap/_Metallic/_Smoothness/_BumpMap/_BumpScale/_OcclusionMap/_OcclusionStrength/_EmissionMap/_EmissionColor`。

- 建材质 `M_名`，shader=Universal Render Pipeline/Lit；依次赋上第 3 节的贴图；金属度/平滑度在无遮罩时给标量（如 0/0.6）。
- 材质实例 `MI_名` 用于场景内变体（颜色/数据微调），不重复建材质。
- 装配线：导入 FBX → 材质 Extract/新建 → 贴图已由 Postprocessor 定好类型 → 拖入槽位 → 截图检查。

## 7. 碰撞与 LOD

- 碰撞：道具 Box/Capsule 优先；不规则件用 Mesh Collider 且勾 Convex；复杂建筑用若干 Box 复合。`UCX_` 前缀简化体在多数 Unity 版本可被识别，但 MCP 直连项目里用组件最稳。
- LOD：LODGroup 三档，渲染器分别放 LOD0/1/2；屏幕占比阈值约 0.6/0.3/0.01；最远档可挂 Billboard。

## 8. 角色 / 动画：Mixamo → Unity（Humanoid）

1. 角色 T-pose 模型上传 Mixamo 自动绑定；下载格式 FBX for Unity（通常 30fps）。
2. 动作：在 Mixamo 单独下载（Include Skin 可关，选 In Place 用于无位移循环如 Idle/Run）；也可以整包在 Blender 用 NLA 整理后一次导出。
3. Blender 导出动画 FBX：
```python
bpy.ops.export_scene.fbx(
    filepath=out, use_selection=True, object_types={'ARMATURE','MESH'},
    add_leaf_bones=False, bake_anim=True,
    bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True,
    axis_forward='-Z', axis_up='Y', global_scale=1.0)
```
4. Unity：角色 FBX Rig = Humanoid → Create Avatar From This Model → 检查骨骼映射（无红叉，下颌/手指按需）；动作 FBX 同样 Humanoid，Avatar 引用角色 Avatar，Clip 分割/循环（Loop Time 给 Idle/Run）。
5. 多动作也可走 Unity 约定：网格文件 `SK_hero.fbx`，动作文件 `SK_hero@Idle.fbx`、`SK_hero@Run.fbx`，导入器自动识别为同名动作。
6. 验收四件事：**不 T-pose（Avatar 映射正确）、不脚滑（位移与循环/根运动匹配）、朝向正确、转身/攻击时手不穿模**。

## 9. Lightmap UV 与静态

- 接受烘焙的静态场景网格：必须有不重叠的第二套 UV；没有就让 Unity 导入器 Generate Lightmap UVs（快但占边界，正式件最好在 Blender 手展）。
- 标记 Static：`manage_components` 或 `manage_graphics` 烘焙时勾选 Contribute GI；LOD 最远档用 Lightmap 或 Simplified LOD 烘焙。

## 10. 推荐目录结构

```
Assets/
├── Imports/                 # 暂存：下载原件、清洗产物、验收场景（验收后清理）
├── Art/
│   ├── Props/{Models,Materials,Textures,Prefabs}
│   ├── Characters/...
│   └── Environment/...
├── Animations/
└── Editor/AssetPostprocessor.cs
```
