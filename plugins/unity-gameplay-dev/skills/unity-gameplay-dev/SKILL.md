---
name: unity-gameplay-dev
description: "让 AI 通过 MCP（或命令行）自主完成 Unity 3D 单机游戏的玩法逻辑开发：从 GDD 规格到可玩、可测试、可构建的代码。覆盖 Unity 6（6000.x，第一人称、URP、UGUI、新 Input System）下的项目脚手架与代码规范、输入系统、第一人称控制器、准星交互、Animator 状态机、UI 面板栈/HUD、背包/对话/存档/对象池/音频、NavMesh 敌人 AI、Profiler 性能定位、构建发布与测试。提供可直接编译运行的 C# 框架模板（带 asmdef 与测试）和一键脚手架脚本。当用户要求在 Unity 里写玩法代码、做控制器/移动/视角、交互系统、背包/对话/存档、UI 菜单、敌人 AI、音效集成、性能优化、跑测试或出包，或把 GDD 规格落地为可玩功能时使用。与 unity-blender-mcp（资产管线）、aaa-game-gdd（设计文档）配套，不负责 3D 资产制作、不覆盖多人联机。 English: Unity 6 single-player gameplay development from GDD specs to playable, testable, buildable code: project scaffold, Input System, first-person controller, interaction, UI panel stack, inventory, dialogue, save system, object pooling, audio, NavMesh enemy AI, profiling, build and tests. Use when writing Unity gameplay code, controllers, interaction, UI, AI, or shipping a build."
---

# Unity 玩法开发技能（第一人称 / Unity 6 / URP）

> **路径约定（先读这一行）**：本文件里所有 `scripts/`、`references/`、`assets/` 都是**相对于本 SKILL.md 所在目录**。
> 执行脚本前先定位该目录。不同宿主的安装位置不同：Claude Code 插件在插件目录下；Cursor/Codex 由 `install.ps1`
> 装到 `<项目>/skills/game-dev/<技能名>/`。不确定时先用 `glob` 找到本 SKILL.md 的绝对路径，再用绝对路径调用脚本。
> 直接在项目根敲 `python scripts/xxx.py` 会 file-not-found。

## 概述

本技能把 GDD 规格和 3D 资产变成**可玩的游戏功能**：用 MCP 在 Unity 里创建/修改脚本、挂组件、配置动画与 UI、进 Play 模式验证、跑测试、出包。默认技术栈：Unity 6（6000.x LTS，兼容 6000.3）、URP、UGUI、新 Input System、Cinemachine 3（可选）、单机、无联机。

## 边界

- **做**：玩法逻辑、控制器、交互、UI、背包/对话/存档、AI、音频、测试、构建与性能定位。
- **不做**：3D 资产制作/导入/材质（交给 unity-blender-mcp 技能）；多人联机（Netcode）；Shader 手写（仅给特效选型建议）。
- **三种 3D 视角都有现成控制器**：第一人称 `FirstPersonController`、第三人称 `ThirdPersonController`、俯视角/双摇杆 `TopDownController`。状态机、输入、交互、UI、存档完全不变，只换控制器与相机；选型与差异见 `references/02` §6。
  **选错会直接毁手感**：第三人称的移动方向必须相对相机水平面，俯视角则必须相对世界坐标——两者的输入投影方式正好相反。
- **2D 项目**：架构层（状态机/事件总线/存档/背包/UI 栈）照用，但角色控制、物理、导航、性能预算必须换，
  见 `references/11-2d-gameplay.md`。不要拿 3D 的 `CharacterController` + `NavMesh` 去做 2D。

## 前置环境

- Unity 6000.x（6000.0 LTS 支持到 2026 年 10 月，之后应升 6000.3 LTS；代码两者兼容）。
- 必装包：`com.unity.inputsystem`（新输入系统）、`com.unity.ugui`（UGUI）、`com.unity.ai.navigation`（NavMesh 烘焙）、`com.unity.test-framework`（测试，脚手架随 `--tests` 自动写）；可选：`com.unity.cinemachine`、URP `com.unity.render-pipelines.universal`。
- 装包走 MCP `manage_packages`，或脚手架自动写 manifest（Input System / UGUI / 测试框架，版本按编辑器内置与主线回退表解析）；安装后 Project Settings → Active Input Handling 设为 Both（脚手架会写 `activeInputHandler: 2`）。
- 版本确认：项目里 `ProjectSettings/ProjectVersion.txt`；不确定 API 时用 `unity_docs` / `unity_reflect`，禁止凭记忆写不熟悉的 API。

## 标准工作流（从 GDD 到可玩功能）

### 流程 A：新项目/新工程从零搭建

