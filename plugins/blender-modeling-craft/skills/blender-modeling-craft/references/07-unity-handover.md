# 07 · Unity 交接：面数预算、LOD、碰撞、导出

> 建模侧的"出厂规格"。导出 FBX、Unity 导入设置、材质通道、Prefab 的操作流程在 `unity-blender-mcp` 技能（`references/06-blender-to-unity.md` 与 `scripts/blender_prep_unity.py`）；本篇只定义模型必须满足的规格与交接物。

## 1. 三角面预算（行业默认值，项目 GDD 预算优先）

> 数值为 LOD0（最近）三角面；面向 PC 60fps 写实/半写实，同屏 50–100 个活跃资产的量级。

| 资产类别 | LOD0 tris | 贴图 | 说明 |
|---|---|---|---|
| 第一人称手持物（武器/手电） | 5,000–15,000 | 2048（2560px/m） | 最近距离，倒角/细节最足 |
| 主角 | 30,000–60,000（含装备） | 2048×2–3 | 走 Mixamo/专业绑定，不在本技能自建 |
| 关键 NPC / 敌人 | 10,000–25,000 | 1024–2048 | |
| 近景可交互道具（椅子/桌面物件/终端） | 1,000–4,000 | 1024–2048 | 1–3m 内可观察 |
| 中景道具/家具（柜/货架） | 800–2,500 | 1024 | |
| 箱子/桶等可堆叠件 | 300–1,000 | 512–1024 | 同屏可能大量 |
| 武器（世界摆放/第三人称） | 2,000–6,000 | 1024–2048 | |
| 建筑模块（2m 墙/门/窗） | 500–2,000 | 1024（atlas） | 共享图集 |
| 载具 | 15,000–40,000 | 2048×2 | |
| 树木 | 1,000–3,000（树干） + 树冠 alpha | 1024 | 树冠用面片 |
| 岩石（大/中/小） | 800/400/200 | 1024 共享 | |
| 远景背景/城市件 | 50–300 | 256–512 或无 | |

- 1080p 60fps 经验：同屏总三角面预算 1–3M 是安全区，3–5M 开始依赖 GPU；道具面数应占 20–40%，其余给角色/地形/特效。
- 用 `topology_audit.py --budget-tris N` 卡住预算。

## 2. LOD（近景资产必须做）

| 级别 | 切换距离（经验） | 面数比例 | 处理 |
|---|---|---|---|
| LOD0 | 0–10m | 100% | 完整倒角细节 |
| LOD1 | 10–25m | 40–50% | 合并倒角、去掉小凸起 |
| LOD2 | 25–50m | 15–25% | 合并小部件 |
| LOD3/Culled | >50m | 3–8% 或剔除 | 剪影即可 |

- 做法：复制 LOD0 逐级 Decimate（COLLAPSE）或手减；保持 UV 与 LOD0 一致（共用贴图），命名 `SM_Chair_LOD0/1/2`。
- Unity 里加 LODGroup，阈值常取 0.6 / 0.3 / 0.01。
- 小物件（<300 面、只会在近处出现）不做 LOD；远景资产直接只做 LOD2。

## 3. 碰撞（建模侧要出的）

- **不要直接用渲染网格做碰撞**（倒角/细节会让物理体昂贵）。
- 为每个资产单独做简化碰撞体：
  - 箱/柜/建筑：1–3 个 Box（凸包）即可，命名 `UCX_SM_<Asset>_01`（多体递增 _02）。
  - 桶/瓶：一个简化 Cylinder/凸包。
  - 复杂但需要精确的（可打开的门、载具）：多个 Box 复合或凸包分解。
  - 角色用 Capsule，不用网格碰撞。
- 碰撞体在 Blender 中作为同名前缀的独立网格对象一起导出（FBX 自动识别 `UCX_` 前缀）；或者在 Unity 中用 Box/Capsule Collider 组合。
- 可射击判定（薄墙/门）要避免单面 Mesh Collider，用有厚度的 Box。

## 4. 原点与命名

- 原点：
  - 落地道具：x/y 几何中心，z=0 底面（finalize 的 BOTTOM_CENTER）。
  - 门/可旋转件：铰链轴线上（旋转轴）。
  - 手持武器：扳机/握把参考点（Unity 中再对齐手骨）。
  - 角色：脚底中心（FEET）。
- 命名：
  - 静态网格 `SM_<Category>_<Name>_NN`（`SM_Prop_Barrel_01`）
  - 骨骼/角色 `SK_<Name>`
  - 碰撞 `UCX_SM_<Name>_NN`
  - LOD：对象名后缀 `_LOD0`（Unity 也支持按命名识别）
  - 贴图：`T_<Asset>_BC/_N/_RMA/_E/_AO`；材质实例 `MI_<Asset>`；材质母版 `M_<MaterialType>`
- 所有名称与贴图路径为英文，无中文、无空格（下划线代替）。

## 5. 导出前检查清单（在 Blender 完成）

- [ ] 变换已应用（Rotation/Scale，Location 归零除原点语义外）
- [ ] 法线朝外、统一（recalc outside）
- [ ] 原点在正确位置；资产在 z=0 落地
- [ ] 没有 REF_*/灯光/相机/参考对象混入导出集合
- [ ] 材质槽命名规范；贴图打包到资产目录（BC sRGB、N/RMA Non-Color）
- [ ] LOD 与 UCX 碰撞体就位（需要的话）
- [ ] 所有修改器 Apply（或在导出时勾选 use_mesh_modifiers 且符合预期）
- [ ] topology_audit 对 LOD0 全绿、面数达预算
- [ ] 导出参数：axis forward=-Z、up=Y、global_scale=1、add_leaf_bones=False、use_tspace=True、mesh_smooth_type=FACE

## 6. 交接物清单（交给 unity-blender-mcp / 程序）

1. `SM_<Asset>.fbx`（含 LOD0/1/2、UCX 碰撞；不带动画）
2. `T_<Asset>_BC/_N/_RMA.png`（必要时 _E/_AO）
3. QA 渲染图（4 角度）+ `qa_gate.json`（剪影门禁报告，必须 passed）
4. 材质规格备注：金属度/粗糙度数值、贴图通道、shader（URP Lit）
5. 尺寸/比例说明（真实尺寸与用途距离）

## 7. Unity 导入验收（与 unity-blender-mcp 共同确认）

- [ ] 模型在 Unity 中 1 单位 = 1m，与 1.8m 第一人称相机比例正常（Scale Factor 1）
- [ ] 法线/切线正常（无黑面、无翻法线）
- [ ] 材质不粉、贴图通道正确（N 为 Normal map、RMA 为 Linear）
- [ ] 碰撞生效（可走/可挡/可射击）；可动件绕正确轴旋转
- [ ] LOD 切换正常；Prefab 生成并放入 `Assets/Art/<类别>/Prefabs/`
- [ ] 控制台无报错；Profiler 中该资产 Draw Call/面数符合预期
