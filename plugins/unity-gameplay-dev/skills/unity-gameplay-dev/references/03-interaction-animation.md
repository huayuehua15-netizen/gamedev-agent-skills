# 交互系统与动画（Animator）

> 目录：1. 交互层结构 → 2. 准星交互配置 → 3. 新增交互物（门/开关/NPC）→ 4. Animator 状态机规范 → 5. 动画事件与判定帧 → 6. 根运动决策 → 7. Mixamo/Humanoid 对接

## 1. 交互层结构

```
玩家相机/Interactor
  └─ 每帧 SphereCast（半径 0.08，距离 2.5，Layer=Interactable）
       └─ 命中 IInteractable → HUD 显示 PromptText → 按 Interact 调 Interact()
```

- `Interactor` 只找接口、发当前目标变更事件；不写具体交互逻辑。
- 具体物继承 `InteractableBase`：实现 `Interact`，可选重写 `PromptText`、`SetHighlight`。
- 高亮（描边）：URP Renderer Feature 屏幕空间描边，或材质自发光；在 `SetHighlight` 里切换。
- 交互层与 UI 解耦：Interactor 发 `TargetChanged(IInteractable)` 事件，HUD 订阅。

## 2. 准星交互配置（MCP）

1. 交互物预制体：Layer 设 Interactable，加碰撞体（IsTrigger 与否按物理需求；SphereCast 两种都能命中）。
2. 玩家 Interactor 字段：interactionMask 只勾 Interactable；raycast 起点用相机。
3. HUD 准星 + 提示文本（见 04）。
4. Play 验证：靠近时提示出现、离开消失、被墙挡住不触发、多物体取最近。

## 3. 新增交互物示例

门：状态机（Closed/Opening/Open/Closing），`Interact` 播动画/协程转铰链，锁门时返回失败并由 UI 提示需要钥匙。
开关：`Interact` 切换场景物体状态（灯/门/机关），发 EventBus 事件，系统订阅。
NPC：`Interact` 启动 DialogueRunner（见 05）。
注意：一次性交互物交互后禁用 Collider 或改标志位，避免重复触发。

## 4. Animator 状态机规范

- 控制器放 `Settings/AC_角色名.controller`；参数统一：
  - `Speed`（Float，移动速度 0→冲刺，Blend Tree 走/跑）
  - `IsGrounded`（Bool）、`Jump`（Trigger）、`Attack`（Trigger）、`Hit`（Trigger）、`IsDead`（Bool）、`IsChasing`（Bool，敌人）
- 结构：Base Layer（Locomotion）+ 上层 Attack/Hit（Has Exit Time 视动作定）；Dead 为终态。
- 转换：移动用 Blend Tree（Idle/Walk/Run 阈值 0/2/6）；攻击触发转换 `Has Exit Time = false`、`Fixed Duration = false`、Transition Duration 0.05~0.1。
- 用 `manage_animation` / Animator 窗口创建状态；MCP 无法表达的 Blend Tree 用 `execute_code` 调 `UnityEditor.Animations.AnimatorController` API 创建。

## 5. 动画事件与判定帧（GDD 数值必须落到帧）

- 攻击判定不要在按键瞬间生效，用**动画事件**：
  - 攻击动画第 X 帧（GDD 写，如第 8 帧）加事件 `NotifyAttackPerformed()`，EnemyAI/玩家武器在此回调里做一次伤害检测；
  - 结束帧 `NotifyAttackEnded()` 解锁输入。
- 判定窗口持续：事件开始时启用武器碰撞体/OverlapSphere，结束时关闭。
- 60fps 下帧数换算：`秒 = 帧/60`（0.13s≈8 帧）。GDD 写的"判定 0.13s"必须在对应动画帧上体现。
- 对话/拾取等反馈也用动画事件同步音效（见 07）。

## 6. 根运动（Root Motion）决策

- **第一人称玩家**：关闭 Root Motion，移动由 CharacterController 驱动，动画只做上半身/手臂表现。
- **敌人/第三人称**：推荐关闭 Root Motion、用 NavMeshAgent 驱动位移、Animator 做原地循环步（速度匹配防脚滑）；位移精确的处决/过场动画才开 Root Motion，开时用 `OnAnimatorMove` 把 deltaPosition 喂给 NavMeshAgent。
- 防脚滑：Blend Tree 阈值速度 = 实际移动速度；Agent 速度变化时平滑 `Speed` 参数。
- 验收：匀速移动脚部不打滑；转向有转身动画；攻击时位移与判定一致。

## 7. Mixamo / Humanoid 对接

- 角色 FBX：Animation Type=Humanoid，建 Avatar，检查映射 T-pose（资产管线技能负责导入）。
- 动作文件：同 Avatar；Loop Time 对循环动作勾选；Root Transform Position/ Rotation 按 Mixamo 规范 Bake Into Pose。
- 动画重定向后首检：手臂穿模、脚底滑动、朝向；在 Animator 预览与 Play 模式各看一遍。
- 骨骼动画事件挂在共享的 AnimationClip 上；用代码触发更稳的做法：在状态机 State 上挂 StateMachineBehaviour 或在动作帧加事件。
