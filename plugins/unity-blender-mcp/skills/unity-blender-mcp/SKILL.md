---
name: unity-blender-mcp
description: "通过 MCP 自主操作 Unity 与 Blender，完成 3D 游戏资产的搜索复用、建模、清洗、导出、导入与验收全流程。核心原则是素材优先：优先从 MCP 内置素材源（Sketchfab、Poly Haven）与外部素材库（3d66 等国内站、TurboSquid、CGTrader、Kenney、Quaternius、Mixamo、AI 生成等）搜索复用现成资产，搜不到再在 Blender 自建。涵盖 MCP 工具发现与连接、bpy 自动化建模与批处理、素材审计清洗、Unity 正确 FBX 导出、Unity 导入设置（材质/LOD/碰撞/骨骼动画/Prefab）、批量导入后处理与故障排查。当用户要求用 MCP 操作 Blender 或 Unity、找 3D 模型/素材/动画、把下载素材导入 Unity、处理素材格式与授权、Blender 建模或改模、导出 FBX、搭建 Blender→Unity 管线、修复粉色材质/缩放/法线/轴/碰撞/动画异常时使用。 English: Asset-first 3D pipeline driving Unity and Blender through MCP: search and reuse existing assets, audit and clean them, export FBX, and import into Unity with correct materials, LODs, colliders, skinned animation and prefabs. Use when sourcing 3D assets, building a Blender-to-Unity pipeline, or fixing pink materials, scale, normals, axes, colliders or animation issues."
---

# Unity + Blender MCP 自主制作管线

> **路径约定**：本文件中所有 `scripts/`、`references/`、`assets/` 都**相对于本 SKILL.md 所在目录**。
> 换到别的宿主或别的工作目录时，先把 SKILL.md 目录解析成绝对路径再调用。
> **命令行跑脚本务必带 `--python-exit-code 1`**：Blender 默认异常退出码为 0，漏掉这个参数时审计失败也会显示成成功。

## 概述

本技能让 AI 通过 MCP（Model Context Protocol）自主操作 Blender 与 Unity，以**素材优先（Asset-First）**方式生产 3D 游戏资产：先搜复用，再 AI 生成，最后才从零建模，并把每个资产做成"导入引擎即可用"的成品。

## 核心原则：素材优先决策树

收到任何"要一个 XX 模型/资产"的需求，严格按以下顺序决策，禁止一上来就手搓：

1. **MCP 内置素材源**（最快，零下载搬运）：Blender MCP 的 `search_sketchfab_models` / `search_polyhaven_assets`（HDRI、PBR 贴图、写实模型）；Unity MCP 的 `import_model`（Sketchfab）。
2. **CC0 游戏素材站**：Kenney、Quaternius、KayKit、Poly Haven、Poly Pizza——风格统一、可直接进引擎、商用零风险。
3. **大型市场免费区**：Sketchfab（筛 CC0/CC-BY 且 Downloadable）、TurboSquid、CGTrader、Fab（Megascans）、BlenderKit。
4. **国内站**：3d66、模之屋、爱给网等——**必须逐件核授权与格式**（大量 `.max` 文件 Blender 打不开，见 03）。
5. **角色/动画**：骨骼与动画优先 Mixamo（免费自动绑定 + 数千动作）、Quaternius 带动画角色包。
6. **AI 生成**：Blender MCP 的 Hyper3D Rodin / Hunyuan3D、Unity MCP 的 Tripo/Meshy——只做**单个明确物体**，不做整场景/地形。
7. **Blender 自建**（最后手段）：前面都找不到，或需要精确功能结构/定制品牌资产时，才用 bpy/建模工作流自建。

**任何来源的素材，进 Unity 前都必须过一遍 Blender 审计与清洗（第 5 步）。** 禁止把下载的原始 FBX 直接拖进 Unity。

## 开工前：MCP 连接与工具发现（每次会话必做）

