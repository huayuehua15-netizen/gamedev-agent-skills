# 03 · 有机建模与雕塑（角色 / 怪物 / 岩石 / 植被）

> 有机对象：曲面主导、没有硬边转角的物体。AI 用 bpy 代码做有机形体很容易翻车，本类默认优先级是：素材库 → AI 生成 → 雕塑/重拓扑。**人形角色与骨骼动画默认走 Mixamo，不要从零自建。**

## 1. 分工边界

| 对象 | 默认路径 | 自建条件 |
|---|---|---|
| 人形角色（含绑定/动画） | Mixamo 模型 + 动画；Quaternius/KayKit 角色包 | 只有当美术风格极度特殊（如纯几何抽象）时 |
| 动物/怪物 | 素材库 → AI 生成（单物） | 游戏核心 IP、素材库完全没有 |
| 岩石/碎石/土坡 | Poly Haven 扫描模型（写实首选）；Kenney 风格岩石 | 风格化或需要特定叙事形状 |
| 树干/植被 | 素材库 + SpeedTree 思路；Quaternius/Kenney 植被 | 特定标志性植物 |
| 布料/旗帜 | 布料模拟（Cloth）或置换 | — |
| 地形 | Unity Terrain / 高度图 | 不用 Blender 手搓地形 |

## 2. 雕塑工作流（Sculpt Mode）

有机建模的唯一正解是"高模雕塑 → 低模重拓扑 → 烘焙法线"，不要试图用盒子拼出生物。

1. **体块**：用基础体（UV 球/圆柱）或人体骨架基础形，标出大比例。
2. **Voxel/Dyntopo 统一网格**：`Remesh → Voxel`（0.005–0.02m 体素，物体越小越细），把拼合的体块熔成一个连续网格。
3. **大形雕塑**：Grab（抓动）、Clay Strips（堆泥）、Crease（压褶）、Smooth（平滑）；只做大肌肉体块和剪影，不做五官/皱纹。
4. **中形**：骨骼凸起、肌肉分界、关节结构。
5. **小形**：疤痕、褶皱、毛孔（用 Stencil 贴图），一般留到贴图阶段。
6. 每阶段出 QA 渲染（雕塑也适用剪影测试）。

```python
# 雕塑体素化（Object 模式）
def voxel_remesh(obj, voxel_size=0.01):
    obj.data.remesh_voxel_size = voxel_size
    obj.data.remesh_voxel_adaptivity = 0.0
    obj.data.use_remesh_fix_poles = True
    obj.data.use_remesh_smooth_normals = True
    sel([obj]); bpy.ops.object.voxel_remesh()
```

## 3. 重拓扑（Retopology）——雕塑必须做

高模（几万~几百万面）不能进引擎，必须在表面铺一层干净的四边面低模。

- **手工**：新建平面 → 吸附（Snap to Face）贴在高模表面 → 用 F2/刀工具铺四边面 → 挤出延伸。
- **半自动**：
  - Quad Remesh（商业化，最快最稳）。
  - Voxel Remesh → Decimate Planar（岩石等不规则物体够用，生物慎用）。
  - Shrinkwrap 修改器把粗略网格吸到高模上。
- 生物面数：四肢走 3–5 圈环（变形要求 6–8 圈关节），躯干沿肌肉走向布环。
- 关节处环切线必须与旋转轴垂直（肩、肘、髋、膝、颈、指），否则动画会穿模。

## 4. 岩石与自然物的"便宜但好看"做法

- **岩石**：一个 UV 球 → 随机缩放压扁 → 加 Subdivision 2 级 → Displace 修改器（Clouds/岩石灰度贴图，强度 0.1–0.3）→ 雕刻几块大平面结构 → Decimate 到预算 → 复制旋转做变体（同一块石头至少出 3 个不同剪影的变体）。
- **土坡/碎石堆**：同一组岩石模块 3–5 个反复摆，大小随机，大中小三级搭配（1 大 + 2 中 + 5 小）。
- **树干**：圆柱沿高度做轻微随机弯曲（缩放出倾斜 + 环切），根脚处加粗张开；树皮用 Noise/树皮贴图 + 置换，不手雕。
- **树**：树冠用 3 个交错的 alpha 面片（Billboard）或简单的 2–4 球 clump 体 + 树叶贴图；树干 + 树枝一根主干、2–4 主枝，不要对称镜像（自然物不对称）。
- **草**：引擎里用 GPU Instancing/Terrain detail，不做单片草模型。

## 5. 自然物的尺度（避免"假"）

- 岩石必须有"落地感"：底部埋进地面 10–20%，不要悬浮。
- 自然物忌讳 90° 对称、等距、等大；复制后必须改变比例、旋转、朝向。
- 树木胸径 200–400mm（树干直径），树冠 4–8m，高 6–10m（城市景观树）；乔木主干在 1.5–2.5m 才分叉。

## 6. 烘焙（高模细节搬到低模，见 04）

- 高模 → 低模 Normal（+ AO、Curvature）；低模 UV 必须先展开，贴图分辨率按 04 的 texel 密度。
- 烘焙前对齐高模低模位置（用 cage 或 ray distance 控制），选中低模、目标高模。
- 法线接缝处用 Bake Cage 包裹，避免边缘漏光。

## 7. 角色资产交接（Mixamo 路线）

1. 找到合适的 Mixamo 角色或上传 T-pose 模型，Auto Rigger 绑定。
2. 下载带皮角色（FBX，T-pose）与需要的动画（FBX，in-place）。
3. 进 Blender 审计、统一命名（`SK_`）、补道具挂点；导出 FBX。
4. Unity 中 Animation Type=Humanoid，建 Avatar；动画复用同一 Avatar。
5. 自建的武器/道具挂到手骨（hand_R 下）或通过 IK 约束瞄准。