1. **确认版本与管线**：`manage_editor` 读编辑器版本；项目 URP 还是 Built-in（材质和后处理不同）。
2. **跑脚手架**：`python scripts/new_gameplay.py --out "<项目>/Assets/Game" --namespace <游戏名>`，生成框架代码、asmdef、测试程序集，并自动补 Input System 依赖；**打开一次 Unity 让包下载后再重跑一次**以回填 asmdef GUID。
   - ⚠️ **首次编译报 `CS0234`/`CS0246`（找不到 `UnityEngine.InputSystem`）是预期行为**，不是脚手架坏了：全新项目还没下载包，读不到 InputSystem 的 asmdef GUID。打开一次 Unity 让包下载 → 重跑脚手架 → GUID 回填 → 再编译即零错误。
   - 已在 Unity 6000.0.84f1 实测：重跑后编译零错误，`InventoryTests` 3/3 通过。
3. **装场景引导对象**：按 `references/01` 建启动场景（GameManager、AudioManager、UIManager、EventSystem、Canvas），用 `manage_gameobject` / `manage_components`。
4. **按功能顺序实现**：输入 → 第一人称控制器 → 交互 → HUD → 具体玩法系统 → AI → 音频/VFX（顺序见下「功能开发顺序」）。
5. **逐功能验证**：每完成一个功能，Play 模式手测 + 写 EditMode/PlayMode 测试，见 `references/00` 的验证循环。
6. **导航/烘焙/构建**：NavMesh 烘焙、场景入 Build、出包前清单，见 `references/08`、`references/09`。

### 流程 B：单个功能开发（最常见）

读 GDD 对应单页（角色/交互/系统/对话/动画规格）→ 列出要改的脚本与组件 → 选模板或新建 → 按 MCP 编辑循环实现 → Play 验证 → 补测试 → 更新功能完成定义。

### 流程 C：排错与优化

编译/运行报错查 `references/10`；掉帧/卡顿走 `references/08` 的 Profiler 流程；MCP 操作失败按 `references/00` 的降级方案。

## MCP 编辑循环（每次改代码都遵守）

1. `refresh_unity` 先同步磁盘；`read_console` 确认起点无错。
2. 建脚本：`create_script`；改脚本：**优先 `script_apply_edits`（结构化方法级编辑）**，小改才用 `apply_text_edits`；改完 `validate_script`。
3. `refresh_unity` 触发编译 → `read_console` 看编译结果（有 CS 错误立即修，不允许带错继续）。
4. 挂组件/配引用：`manage_components` / `manage_gameobject`；动画用 `manage_animation`；UI 用 `manage_gameobject`（UI Toolkit 才用 `manage_ui`）。
5. 进 Play 模式验证：`manage_editor` 切换 playmode，`read_console` 查运行时异常；视角/手感用 `find_gameobjects` 读 Transform 状态确认，必要时 `execute_code` 截图 Game View。
6. 多个不冲突操作合并进 `batch_execute`；每个功能结束前 `manage_scene` 存盘。

## 功能开发顺序（脚手架之后）

```
1. 输入 InputReader（脚手架已生成）→ 场景里挂 Player，WASD/鼠标动起来
2. 第一人称 PlayerLook + FirstPersonController（走、跑、跳、蹲、落地）
   - 2D 项目改用 `PlatformerController2D`（`--dimension 2d` 时自动生成，3D 专用文件不会生成）
3. 交互 Interactor + 门/拾取物（准星提示 UI 打通）
4. HUD + 菜单面板栈（UIManager，ESC 暂停）
5. 玩法系统：Health/背包/对话（按 GDD 取舍）
6. 存档 SaveSystem（把已做系统接入 ISaveable）
7. 敌人 AI：NavMesh 烘焙 + EnemyAI + 感知
8. 音频 AudioManager + 混音器；VFX（粒子/枪口/命中）
9. 性能 Profiler 定帧；构建出包（references/08、09）
```

## 脚手架与模板

```bash
python scripts/new_gameplay.py --out "D:/MyProject/Assets/Game" --namespace MyGame
#   --no-tests：不生成测试程序集
#   --editor-data "Editor/Data 路径"：解析 Input System 版本（不传则按版本回退表）
```

模板清单（`assets/templates/`）。注意：模板里含 `{{NS}}` 命名空间占位符，**手动复制时先替换，或直接跑 `new_gameplay.py` 自动生成**，否则无法编译：

