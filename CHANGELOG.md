# 更新日志

本项目从 1.1.0 起按语义化版本记录。格式参考 Keep a Changelog。

## [1.2.0] - 2026-11-04

### 新增：三种 3D 视角都有控制器了

此前 `SKILL.md` 写着"第三人称/俯视角沿用同一套架构，仅控制器与相机分支不同"，
但**实际只有一个第一人称模板**——文档承诺了两个代码不存在的选项。
现在补齐：

| 视角 | 控制器 | 输入方向相对谁 | 角色朝向 |
|---|---|---|---|
| 第一人称 | `FirstPersonController`（原有） | 角色自身 | 与视角合一 |
| 第三人称 | `ThirdPersonController`（新增） | **相机水平面** | 转向移动方向，有转速上限 |
| 俯视角 / 双摇杆 | `TopDownController`（新增） | **世界坐标** | 转向移动方向；双摇杆时转向瞄准 |

三者的状态机、输入、交互、背包、UI、存档完全不变，只换控制器与相机。

**最容易选错的一点**（已写进 `references/02` §6）：
第三人称的移动方向必须相对相机水平面，俯视角必须相对世界坐标——
两者的输入投影方式正好相反，选错直接毁手感。
双摇杆另有第三条规则：朝向跟瞄准，不跟移动。

第三人称还补了两个容易漏的细节：
- 蹲伏同步 `controller.height`，起身前 `SphereCast` 查头顶，防止在低矮通道穿模
- 喂 `LocalMoveX/LocalMoveZ`（世界速度转到角色空间），可直接接 8 向混合树

**真机验证**：在 Unity 6000.0.84f1 中用 `--dimension 3d` 生成并编译，
**零 CS 错误**，产出 `TPTest.dll`（51 KB，比只有第一人称时的 36 KB 增加两个类）。
2D 模式确认不会带入这三个 3D 控制器。

## [1.1.1] - 2026-11-04

### 修复：CI 从未通过过

从加入 CI 到 1.1.0 发行为止，**全部 20 次运行都是红的**。
此前只在本机手工复刻各个步骤就认为没问题，这是错误的判断方式。
以下是逐层挖出来的四个独立原因：

1. **内联 heredoc 在 Windows 上不可用**。步骤里写了 `python - <<'PY'`，
   而 windows-latest 的默认 shell 是 pwsh，不支持 heredoc；
   且结束符在 YAML 块内缩进错位，在 Linux 上同样会挂。
   现在所有检查都是 `tools/` 下的真实文件，CI 只负责调用。

2. **PyYAML 被当成预装**。注释里写着 "PyYAML ships preinstalled"，
   实际依赖步骤只装了 numpy，于是 ubuntu 的 frontmatter 校验直接 ImportError。
   现在显式安装，且 `validate_skills.py` 在缺 PyYAML 时降级为模式匹配而不是崩溃。

3. **脚本 print 中文在 Windows 控制台崩溃**。Windows 默认编码是
   cp1252/cp936，`print("已写入 manifest.json…")` 会抛 UnicodeEncodeError，
   脚手架直接挂掉——这正是 Windows 用户最常见的运行方式。
   17 个脚本现在都带内联 UTF-8 守卫。
   （守卫必须内联：Blender 用 `--python` 执行脚本时不把脚本目录加入
   `sys.path`，`import _utf8` 会 ModuleNotFoundError。）

4. **门禁参数校验的退出码断言过严**。本机 Blender 5.2 返回 2，
   ubuntu 上的 Blender 返回 1——不同版本对 `--python-exit-code` 的归一化不同。
   真正要保证的性质是"拼错必须失败、不能静默退出 0"，
   所以断言改成非 0，并在标签里写明。

### 修复：诊断能力

失败时只报 `exit=1` 让人无从下手，而 GitHub 的 job 日志和 artifact
都需要 admin 权限才能下载。现在：

- `check_toolchain.py` 记录每个子进程的 stdout/stderr，失败时打印出来。
- CI 把失败行以 `::error::` 注解形式输出，可通过公开 API 读取。
- GL 探测按**真实分辨率**（512×512 RGBA）用图，而不是 32×32：
  小图能过、大图失败，曾导致探测结果与实际检查不一致。
- 参考剪影改用 numpy+zlib 合成，不再依赖渲染——
  纯数学步骤不应该依赖 GPU。

### 已知限制：CI 不跑渲染类检查

GitHub 的 ubuntu runner 没有 GPU。即使装上 libegl1 / libgl1 / libgles2 /
libgl1-mesa-dri / libosmesa6，Workbench 在这个环境里仍不稳定
（能渲染小图，512×512 RGBA 必失败）。因此 CI 显式设 `BLENDER_SKIP_RENDER=1`，
只验证不依赖 GPU 也必须正确的部分：拓扑判定三项 + 参数校验两项。

剪影门禁与转盘渲染仍需在**有 GL 的环境**验证：
`python tools/check_toolchain.py`（本机实测 8/8，IoU 1.0 通过 / 0.3534 拒绝）。

