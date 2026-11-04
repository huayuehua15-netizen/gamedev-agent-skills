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

## 6. 三种视角：选哪个控制器

三个控制器都在 `assets/templates/Game/Player/`，共用同一套 `InputReader`、
`CharacterController` 方案与 Animator 参数（`MoveSpeed` / `IsGrounded`），
**状态机、交互、背包、UI、存档完全不变**——只换 Player 上的控制器 + 相机。

| 视角 | 控制器 | 输入方向相对谁 | 角色朝向 | 典型品类 |
|---|---|---|---|---|
| 第一人称 | `FirstPersonController` + `PlayerLook` | 角色自身 | 与视角合一 | FPS、恐怖、沉浸模拟 |
| 第三人称 | `ThirdPersonController` | **相机水平面** | 转向移动方向（有转速上限） | 动作冒险、类魂、开放世界 |
| 俯视角 / 双摇杆 | `TopDownController` | **世界坐标** | 转向移动方向；双摇杆时转向瞄准 | 幸存者 like、ARPG、双摇杆射击 |

### 6.1 三者最容易搞混的地方（选错了手感直接崩）

- **第三人称：移动方向必须相对相机，不是相对角色。** 若相对角色，
  角色一转身输入方向就跟着转，玩家会感觉"按左却往右走"。
  `ThirdPersonController` 用 `CameraRelativeDirection()` 把输入投影到相机水平面上。
- **俯视角：移动方向不能相对相机。** 相机是斜俯角，投影到水平面后
  "上"会变成"斜后方"。`TopDownController` 直接用输入的世界轴向。
- **双摇杆：朝向跟瞄准，不跟移动。** `twinStickAim = true` 时，
  右摇杆超过死区就把角色转向瞄准方向（`LookStick`），移动方向独立。

### 6.2 第三人称的必备细节

- **转向速度上限**（`turnSpeedDegPerSec`，默认 720°/s）：瞬间转身会让
  动画看起来抽搐。别设为无限。
- **蹲伏要改碰撞体高度**：只降速不改 `controller.height`，穿低矮通道会穿模。
  本模板已在 `UpdateCrouch()` 里同步高度，并在起身前用 `SphereCast`
  检查头顶（`BlockedFromStanding()`），头顶有物体就拒绝起身。
- **Animator 用局部速度做 8 向 blendspace**：模板会喂 `LocalMoveX/LocalMoveZ`
  （世界速度转到角色空间），直接接 2D 混合树即可，不需要额外脚本。

### 6.3 相机怎么配

- **第三人称**：Cinemachine 3 `CinemachineCamera`（Unity 6 已无 VirtualCamera），
  Brain 挂 Main Camera；Follow = 玩家，Aim 建议 `Pan Tilt` 或 `Hard Look At`；
  肩部偏移用 Follow Offset。把相机 Transform 拖给控制器的 `cameraReference`。
- **俯视角**：正交相机 + `Cinemachine PositionComposer` 跟随；
  鼠标点地交互用 `Physics.Raycast` 打地面层。
- **双摇杆**：相机固定不跟朝向，只跟位置；避免相机随角色旋转，
  否则"世界方向输入"会和画面对不上。

### 6.4 验收（三种视角通用）

- [ ] 移动方向符合上表（第三人称转视角后按前仍向前，俯视角按上永远向屏幕上方）
- [ ] 冲刺/蹲伏/跳跃参数与 GDD 一致，且都在 Inspector 可调
- [ ] 第三人称转身有过渡、不抽搐；蹲伏能改变碰撞体高度
- [ ] 双摇杆：移动时仍可朝任意方向瞄准
- [ ] 相机不穿墙（近处遮挡时拉近或淡出，见参考文献）
