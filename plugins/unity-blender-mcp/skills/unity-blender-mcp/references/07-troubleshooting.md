# 故障排查对照表（症状 → 原因 → 修复）

> 按软件分节；每步修复后用截图/控制台复验，再继续。

## 一、缩放与位置

| 症状 | 原因 | 修复 |
|---|---|---|
| 模型巨大/极小（常见 100 倍、1000 倍） | 单位不一致；缩放未应用；Sketchfab 件未归一化 | Blender 里按真实尺寸缩放（参照物 1.7-1.8m 人）→ 应用 Scale → 重新导出；Unity Scale Factor 保持 1，不用它兜底 |
| 模型躺在地上/朝背面 | 轴向问题，导出轴错 | 导出 FBX 固定 `axis_forward='-Z', axis_up='Y'`；已应用 Rotation；验证朝向正面朝 -Z |
| 模型飘在半空/陷地 | 原点没在脚底/几何中心 | 道具原点到几何中心；角色原点到脚底（cursor 到最低点再 Set Origin to 3D Cursor） |
| 资产间相对比例乱 | 各素材独立缩放未统一 | 全部以米为单位在 Blender 归一后再进 Unity |
| 导入后位置/旋转带奇怪数值 | 变换未应用 | 应用 Rotation & Scale；Location 归零 |

## 二、网格与法线

| 症状 | 原因 | 修复 |
|---|---|---|
| 部分面发黑/看不见 | 法线反了 | Edit Mode 全选 → Recalculate Outside（make_consistent） |
| 高光不对/边看起来糊 | 平滑着色与锐边没处理 | 硬边加 Bevel + Weighted Normal；设置 Auto Smooth 角度 |
| 表面有碎面/破洞 | 重复点、松散点、N-gon 三角化乱 | Remove Doubles → Delete Loose → 检查 N-gon |
| 阴影有锯齿/明暗断层 | 法线平滑组/切线缺失 | 导出 `mesh_smooth_type='FACE'`、`use_tspace=True`；Unity Tangents = Calculate Mikk |
| 面数暴涨/卡顿 | 扫描件/高模未减面 | 跑审计看面数 → Decimate/重拓扑 → 出 LOD |
| 布尔开孔后边缘崩 | Boolean 拓扑没清 | EXACT 求解器 → 清环 → 重算法线；复杂开口改用手动拓扑 |

## 三、材质与贴图

| 症状 | 原因 | 修复 |
|---|---|---|
| 材质全粉（magenta） | shader 与管线不匹配（如 HDRP 材质进 URP）或贴图缺失 | 重建材质为 URP/Lit（或 HDRP/Lit）；重连贴图；`read_console` 看缺图路径 |
| 贴图丢失（灰色） | 贴图路径丢失/中文路径/未随包 | 导出前路径全英文；贴图与 FBX 同目录或已在 Assets 内；检查 Blender 贴图为相对路径 |
| 颜色贴图发灰/过曝 | 色彩空间错 | 颜色图 sRGB；法线/遮罩/金属/粗糙/AO 设 Non-Color |
| 金属/粗糙度表现怪异 | 通道接错 | URP 用 R=Metal、A=Smoothness；HDRP Mask 用 R=AO、G=Smoothness、B=Metal；ORM 按 06 节重排 |
| 金属看起来像塑料 | 金属度/粗糙度数值不对 | 金属件 Metal≈1 且粗糙度按表面（镜面 0.05-0.15、拉丝 0.3-0.6） |
| 法线凹凸反了/边缘炸 | 法线格式 DirectX/OpenGL 混用 | Blender 用 OpenGL（绿向上）；DirectX 图翻转绿通道 |
| 3ds Max 材质（V-Ray/Corona）导入后没了 | FBX 不带节点材质 | 拿到 BSDF/标准材质重连 PBR；或找带贴图的版本手动接 |
| 自发光不亮 | 未开 Emission 开关 | 材质勾 Emission，赋 `_EmissionMap` 和颜色，URP 注意后处理 Bloom |
| 贴图精度看起来糊 | texel density 不一致/分辨率不够 | 按 1024 px/m 近景 2048；同场景统一密度 |

## 四、碰撞

| 症状 | 原因 | 修复 |
|---|---|---|
| 角色穿过道具 | 无 Collider | 加 Box/Capsule/Mesh Collider；复杂建筑用复合 Box |
| 角色被不可见边缘卡住 | 网格碰撞/凸包形状过细 | 用简化碰撞体；Mesh Collider 勾 Convex 用于刚体，静态场景可不勾 |
| 角色胶囊被台阶挡住 | 碰撞台阶过高 | 台阶碰撞做斜面或改用 CharacterController 台阶高度；Max Step Offset 调到 0.3-0.4 |
| 子弹/射线打不中 | 无碰撞或射线层级问题 | 检查 Collider 与 Layer；`manage_physics` 看碰撞矩阵 |

## 五、角色与动画