MCP 工具名因实现而异（Blender 侧常见 ahujasid/blender-mcp；Unity 侧常见 CoplayDev/unity-mcp 或 Unity 官方 `com.unity.ai.assistant`），**不要假设工具名固定**。

1. 先查看当前会话实际暴露了哪些 MCP 工具，把它们与 `references/00-mcp-connection.md` 的"标准能力对照表"做映射。
2. 检查连接状态：
   - Blender：调用场景检查类工具（如 `get_scene_info`）确认 Blender 已开、插件已 Connect；
   - Unity：调用编辑器状态/控制台类工具（如 `manage_editor` / `read_console`）确认桥接 Running。
3. 工具缺失或未连接：按 00 的排查表处理，或退化为命令行批处理（`blender --background --python`、Unity batchmode），不要装作调用成功。
4. 首次接入时确认项目的**渲染管线**（Built-in / URP / HDRP）与 Unity 版本——材质 shader、遮罩通道打包方式都不同。

## 标准工作循环（每个操作都遵守）

```
检查现状（scene_info / 控制台）→ 截图/读数留证 → 小步执行单个变更
→ 截图或读数验证 → 存盘/记录 → 再进行下一步
```

- **先读后写**：改任何东西前先获取场景/对象信息；Blender 改前先 `bpy.ops.wm.save_as_mainfile` 备份。
- **小块执行**：Blender MCP `execute_blender_code` 有超时（约 180s），复杂任务拆成多个代码块；每块自包含（自己 `import bpy`、按名字重新选择对象，不依赖上一块的内存变量）。
- **结果必须可见**：Blender 每次导入/摆放/导出后用 `get_viewport_screenshot` 验证；Unity 每步用 `read_console` 查报错、用层级/场景查询确认结果。
- **失败不硬闯**：同类操作失败两次，换方法或换通道，记录现象，不要反复重试同一调用。

## 三条工作流

### 流程 A：拿一个现成资产（最常用）

读 `references/04-asset-reuse-workflow.md`，走 9 步：
**需求单 → 搜素材 → 候选评估（含授权）→ 下载暂存 → Blender 审计 → 清洗标准化 → 导出 FBX → 质检渲染目检 → Unity 导入验收。**

- 审计：`scripts/blender_asset_audit.py`（输出面数/材质/UV/变换/骨骼/动画的 JSON 报告，对照预算决定去留）。
- 清洗 + 导出：`scripts/blender_prep_unity.py`（应用变换、原点归位、法线重算、统一命名、按 Unity 正确参数导出 FBX）。
- 质检渲染：`scripts/blender_asset_qa_render.py`（导出后自动出一张标准灯光/取景的品质图，目检贴图、金属粗糙度、法线、造型；`--turntable N` 可出多视角，审计过的数据 + 眼睛确认都通过才算合格）。
- 授权：非 CC0 资产逐项登记到 `assets/asset-ledger.csv`（授权类型、来源 URL、署名要求）。

### 流程 B：从零做一个资产

读 `references/05-model-from-scratch.md`：参考图/尺寸 → 低模搭型 → 高模细节 → UV → 烘焙法线/PBR → 面数与 texel 预算自检 → 走 A 的导出/导入步骤。先判断 AI 生成能否替代，AI 生成件同样要审计、重拓扑。

### 流程 C：Blender → Unity 引擎内设置

读 `references/06-blender-to-unity.md`：模型/材质/动画导入设置 → LOD → 碰撞 → 材质贴图通道映射（URP/HDRP 不同）→ 生成 Prefab → 场景摆放/灯光烘焙 → 构建。
- 批量导入时把 `assets/unity/Editor/AssetPostprocessor.cs` 放进 Unity 项目的 `Assets/Editor/`（带目录门控，只处理指定导入目录，不会污染全项目）。

## 脚本与资产

