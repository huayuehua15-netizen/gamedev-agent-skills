# 更新日志

本项目从 1.1.0 起按语义化版本记录。格式参考 Keep a Changelog。

## [1.1.0] - 2026-11-03

这一版的主题是**让门禁真的能拦住问题**，并修正会误导使用者的错误事实。
首发版 1.0.0 的门禁存在多处「失败却返回成功」的缺陷。

### 新增：Unity 模板的真机编译验证

此前 C# 模板只做了 API 对照，**从未在真实编辑器里编译过**，这一条一直挂在"已知限制"里。
现已在真实 **Unity 6000.0.84f1** 中完成验证：

- 22 个 C# 模板编译零错误，产出 `GateTest.dll`（45 KB）与 `GateTest.Tests.dll`（5.6 KB）。
- `InventoryTests` 三个用例在 EditMode 下全部通过（3/3）。
- 同时验证了"首次运行需重跑一次脚手架回填 InputSystem GUID"这一设计：
  首次编译报 `CS0234`/`CS0246` 属预期，重跑后 GUID 正确回填，编译即通过。

> 验证在一个隔离的临时项目中进行，未触碰仓库使用者的任何现有工程。

### 新增：CI 与可视化证据

- **GitHub Actions**（`.github/workflows/ci.yml`），两个 job：
  - `python`：在 Ubuntu/Windows × Python 3.10/3.12 上跑语法编译、门禁数学单元测试、
    JSON 校验、SKILL.md frontmatter 校验、两个脚手架的产物校验（asmdef 可解析、
    2D/3D 包差异、三种引擎输出不相同）、以及 `dist/` 与 `plugins/` 的一致性。
  - `blender`：装真 Blender，验证门禁**退出码**确实可信——
    干净资产退 0、缩放未应用退 1、文件不存在退 2、拼错的 `--gate=1` 退 2。
- **门禁对比截图** `docs/images/silhouette-gate.png`，展示同一张参考图下
  正确模型（IoU 0.9965，退 0）与错误比例（IoU 0.3669，退 1）的判定结果。
  图上的数字是脚本返回原值，不是示意图。
- **可复现**：截图由 `tools/make_gate_screenshot.py` 生成，跑真实门禁脚本后拼图。
  改了门禁逻辑就重跑，避免截图与代码脱节。

### 修复：门禁失效（最重要）

- **退出码统一为三档语义**：`0` 通过 / `1` 检查未通过 / `2` 参数或输入问题。
  此前 `blender_asset_audit.py`、`blender_asset_qa_render.py`、`model_helpers.py`
  的失败路径全部返回 0；Blender 默认 `--python-exit-code=0` 使异常也显示成功。
- **`qa_render.py` 不再静默吞参数**。原实现 `else: i += 1` 会丢掉一切不认识的参数，
  于是 `--gate=1` 意味着**门禁根本没跑**却退出 0。现在未知参数、`=` 写法、
  拼错的 `--stage` 全部报错。
- **三角面预算改为计算求值后的网格**。此前按基础网格计算，而 FBX 导出会应用修改器：
  一个带 Bevel 的资产按 12 面判定合格，实际导出 588 面。且 `--require-bevel`
  正在鼓励添加 Bevel，两者互相冲突。
- **空目标集不再等于通过**。`--selection-only` 在 `--background` 下选不中任何对象时，
  原来打印「0 个网格，0 个有问题」并退出 0。
- **不再审计 Blender 启动场景**。`blender_asset_audit.py` 无参数时审计默认的
  Cube/Camera/Light 并输出一份格式合法、内容完全错误的「体检通过」。
- **MCP 粘贴模式恢复可用**。`blender_asset_qa_render.py` 的兜底逻辑引用了
  `__name__` 却写在自己的守卫之后，`exec()` 时必然 `NameError`。

### 修复：细长物体的剪影门禁假阴性

模型与**自己的参考图**比较时，长宽比 ≥20:1 也会被判不合格。原因有三层：

1. 正交取景下长边撑满画面，短边只剩不到 10 像素；
2. 归一化画布仅 256px，取整误差被放大；
3. 宽高比容差是固定值，没考虑短边采样不足。

现改为：按长宽比自适应提高剪影渲染分辨率（保证短边 ≥48px）、归一化画布提到 512、
并加入**基于短边像素数的量化容差**（该项会写进 JSON 报告，不是隐藏放水）。

实测：长宽比 1:1 ~ 40:1 自比全部通过；而真正的形状错误（IoU 0.10~0.49）
仍然全部被拒，无漏判。

### 修复：产生错误资产的缺陷