## [1.1.0] - 2026-11-03

这一版的主题是**让门禁真的能拦住问题**，并修正会误导使用者的错误事实。
首发版 1.0.0 的门禁存在多处「失败却返回成功」的缺陷。

### 新增：2D 平台跳跃控制器（已在真机编译验证）

补上 2D 轨道最后缺的一块：**有文档没代码**。

- 新增 `PlatformerController2D.cs`：Rigidbody2D 方案，含
  **Coyote Time**（离开平台 0.10s 内仍可跳）、**Jump Buffer**（落地前 0.10s 按跳有效）、
  可变跳跃高度、`Physics2D.OverlapCircle` 地面检测、连续碰撞检测防穿地板。
  这三个手感辅助件是"跳得粘不粘"的分水岭，缺了明显差。
- `InputReader` 增加只读的 `JumpAction`：`JumpPerformed` 只报按下瞬间，
  做"松手截断上升"时读不到持续态。

### 修复：`--dimension 2d` 会生成编译不过的工程

实测发现的真实缺陷：2D 模式虽然装了 `com.unity.2d.*`，但**仍然生成 3D 专用文件**。
2D 项目通常不启用 Physics/AI 内置包，于是：

```
error CS1069: 'CharacterController' could not be found ...
  forwarded to assembly 'UnityEngine.PhysicsModule' — Enable the built in package 'Physics'
error CS1069: 'NavMeshAgent' ... 'UnityEngine.AIModule' — Enable the built in package 'AI'
```

现在脚手架按维度裁剪：2D 跳过 `FirstPersonController`/`PlayerLook`/`EnemyAI`/
`EnemyPerception`/`Interactor` 等 7 个 3D 专用文件，3D 跳过 `PlatformerController2D`。
两边都实测：2D 生成 17 个文件、3D 生成 22 个文件，互不污染。

**真机验证**：2D 工程在 Unity 6000.0.84f1 编译**零错误**，
产出 `G2D.dll`（36 KB）与 `G2D.Tests.dll`（5.6 KB）。

### 新增：8 类单页全部有完整范文

此前只有场景页有范文，其余 7 类只有空模板，AI 填出来的质量明显低于场景页。
现在 8 类各有一份完整范文，且**全部在同一个虚构项目内互相引用**，形成一张可追的文档网：

| 类型 | 范文 | 演示的重点 |
|---|---|---|
| 场景（恐怖/线性） | `SC_01_外科楼二层走廊` | 视线遮蔽型空间供给 |
| 场景（开阔/BOSS） | `SC_07_断桥瞭望台` | 距离/环形/坠落风险型空间供给 |
| 关卡 | `LV_01_走廊初遇` | beat 表与 `TZ_` 对账、不靠弹窗的教学 |
| 角色（敌人） | `EN_01_缝合者` | 速度差为何是"跑得掉"、战斗时长怎么算出来 |
| 道具 | `PR_017_缺轮轮椅` | 技术规格取值、"有意不做"怎么写 |
| 动画 | `AN_EN01_Slash_01` | 三段式帧区间、预告音是公平性底线 |
| 对话/过场 | `DL_07_护士长录音` | 台词 ID、时长估算、字幕合规、中断续播 |
| 系统 | `SYS_04_抓取挣脱` | 参数表带设计意图、边界一个不漏 |

范文刻意保留了两处**真实踩坑记录**，因为设计教训比结论更有价值：
- 抓取系统初版把推开距离设为 2.0m，小于敌人攻击距离 2.6m，导致"抓→挣脱→再抓"死循环，
  实测连抓 4 次打死玩家；现改为 3.2m 并写明约束原因。
- 断桥场景的三角面预算刻意**高于**走廊（32 万 vs 25 万），因为开阔场地剔除效率低，
  文中注明原因，避免被读成放宽标准。

### 新增：范文自动校验

- `tools/validate_examples.py`：校验每份范文是否覆盖其模板的**全部章节**，
  以及引用的 `TZ_/EV_/SC_/PR_/SYS_/AN_/DL_/EN_` 编号是否真实存在（无悬空引用）。
- 已接入 CI（`Examples match their templates` 步骤），范文与模板脱节会直接挂 CI。
- 该工具立刻发现一处真实问题：`SC_01` 的章节名是"玩法要素"，与模板的"空间与玩法要素"不一致，
  已统一。

### 新增：英文 README

- 新增 `README.en.md`：与中文版信息等价的英文文档（快速上手、技能选型表、2D 边界、
  兼容安装、门禁口径、Unity 编译验证、已知限制全部覆盖）。
- 两版顶部互相链接，可一键切换语言。
- 英文版额外增加一节 `A note on language`，说明**技能内容（SKILL.md / references）
  仍为中文**，而脚本与门禁与语言无关——避免英文用户下载后发现文档是中文而失望。
- 已核对两版的关键数字一致（IoU、阈值、容差、DLL 体积、Unity/Blender 版本等 13 项）。

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
