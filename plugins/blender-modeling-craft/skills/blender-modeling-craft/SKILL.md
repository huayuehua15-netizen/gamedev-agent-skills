---
name: blender-modeling-craft
description: "解决大模型从零做 3D 模型质量差的问题：Blender 建模手艺 + 多角度渲染自检 + Unity 游戏化交付。涵盖参考图驱动建模、真实尺寸比例（含 1.7m 人体标尺）、blockout 体量、硬表面（盒建模/卡线/倒角/布尔/细分曲面）、有机雕塑与重拓扑、游戏级拓扑（四边面/边流/极）、UV 与 texel density、PBR 材质与法线烘焙、面数预算与 LOD、剪影 IoU 门禁（正交渲染与参考图比对比例，不过不许导出）+ 多机位质检渲染人审、FBX 导出 Unity 交接。当用户要求在 Blender 里从零建模/改模、做道具/武器/建筑/载具/家具/自然物、模型看着像方块堆砌或比例不对、需要卡线倒角拓扑 UV、要渲染检查模型效果、或为 Unity 做游戏就绪资产时使用。素材复用/导入管线交给 unity-blender-mcp；本技能只负责『自己动手做时怎么做得不烂』。"
---

# Blender 建模手艺：从"方块堆砌"到游戏就绪资产

## 定位与边界

- **本技能管"做模型的手艺"**：AI 在 Blender 里从零建模或改模时，怎么保证比例、体量、细节、拓扑、材质达到写实 3A 游戏可用水准。
- **素材优先不动摇**：要一个资产时，先走 `unity-blender-mcp` 的素材优先决策树（MCP 内置库 → CC0 站 → 大市场 → 国内站 → Mixamo → AI 生成 → 最后自建）。**只有搜不到、需要精确定制结构、或必须修素材时，才进入本技能。** 自建决策见 `references/00-modeling-principles.md`。
- **导出与引擎内设置**：清洗、FBX 导出、Unity 材质/碰撞/LOD/Prefab 的操作细节在 `unity-blender-mcp`；本技能的 `references/07-unity-handover.md` 只负责建模侧必须满足的规格与交接物。

## 七条铁律（违反任何一条，成品都是"AI 烂模"）

1. **无参考不开工**。至少有正面、侧面两张参考图（概念图、实物照片、蓝图、同类型游戏截图均可）；做之前先把参考图导入场景，不要凭记忆"脑补"形状。
2. **真实尺寸**。1 单位 = 1 米，开工先 `ensure_units_metric()`，建一个 1.7m 人体标尺（`build_human_scale_rig`）放旁边；一切尺寸对照 `assets/real-world-dimensions.csv`。比例错了，细节再多也是废的。
3. **先 blockout 后细化**。先用盒子/圆柱把大比例和体量做对（30 分钟可推倒重来的程度），截图确认比例，再动手做细节。禁止一上来就挤出、雕刻。
4. **所有硬边都要倒角**。现实世界没有数学上锐利的边，锐利边不反光 → 廉价感。硬表面模型每个棱角都要有倒角（宽度对照物体尺度，常见 0.5–3mm），倒角段数 2–4。
5. **非破坏式工作流**。镜像/倒角/细分/实体化都用修改器，最后再 apply；先复制出备份命名 `_subd`。禁止在大平面上用布尔然后不管。
6. **先机器门禁，再人眼验收**。比例与剪影用 `scripts/qa_render.py --gate` 跟参考图算 IoU 和宽高比（blockout ≥0.70 / 成品 ≥0.85），不过就禁止进入下一步；门禁过了再按 06 的 rubric 挑细节。**禁止把"模型自己看一眼觉得还行"当成验收**——多数运行环境里它看不到渲染图。
7. **游戏化交付**。交付前过拓扑审计（四边面为主、无 N-gon、无松散点、变换已应用）、UV 完整、面数符合预算、原点与命名规范，再走 FBX 导出。

## 标准工作流（每个从零建模任务都走完）

```
1. 需求单 + 素材决策（先问 unity-blender-mcp 是否有现成资产）
2. 参考图：搜集 front/side/top，导入场景（model_helpers.add_reference_image）
3. 尺寸：确认真实尺寸，建人体标尺（--build-scale-rig）
4. Blockout：尺寸基元搭体量，只做几何关系，不做细节
5. 比例门禁：跑 `qa_render.py --gate --stage blockout`，IoU 或宽高比不过就改大形，不进入下一步
6. 细化：按类型选工作流（硬表面见 02，有机见 03；bpy 配方见 01）
7. 倒角/卡线/细分，控制硬边反光；Modifiers 非破坏
8. 拓扑检查（topology_audit.py）+ UV + 材质（见 04）
9. 成品门禁：`--stage final` 通过后，4 角度渲染 + 06 rubric 人审，逐项修问题清单
10. 按 07 做 LOD/面数/导出，交给 unity-blender-mcp 完成引擎接入
```

