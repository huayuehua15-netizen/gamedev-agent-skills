# 从零建模（最后手段）与 AI 生成件处理

> 目录：1. 什么时候才自己建 → 2. 游戏资产建模管线 → 3. 常用 bpy 建模片段 → 4. UV 与 texel density → 5. 烘焙与 PBR → 6. 角色 → 7. AI 生成件返工

## 1. 什么时候才自己建

满足以下任一条件才动手，否则继续素材优先：
- 所有素材库都找不到（风格/结构独特，如定制招牌、剧情关键道具）
- 资产有精确功能结构（自定义机关、可交互机械、需要精确碰撞/动画绑定）
- 品牌/版权形象必须原创
- 搜索 + 改造素材的时间已超过自建时间

动手前先评估：**AI 生成（Rodin/Hunyuan/Tripo/Meshy）能不能作为起点**。能则用 AI 起型再返工，省掉白盒阶段。

## 2. 游戏资产建模管线（与 3A 做法一致，做简化版）

```
参考图/尺寸(米) → 低模白盒(blockout) → 高模细节 → 重拓扑低模 → UV
→ 烘焙(法线/AO/位置) → PBR 贴图 → 面数/比例自检 → 导出(走06)
```

1. **设单位**：Properties > Scene Properties > Unit System = Metric，Unit Scale = 1.0。永远在真实尺寸下建模（门 2.0m、椅高 0.45m、桌高 0.75m）。
2. **白盒**：用立方体/圆柱快速搭比例和体积，不做细节，进 Unity 先验玩法和遮挡。
3. **高模**：细分、倒角、雕刻（Sculpt）做细节；靠法线贴图把细节转移到低模，而不是真用高模进引擎。
4. **重拓扑**：产出四边面为主的低模，循环边服务于变形（角色关节）和 UV 接缝。
5. **硬表面准则**：
   - 所有 90° 边加 Bevel（哪怕 1-2mm，否则法线高光过曝），Bevel 后用 Weighted Normal。
   - 镜像建模用 Mirror 修改器；重复结构用 Array；开孔用 Boolean 后必须清理环形拓扑。
   - 平滑着色 + 锐边/自动平滑，别整面 flat 也别全 smooth（圆柱端面会糊）。
6. **面数自检**：见 04 预算表；远看不见的面（贴墙底面、内部）删掉。

## 3. 常用 bpy 建模片段（MCP 执行）

```python
import bpy, bmesh
from math import radians

def new_mesh(name, loc=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; return o

# 加倒角（避免硬边高光问题）
def bevel(obj, width=0.005, segments=2):
    m = obj.modifiers.new('Bevel', 'BEVEL')
    m.width, m.segments = width, segments
    m.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)

# 加权法线（低模硬表面平滑正确）
def weighted_normals(obj):
    m = obj.modifiers.new('WN', 'WEIGHTED_NORMAL'); m.keep_sharp = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)

# 布尔开孔（之后清理：选环面 Dissolve 多余点，重算法线）
def boolean_diff(target, tool):
    m = target.modifiers.new('Bool', 'BOOLEAN')
    m.operation = 'DIFFERENCE'; m.object = tool; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)

# 重新拓扑减面（AI/扫描件）：Decimate 保形或 Quad Remesh
def decimate(obj, ratio=0.2):
    m = obj.modifiers.new('Dec', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'; m.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)
```

重拓扑质量要求高的角色/主角，不能只靠 Decimate：用 Remesh（Voxel）出基底再手修，或提示用户使用 Quad Remesher/手动拓扑；AI 自己拿 bmesh 手做精拓扑不现实，交给专业流程或外包。

## 4. UV 与 texel density

- 每个静态网格至少一套 UV（UV0），需要光照烘焙的再加第二套（UV1，Lightmap，无重叠、留边距）。
- 低模 UV 用 Smart UV Project 起步，再手动拉直、缝合（接缝藏在视线外、腋下、底面）。
- texel density 目标（与 GDD 一致）：约 **1024 px/m**，近景关键道具 2048 px/m，远景 512 px/m。同一场景资产保持同一密度。
- 贴图尺寸：道具 256-1024、大件 1024-2048，不要什么都 4K。

```python
import bpy
# 自动展 UV（白盒/占位用，正式资产仍需手修）
def smart_uv(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
```

## 5. 烘焙与 PBR

- 从高模→低模烘焙：Normal（法线）、AO；颜色/金属/粗糙度在 Substance 或材质节点里做。
- 无 Substance 时 Blender 烘焙：Cycles 引擎，Selected to Active，给低模 Cage/Ray Distance，图像设置 16-bit。
- 最终贴图通道（导出前命名规范）：
  - `T_名_BC`：BaseColor，sRGB，PNG
  - `T_名_N`：Normal，Linear（Blender 用 OpenGL 法线，绿通道向上，与 Unity 一致）
  - URP：`T_名_M`（**R=Metallic，A=Smoothness=1−Roughness**），Linear；AO 单独 `T_名_AO`（G 通道）
  - HDRP：`T_名_Mask`（**R=AO，G=Smoothness=1−Roughness，B=Metallic，A=1**），Linear
  - 外部素材若给的是 glTF/ORM 贴图（R=AO、G=Roughness、B=Metallic），用 06 第 4 节脚本重排，不要直接挂
- 金属度一般是 0/1 两极；粗糙度变化承载大部分旧化效果。

## 6. 角色

- 自己不写复杂绑定：人形一律 **Mixamo 自动绑定**（65 骨/25 骨，见 03）或 Blender Rigify 后转 Humanoid。
- 建模摆 T-pose（手掌朝下、掌心朝后，符合 Mixamo 习惯）；关节处留足循环边；手指、膝盖、肩是变形重灾区。
- 表情/换装/第一人称手等特殊需求在 GDD 单页里写清，再决定骨架层级。
- 角色导出与 Unity Avatar 配置见 06。

## 7. AI 生成件的标准返工流程

Rodin/Hunyuan/Tripo/Meshy 出的件必须返工，禁止直接进引擎：

1. 审计：面数、UV、贴图分辨率（用 audit 脚本）。
2. 重拓扑：Decimate/Voxel Remesh 到预算内；主角级表面手动修。
3. 重新展 UV（AI 给的 UV 通常不可用于光照烘焙）。
4. 贴图处理：重命名通道、转色彩空间；糊的地方手绘或程序化重做。
5. 走标准清洗、导出、Unity 验收（同 04 的 6-8 步）。
6. 若返工后仍达不到近景标准，降级为远景/背景件，或放弃自建重搜。