- **Unity 前向轴写反**：原文档写 `-Z forward`，实际是 `+Z`。按原文档导出的资产全部朝向反了。
- **HDRP Mask Map 通道顺序错误**，会把金属度与 AO 对调。
- **RMA 与 ORM 被写成完全相同的定义**，而二者按定义 R/B 通道相反。
- **`UCX_` 被当作通用规则**，它是 Unreal 专用前缀，Unity 与 Godot 均不识别。
- **Steam Deck 内存少算一倍**（8GB → 实际 16GB LPDDR5）；分辨率 `1200×800` 不存在。
- **Steam 商店胶囊图全套为 2024 年停用的旧尺寸**，且缺少必填的竖版胶囊 748×896。
- **IARC 误标**：Steam 使用自家的 Content Survey，IARC 是 Google Play / 主机平台那套。
- **三角面预算一个数字同时服务 3A 与独立团队**，且与仓库自带示例相差 20 倍。现分三档。
- **`AssetPostprocessor.cs` 会毁掉 2D 美术**：所有贴图被强制设成 3D 规则
  （双线性、开 Mipmap、Repeat、2048 上限），像素画过一遍即废，而日志显示成功。

### 修复：脚手架首次运行失败

- **`new_gameplay.py` 在全新项目上写出非法 JSON**。清理零 GUID 引用时按行过滤，
  留下数组尾逗号，Unity 直接报 asmdef 解析失败——而这正是文档写明的首次运行路径。
  现改为 JSON 往返。
- **包版本回退表从未生效**。原逻辑依赖 `ProjectVersion.txt`，该文件只在项目被打开过
  后才存在；全新项目上所有包（含 Input System）都解析为 `None` 并被跳过。
- **`Game.Tests.asmdef` 使用 2019 年即弃用的 `optionalUnityReferences`**，
  改为显式 `UnityEngine.TestRunner` / `UnityEditor.TestRunner` 引用。
- **asmdef 的 `.meta` 用了错误的 importer**（`MonoImporter`），会导致重新导入并可能改写 GUID。
- **`--add-packages` 是空操作**（`store_true` 配 `default=True`）。

### 修复：Unity 模板的三个真实 bug

- `UIManager.Open<T>()` 重复打开同一面板会重复入栈，导致菜单再也关不掉。
- `SaveSystem.Write()` 不清空既有条目，同一 `SaveData` 写两次会产生重复 key。
- **ESC 从未真正暂停**：`TogglePause()` 零调用者，按下后只解锁了鼠标，角色仍在移动。

### 新增：2D 支持

- `unity-gameplay-dev` 新增 `references/11-2d-gameplay.md`：2D 包安装、Sprite 导入对照表、
  Physics2D 与层碰撞矩阵、2D 平台跳跃（coyote time / jump buffer）、Tilemap 与
  Composite 碰撞、像素完美相机，以及**以 overdraw 与 Batch 计的预算表**
  （三角面预算对 2D 无意义）。
- `aaa-game-gdd` 新增 `sprite-sheet.md` 与 `tileset-sheet.md` 两个模板。
- 两个脚手架均支持 `--dimension 2d`：2D 会额外写入 `com.unity.2d.*` 包并创建
  `sprites/`、`tilesets/` 子目录。
- `AssetPostprocessor.cs` 增加 Sprite 分支，按命名或路径自动走 2D 导入设置。

### 新增：引擎真正可切换

- `new_gdd.py --engine` 此前只替换一个显示名，现在会**真正写入**该引擎的
  交换格式、轴向、碰撞命名、导航系统、数据资产、LOD 机制与测试框架。
  已实测 Unity / Godot / Unreal 三种产出互不相同且无残留占位符。

### 新增：宿主兼容性

- 四个 `SKILL.md` 均补充路径锚定说明（路径相对 SKILL.md 所在目录）。
  Cursor/Codex 的安装位置与 Claude Code 不同，裸相对路径会 file-not-found。
- 四个 description 追加英文子句，改善英文提示下的技能检索。
- 文档中的 Blender 命令全部补上 `--python-exit-code 1`。

### 新增：项目文档

- `CONTRIBUTING.md`：贡献标准、提交前自检、硬性规则。
- `CHANGELOG.md`：本文件。
- `README.md` 增加「2D 支持边界」与退出码约定，并补充细长物体的已知限制。

### 已知限制

- C# 模板已在 Unity 6000.0.84f1 编译通过，但未覆盖 6000.3、Built-in 渲染管线与其他平台。
- 剪影门禁只能校验外轮廓与比例，无法校验细节、材质与气质。
- 参考图必须是正交视图；带透视的照片必然失败。
- 2D 资产管线仍以 3D 素材库为主。

## [1.0.0] - 2026-10-31

首发：四个技能（`aaa-game-gdd`、`unity-blender-mcp`、`blender-modeling-craft`、
`unity-gameplay-dev`），含文档模板、资产管线、建模手艺、玩法框架与剪影门禁。