| 文件 | 用途 | 运行方式 |
|---|---|---|
| `scripts/blender_asset_audit.py` | 审计当前场景或指定模型文件，输出 JSON 体检报告 | MCP：粘贴代码执行；或 `blender --background --python scripts/blender_asset_audit.py -- 模型路径` |
| `scripts/blender_prep_unity.py` | 清洗选中资产并导出 Unity 标准 FBX（含可选动画烘焙） | MCP：粘贴代码后调用 `prep_and_export()`；或命令行 `-- 输出路径` |
| `scripts/blender_asset_qa_render.py` | 资产质检渲染：自动取景、HDRI/三点布光、AgX、中性背景出品质图，支持 `--turntable N` 多视角 | `blender --background --python ... -- 模型路径 输出.png [--hdri 路径] [--turntable 3]`；MCP 粘贴渲染当前场景 |
| `assets/unity/Editor/AssetPostprocessor.cs` | Unity 端导入后处理：贴图按后缀设 sRGB/法线/遮罩，模型统一缩放/法线/网格设置 | 复制到 Unity 项目 `Assets/Editor/` |
| `assets/asset-ledger.csv` | 资产授权台账模板 | 每个非 CC0 资产登记一行 |

## 参考文档索引（按需加载）

- `references/00-mcp-connection.md`：MCP 连接/工具发现/安全铁律/无 MCP 时的命令行退化
- `references/01-blender-mcp-playbook.md`：Blender MCP 工具表 + bpy 常用代码片段库（导入/清洗/材质/LOD/导出/截图）
- `references/02-unity-mcp-playbook.md`：Unity MCP 工具表 + 场景/对象/资产/材质/脚本/构建操作
- `references/03-asset-libraries.md`：素材库大全（授权/格式/选型/搜索关键词/3d66 等国内站的坑）
- `references/04-asset-reuse-workflow.md`：素材复用 9 步流程与验收清单
- `references/05-model-from-scratch.md`：何时自建、Blender 游戏资产生成管线、AI 生成件处理
- `references/06-blender-to-unity.md`：Blender→Unity 标准管线（轴/比例/FBX 参数/材质通道/LOD/碰撞/Humanoid）
- `references/07-troubleshooting.md`：症状→原因→修复对照表（粉材质/缩放/法线/躺倒/无碰撞/T-pose/脚滑等）

## 安全铁律

- 改用户现有 Blender 场景/Unity 场景前先另存备份；导入、清洗一律在**独立 Blender 场景**和 Unity 的 `Assets/Imports/` 暂存目录内完成，验收通过再移入正式目录。
- 不删除、不覆盖用户源文件；下载原件保留在暂存区，清洗产物另存。
- `execute_blender_code` 与 Unity 的 `execute_code` 可执行任意代码，禁止做与当前任务无关的操作；危险操作（删除、批量改名、覆盖导出）先列出受影响对象再执行。
- 授权不明（尤其 NC、仅限学习、3d66 免费件、付费会员件）一律不进商业项目；宁可换 CC0 源或自建。
- 所有材质/贴图/模型命名走规范（`SM_`/`SK_`/`T_BC/N/RMA/M`/`M_`/`MI_`），中文文件名和中文贴图路径在导出前全部转英文。

## 完成定义（资产级 DoD）

每个交付到 Unity 的资产必须满足：

- [ ] 授权已登记（CC0 也要记来源），可商用无阻断
- [ ] 审计报告：面数符合预算、有 UV、无 N-gon 问题、变换已应用
- [ ] 场景内缩放正确（人物约 1.7m、与周围物体比例真实），方向正确
- [ ] 材质不粉、贴图不丢（贴图随包/在项目内），URP/HDRP 通道正确
- [ ] 有合适碰撞体，角色/带动画件已配 Avatar 且动作正常
- [ ] 已生成 Prefab，LOD 按要求配置，控制台无报错
- [ ] 关键视角品质图已由 `blender_asset_qa_render.py` 出图并目检通过（贴图/法线/金属粗糙度/造型），再交付用户确认