| 症状 | 原因 | 修复 |
|---|---|---|
| 播放动画变 T-pose | 非 Humanoid/Avatar 未创建/映射缺失 | Rig=Humanoid → Create Avatar → 检查骨骼映射无红 |
| 动画整体错乱/扭曲 | 骨骼名/层级不匹配 | 同一套 Mixamo 骨架；动作 FBX 引用角色 Avatar；统一 65 骨 |
| 角色原地滑行（脚滑） | 位移与速度不匹配/根运动错 | 循环动作选 In Place；或正确烘焙 Root Motion，动画位移与移动速度对齐 |
| 动画时长/速度不对 | 帧率不一致 | Mixamo 与工程统一 30fps；Clip 检查采样；用帧数与秒数双写核对 |
| 末端多奇怪骨点 | 导出带了叶子骨 | 导出 `add_leaf_bones=False` |
| 转身/攻击手穿模 | 循环边/动作本身问题 | 模型关节加循环边；换动作或调 Avatar Mask |
| 角色进场景比例怪 | 骨架与网格缩放链 | 应用全部变换、骨架在原点、重导 |

## 六、Blender MCP / 操作

| 症状 | 原因 | 修复 |
|---|---|---|
| `Timeout waiting for Blender response` | 代码块执行超过约 180s | 拆小步骤；先存盘；大批量改循环外保存 |
| 连接丢失/首条命令失败 | 插件未 Connect/重启后偶发 | 检查 N 面板 Connect；首条失败重试一次 |
| `bpy.ops` 报 context incorrect | 操作上下文不对 | 设 active/selected；`temp_override` 切到 VIEW_3D；优先用数据 API |
| 代码块里变量不见了 | 每块执行环境独立 | 每块自包含 import、按名字重新选对象 |
| 直接赋值 `obj.scale=` 后 `transform_apply`，对象跑到原点/尺寸减半 | headless 下依赖图未刷新 + 算子参数简写 | 先 `bpy.context.view_layer.update()`；再用完整关键字 `bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)`，不要写 `transform_apply(scale=True)` |
| `primitive_cube_add(size=1)` 缩放后尺寸只有预期一半 | size=1 的基础立方边长就是 1m，不是 2m | 直接 `obj.scale=(长,宽,高)`，不要再除以 2 |
| 中文 Blender 下 `nodes["Background"]` 报 KeyError | 节点名被本地化 | 一律按类型找：`next(n for n in nodes if n.type=="BACKGROUND")`；节点输入槽名（如 `"Base Color"`）API 里仍为英文 |
| 渲染引擎枚举找不到 `BLENDER_EEVEE_NEXT` | 5.2 起 EEVEE 枚举重命名 | 5.2 用 `scene.render.engine="BLENDER_EEVEE"`；4.2-4.5 才是 `BLENDER_EEVEE_NEXT` |
| 多对象合并（join）后倒角消失或重复 | 非活动对象修改器在 join 时烘焙、活动对象保留 | join 前先对每个零件 `modifier_apply` 全部修改器，再合并 |
| 质检渲染图顶部/侧面被裁切 | 取景只按宽高算，忽略俯仰时纵深投影 | 用角点法：8 个包围盒角点投影到相机空间，按水平/垂直最大半宽取景（脚本已实现） |
| 质检渲染背景露出黑棚角落 | HDRI 全景图边缘不是中性色 | 用 LightPath 的 Is Camera Ray 混合：照明射线走 HDRI、相机射线走 0.55 中性灰，地面同色 |
| 渲染图灰蒙蒙/明暗反差弱 | 默认视图变换 Standard 线性发灰 | 4.2+ 用 `view_transform="AgX"`、`look="AgX - Medium High Contrast"`；旧版无 AgX 才退回 Standard |
| PolyHaven 工具不可用 | 插件面板没勾选 | N 面板 BlenderMCP 启用 PolyHaven |
| Rodin 提示额度不足 | 免费每日额度 | 等次日或换 Hunyuan/其它源，或自建 |
| `.max` 打不开 | Blender 无该导入器 | 找 FBX/OBJ 版；3ds Max 转；或直接换源 |

## 七、Unity MCP / 导入

| 症状 | 原因 | 修复 |
|---|---|---|
| 刷新后没导入/材质没更新 | AssetDatabase 未刷新 | `refresh_unity`；必要时 Reimport |
| 控制台一堆编译错误 | 编辑器脚本/包不兼容 | `read_console` 定位；先修编译错误，否则 MCP 操作可能全失效 |
| Postprocessor 没生效 | 不在 Editor 程序集/没编译/不在门控目录 | 确认文件在 `Assets/Editor/`（含 asmdef Editor 平台）；资产在 `Assets/Imports/`；`refresh_unity` |
| 后处理误伤其它资产 | 目录门控不对 | 改文件顶部的门控常量；只保留专属导入目录 |
| glTF 导不进 Unity | Unity 原生不支持 | 装 glTFast，或在 Blender 转 FBX（首选） |
| 灯光烘焙失败 | 没 Lightmap UV | 导入器 Generate Lightmap UVs 或 Blender 展 UV1；勾 Contribute GI |
| 构建失败/包冲突 | 平台场景没加/包版本 | `manage_build` 检查 Scenes In Build、目标平台；`read_console` 查包错误 |
| 截图/视野无法确认 | 部分 Unity MCP 无截图 | 用 `find_gameobjects`/`manage_scene` 查层级与 Transform；让用户在编辑器确认或用 `execute_code` 截 Game View 到文件 |

## 八、排查总原则

1. 每次只改一个变量，改完即验，禁止"多改一把梭"。
2. 保留问题文件副本（暂存区），对比修复前后截图。
3. 同一问题在两个软件都可能出错时，先在 Blender 确认（尺寸/法线/贴图），再查 Unity 设置；**不要用 Unity 端补偿 Blender 端的错误**。
4. 30 分钟内修不好一个素材，回 03 重新选源——素材优先的意义就是不被烂资产绑架。