| 模块 | 文件 | 用途 |
|---|---|---|
| Core | `PersistentSingleton` / `StateMachine` / `EventBus` / `GameManager` / `GameEvents` | 单例、状态机、事件总线、游戏流程（菜单/游戏/暂停/加载） |
| Input | `InputReader` | 新 Input System 代码化封装，键鼠+手柄 |
| Player | `FirstPersonController` / `PlayerLook` / **`ThirdPersonController`** / **`TopDownController`** / **`PlatformerController2D`** | **三种 3D 视角 + 2D 平台跳跃**，见 `references/02` §6 选型表：第一人称（输入相对自身）、第三人称（相对相机水平面）、俯视角/双摇杆（世界坐标，可移动与瞄准解耦）；2D 用 Rigidbody2D |
| Interaction | `InteractableBase` / `Interactor` / `PickupItem` | 准星交互、拾取示例 |
| Systems | `Health` / `Inventory` / `SaveSystem` / `DialogueRunner` / `ObjectPool` / `AudioManager` | 生命、背包、JSON 存档、线性对话、对象池、音频 |
| AI | `EnemyAI` / `EnemyPerception` | NavMesh 巡逻/追击/攻击状态机 + 视锥感知 |
| UI | `UIPanel` / `UIManager` / `HUDController` | 面板栈、HUD 血条/提示/字幕 |
| Tests | `InventoryTests`（+ asmdef） | 背包逻辑测试样例，`run_tests` 可跑 |

## 参考文档索引（按需加载）

- `references/00-mcp-code-workflow.md`：MCP 47 个工具按玩法任务映射、编辑循环、Play 验证、测试、无 MCP 降级
- `references/01-architecture.md`：目录结构、asmdef、命名规范、数据驱动、引用/事件/单例使用边界、ScriptableObject
- `references/02-input-and-fp-controller.md`：Input System 落地、Player 预制体层级、移动视角参数表、**三种视角选型（第一/第三/俯视双摇杆）与各自的手感陷阱**
- `references/03-interaction-animation.md`：交互层、Animator 状态机/Blend Tree/根运动、动画事件、Humanoid 对接
- `references/04-ui-ugui.md`：Canvas/EventSystem 搭建、面板栈、HUD、暂停、输入切换
- `references/05-gameplay-systems.md`：血量/背包/对话/存档/对象池的使用与扩展规范、数据定义
- `references/06-ai-navigation.md`：NavMesh 烘焙、敌人配置、巡逻点、感知调参、状态扩展
- `references/07-audio-vfx.md`：AudioMixer 分组、音频池、音乐淡变、粒子/VFX Graph 选型
- `references/08-performance.md`：60fps 预算、Profiler/Frame Debugger 流程、常见热点
- `references/09-build-release.md`：构建设置、场景清单、Steam/Deck 检查、存档兼容
- `references/10-troubleshooting.md`：编译/空引用/执行顺序/输入/导航/UI 常见错误对照
- `references/11-2d-gameplay.md`：**做 2D 项目先读这篇**。2D 包安装、Sprite 导入、Physics2D 与层矩阵、
  2D 平台跳跃（coyote time/jump buffer）、Tilemap 与 Composite 碰撞、像素完美相机、
  **以 overdraw 与 Batch 计的 2D 预算**（三角面预算表对 2D 无意义）。

> **2D 项目注意**：本技能的 C# 模板默认是 3D 第一人称（`CharacterController`、`NavMesh`）。
> 2D 请复用与维度无关的部分（`EventBus`、`StateMachine`、`Inventory`、`SaveSystem`、`Health`、
> `ObjectPool`、`UIManager`、`AudioManager`），而控制器、导航、物理、性能预算按 `references/11` 重写。

## 铁律

- **数值来自 GDD**：移速、跳跃、伤害、判定帧、视野距离都要在 Inspector 暴露且与 GDD 单页一致；GDD 没写的标 `【待确认】`，禁止编数字。
- **每步必须可验证**：改完代码编译零错、Play 模式实测；手感类（移动/视角/攻击）必须录得到 Transform/状态证据，不能只说"应该可以"。
- **禁止假编译**：`validate_script` 或 `read_console` 没过就不算完成；无法在本环境验证时明确声明，不编造结果。
- **数据与逻辑分离**：可调数值用 SerializeField/ScriptableObject；表现层订阅事件，不写进系统类。
- **命名规范**：类 PascalCase；文件名与主类名一致；场景/预制体 `Level_01_`、`PF_Player`；常量不含中文；Console 出现 CS 警告也要修。
- **小步提交**：一个功能一个 commit；改前存盘/备份场景；危险操作（删除、批量改组件）先列出影响对象。

## 功能完成定义（DoD）

- [ ] 实现的逻辑与 GDD 单页一致，数值可追溯（行业默认值已标注）
- [ ] 编译零错零警告（`read_console` 截图/读数为证）
- [ ] Play 模式实测通过：输入、状态切换、交互、反馈都能复现
- [ ] 可单元测试的逻辑有测试（`run_tests` 绿）
- [ ] 相关引用/组件/层级配置完整（预制体拖入空场景即可用，不依赖手工临时连线）
- [ ] 存档新增字段已处理版本号；新增场景已入 Build
- [ ] 性能无新增热点（目标 60fps，移动端/Deck 见 08）