## 脚本（MCP 内可整段粘贴；命令行用 Blender headless）

| 文件 | 用途 |
|---|---|
| `scripts/model_helpers.py` | 公制单位、参考图导入（front/side/top）、尺寸精确的基元（米）、1.7m 人体标尺（7.5 头身）、尺寸测量与真实值对比 |
| `scripts/topology_audit.py` | 拓扑审计：V/E/F、tris/quads/ngons、松散顶点、非流形边、缩放是否应用、UV/材质、倒角存在性（--require-bevel 时强制）、面数预算；输出 JSON，有问题退出码 1 |
| `scripts/qa_render.py` | 两种模式：① 4 角度（35/125/215/305°）1280×720 质检渲染，中性灰背景、三点布光、角点法取景；② `--gate` 剪影门禁：正交渲染后与参考图算 IoU / 宽高比，不通过退出码 1 |

```bash
# 建一个带人体标尺的参考场景（在空场景里）
blender --background --python scripts/model_helpers.py -- --build-scale-rig
# 审计当前模型（--budget-tris 可按 07 的预算传）
blender --background --python scripts/topology_audit.py -- path/to/asset.blend --budget-tris 3000
# 出 4 张质检图
blender --background --python scripts/qa_render.py -- path/to/asset.blend --outdir C:/tmp/qa
# 剪影门禁（不通过返回 1，不会悄悄放过）
blender --background --python scripts/qa_render.py -- path/to/asset.blend --gate \
    --ref-front refs/front.png --ref-side refs/side.png --stage final --outdir C:/tmp/qa
```

MCP 内用 `execute_blender_code` 时：每块代码自包含、按名字重新选择对象、超时约 180s 就拆块；改用户场景前先另存；参考图/标尺放 `REF_*` 集合（审计与渲染默认跳过）。

## 参考文档索引（按需读取）

- `references/00-modeling-principles.md`：建模美学与比例原则、"AI 烂模特征清单"、自建/复用决策
- `references/01-bpy-recipe-library.md`：bpy 代码配方库（镜像/倒角/布尔后清理/重拓扑/细分/UV/材质/命名）
- `references/02-hard-surface.md`：硬表面工作流（道具、家具、武器、建筑、载具）
- `references/03-organic-sculpt.md`：有机雕塑与重拓扑（角色优先 Mixamo，雕塑只做怪物/岩石/植被）
- `references/04-topology-and-uv.md`：游戏级拓扑规范、UV 展开、texel density、法线/PBR 烘焙
- `references/05-prop-recipes.md`：常见道具分步配方（椅/桌/箱/桶/门/刀剑/枪械/建筑/岩石/树）
- `references/06-qa-critique-loop.md`：剪影门禁 + 渲染自评 rubric（10 维）+ 分阶段迭代 + 常见问题对照表
- `references/07-unity-handover.md`：面数预算、LOD、碰撞、原点/命名、FBX 交接清单（与 unity-blender-mcp 对接）

## 数据

- `assets/real-world-dimensions.csv`：常见道具/家具/建筑/武器/载具/自然物的真实尺寸（米），开工前查，渲染后对比。

## 完成定义（资产级 DoD，全勾才允许导出）

- [ ] 有 front/side 参考图，且模型与参考图轮廓一致
- [ ] 尺寸与真实值偏差 ≤ 15%（人体标尺旁对比）
- [ ] 所有硬边有倒角（0.5–3mm 量级），无廉价锐利边
- [ ] `topology_audit.py` 报告：无 N-gon、无松散点、无非流形、变换已应用、有 UV、有材质
- [ ] 三角面数符合 07 预算；需要 LOD 的资产做了 LOD0/1/2
- [ ] 剪影门禁 passed（front/side IoU ≥0.85、宽高比误差 ≤5%），`qa_gate.json` 留档
- [ ] 4 角度渲染 + 06 rubric 人审通过（倒角反光/穿插/厚度/材质/旧化）
- [ ] 原点在正确位置（道具几何中心底部、角色脚底），命名 `SM_` 前缀
- [ ] 已按 unity-blender-mcp 导出 FBX，在 Unity 中缩放/法线/材质正常
