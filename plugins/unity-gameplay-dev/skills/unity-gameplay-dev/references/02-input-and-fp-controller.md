# 输入系统与第一人称控制器

> 目录：1. Input System 落地 → 2. Player 预制体层级 → 3. 控制器参数表（行业默认值）→ 4. 搭建步骤（MCP）→ 5. 常见手感问题 → 6. 第三人称/俯视角分支

## 1. Input System 落地

- 项目装 `com.unity.inputsystem`（脚手架自动）；Active Input Handling 设 Both（脚手架写 `activeInputHandler: 2`）。
- 本套**不使用 .inputactions 资产**，而在 `InputReader` 里用代码构建动作（便于版本管理、无 GUID 依赖）。动作：
  - `Move`（2D Vector，WASD/左摇杆，2D 复合绑定）
  - `Look`（2D Vector，鼠标 Delta/右摇杆，鼠标绑定为 1D 轴合成 + Delta）
  - `Jump`（Button，空格/手柄 South）
  - `Sprint`（Button，Left Shift）
  - `Crouch`（Button，Left Ctrl/Circle）
  - `Interact`（Button，E/手柄 West）
  - `Attack`（Button，左键/RT）
  - `Pause`（Button，Esc/Start）
- 控制器只读 `InputReader` 的 C# 属性与事件（**实际成员名以 `InputReader.cs` 为准**）：
  - 持续量属性：`Move`（Vector2）、`LookMouse`（鼠标像素增量）、`LookStick`（摇杆 -1..1）；
  - 离散事件：`JumpPerformed`、`InteractPerformed`、`AttackPerformed`、`PausePerformed`，
    以及 `SprintChanged(bool)` / `CrouchChanged(bool)`。
  - 鼠标与摇杆**刻意分成两个属性**：像素/帧与 -1..1 差一个数量级，合并成一个 Look 会让两种设备手感无法同时调好。
  - 不要直接碰 `InputAction`；也不要自己再建一份输入表。
- 注意：鼠标 Look 绑定 `<Mouse>/delta`；手柄 Look 绑定 `<Gamepad>/rightStick`；移动复合绑定 `WASD` 用法用 `AddCompositeBinding("2DVector")` + With("Up","<Keyboard>/w")...。
- 手柄 UI 导航：EventSystem 上 `InputSystemUIInputModule` 替代 Standalone Input Module（装包后自动替换；没替换就手动换）。

## 2. Player 预制体层级（PF_Player）

```
PF_Player (Layer: Player)
├── Capsule (mesh, 子物体，只做视觉；或直接引用美术角色模型)
├── Camera Rig (空物体，PlayerLook 挂这里)
│   └── MainCamera (Camera，AudioListener；眼睛高度 1.6m；蹲 0.9m)
├── [CharacterController]  中心 Y=0.9，高 1.8，半径 0.3，Skin Width 0.08
├── [FirstPersonController]
├── [PlayerLook]
├── [Interactor]
├── [Health]
└── [Inventory]
```

- `FirstPersonController` 持 CharacterController + Transform cameraPivot；相机枢轴本地 Y=眼高，X/Z=0。
- 蹲下改 CharacterController.height（1.8→1.0）、center.y（0.9→0.5）、相机高度（1.6→0.9），用 Lerp 平滑（0.12s）。
- 玩家物理层 Player；地面 Ground；交互物 Interactable；敌人 Enemy。

## 3. 控制器参数表（第一人称行业默认值，首测后调）

| 参数 | 默认值 | 说明 |
|---|---|---|
| 走路速度 | 4.5 m/s | 写实风格；快节奏 FPS 用 5.5 |
| 冲刺速度 | 7.0 m/s | 约 1.55x 走速 |
| 蹲走速度 | 2.2 m/s | |
| 跳跃高度 | 1.2 m | 用 `v=sqrt(2gh)` 反推初速度 |
| 重力 | -20 m/s² | 比真实 -9.81 更"爽"，落地更快 |
| 加速时间（地面） | 0.12 s | 速度插值，避免瞬起 |
| 空中操控 | 0.4 倍 | |
| 鼠标灵敏度 | 0.0012 rad/px（约 0.07°/px） | 菜单里给 0.1~3 倍调节 |
| 手柄灵敏度 | 120 deg/s（`stickSensitivity`） | 与鼠标分开成两个 action，带非线性死区曲线 |
| 俯仰限制 | ±85° | 防翻转 |
| 落地判定 | 连续接地 0.05s | 避免斜坡/台阶误判离地 |
| 台阶高度 | 0.3~0.4 m | CharacterController.slopeLimit=45°、stepOffset=0.35 |

GDD 写了具体数值的，以 GDD 为准并在 Inspector 覆盖。

## 4. 搭建步骤（MCP）

1. `manage_gameobject` 建 PF_Player（Capsule 临时占位，美术到位后替换子物体），加 CharacterController、FirstPersonController、PlayerLook、Interactor、Health、Inventory。
2. 建 Camera Rig 子物体 + MainCamera 子物体，Camera tag=MainCamera，加 AudioListener。
3. 挂 InputReader（在 Player 或 GameManager 上，同场景一个），拖引用。
4. `manage_components` 按第 3 节填参数。
5. 地面放一个大 Plane（Layer Ground），`manage_gameobject` 加。
6. Play 模式：WASD/鼠标/跳跃/冲刺/蹲下逐项验证，读 Transform.position 变化与 `CurrentSpeed`，截图。
7. 验收：贴地不抖、下斜坡不弹、冲刺有加速度、蹲时镜头平滑下降、Pitch 不翻转。

## 5. 常见手感问题

| 现象 | 原因/修法 |
|---|---|
| 移动滑/停不住 | 加速度插值过大或没做地面摩擦；把 `Time.deltaTime` 插值系数调小 |
| 视角卡顿/撕裂 | 相机放 LateUpdate；垂直同步或 URP 目标帧率；检查 Time.maximumDeltaTime |
| 跳不起来 | 接地判定误判离地；用 `controller.isGrounded` + 连续接地计时；台阶边缘加皮肤宽度 |
| 下坡弹飞 | 垂直速度恒为重力累积；接地后强制 vy=-2 贴地；高处在 OnControllerColliderHit 处理台阶 |
| 撞墙抖 | 不要对撞墙方向施加速度；用 `controller.Move` 返回 CollisionFlags 处理 |
| 蹲下起不来 | 头顶有碰撞，用 `controller.height` 变更前做 CapsuleCast 检测，挡住就保持蹲 |
| 鼠标太飘/太慢 | 灵敏度菜单可调；手柄加响应曲线 `x²`；鼠标加原始读取（delta 已在输入层） |

## 6. 第三人称 / 俯视角分支

- 第三人称：相机换成 Cinemachine 3 `CinemachineCamera`（Unity 6 已无 VirtualCamera），Brain 挂 Main Camera；目标 = 玩家 + 肩部偏移；移动方向相对相机 yaw。控制器换 `ThirdPersonController`（NavMesh/Rigidbody 或 CharacterController 均可），新增 Animator 驱动（见 03）。
- 俯视角：Move 直接映射世界方向，相机正交跟随（Cinemachine PositionComposer），鼠标点地交互用射线。
- 状态机、输入、交互、背包、UI、存档全部不变；只替换 Player/相机两个组件。
