# 架构与代码规范

> 目录：1. 目录结构 → 2. asmdef 与编译边界 → 3. 命名规范 → 4. 组件编排原则 → 5. 数据驱动（ScriptableObject）→ 6. 通信方式选择 → 7. 生命周期与执行顺序

## 1. 目录结构（Assets 下）

```
Assets/
├── Game/                  # 玩法代码（脚手架生成，独立 asmdef）
│   ├── Core/              # 单例、状态机、事件总线、GameManager
│   ├── Input/             # InputReader
│   ├── Player/            # 控制器、视角、玩家生命
│   ├── Interaction/       # 交互接口与实现
│   ├── Systems/           # 背包、存档、对话、对象池、音频
│   ├── AI/                # 敌人 AI、感知
│   └── UI/                # 面板、HUD
├── Game.Tests/            # 测试程序集
├── GameData/              # ScriptableObject 资产（Items/Dialogues...）
├── Art/                   # 美术（资产管线产物，PF_ 预制体）
├── Prefabs/               # 玩法预制体 PF_Player、PF_Enemy、PF_Pickup
├── Scenes/                # Level_01_xxx.unity
├── Settings/              # URP 资产、AudioMixer、InputActions
└── Editor/                # 编辑器脚本（资产管线的 Postprocessor 放这里）
```

## 2. asmdef 与编译边界

- 玩法代码放 `Game.asmdef`（脚手架建，命名空间与目录名一致）。
- 引用 Input System 用 GUID（脚手架从 PackageCache 解析）；包在 asmdef Inspector 里勾选 Unity.InputSystem。
- 测试程序集单独 asmdef（`optionalUnityReferences: TestAssemblies`，引用 Game）。
- 好处：改一行代码只重编译玩法程序集；边界清晰后不会让 UI 直接拿到 AI 类型。
- 不要把所有代码丢进默认 Assembly-CSharp：大项目编译慢、没有依赖边界、模板无法复用。

## 3. 命名规范

| 类型 | 规范 | 示例 |
|---|---|---|
| 类/脚本 | PascalCase，文件名=主类名 | `FirstPersonController.cs` |
| 字段（可序列化） | 私有 + SerializeField，camelCase | `[SerializeField] float walkSpeed` |
| 常量 | PascalCase | `public const int MaxSlots = 24` |
| 预制体 | PF_类型_名 | `PF_Player`, `PF_Enemy_Grunt` |
| 场景 | Level_序号_名 | `Level_01_Apartment` |
| SO 资产 | Item_名、Dialogue_名 | `Item_KeyCard_01` |
| 层 | 玩家 Player、敌人 Enemy、交互物 Interactable、地面 Ground | Project Settings/Tags&Layers 里建 |
| 输入动作 | 动词 PascalCase | Move/Look/Jump/Interact |

## 4. 组件编排原则（Composition over inheritance）

- 一个 MonoBehaviour 一个职责：`FirstPersonController` 只管移动，`PlayerLook` 只管视角，`Interactor` 只管交互。
- 跨系统通信优先**序列化引用**（Inspector 拖），系统间广播才用 EventBus。
- 进程内唯一服务（GameManager、AudioManager、UIManager）继承 `PersistentSingleton`；场景内的服务（Inventory、Health）用普通组件，由预制体持有引用。
- 不要在 Awake 里访问其他组件的运行时结果：Awake 只做自己的初始化，跨组件在 Start 或事件回调里拿。
- 禁止在 Update 里 FindObjectOfType/GetComponent：缓存到字段，或在 Awake 取。

## 5. 数据驱动（ScriptableObject）

- 物品（ItemDefinition）、对话（DialogueData）、敌人属性、武器参数、关卡配置都用 SO；策划/GDD 改数值不动代码。
- SO 是资产（`[CreateAssetMenu]`），放 GameData/，用 `manage_scriptable_object` 或菜单创建。
- 运行时不要改 SO 字段（SO 被所有实例共享，退出 Play 模式可能残留）：运行时状态复制进 MonoBehaviour 容器（如 Inventory 的 ItemStack）。
- 存档只存 SO 的 id（如 itemId），不存整个 SO；读档时按 id 查资产（Resources/Addressables）。

## 6. 通信方式选择（按耦合度从低到高）

| 场景 | 方式 | 例子 |
|---|---|---|
| 父子/同预制体 | 序列化引用 + 直接调用 | Player 持 InputReader |
| 一对多广播 | C# event | Health.Changed → HUD/音效/动画 |
| 跨系统、无所有权 | EventBus | 拾取 → 背包事件 → 音效/任务 |
| 全局流程 | GameManager 状态机 | Playing/Paused/Loading |
| 异步/帧延时 | 协程或 async | 音乐淡变、UI 动画 |
| 禁止 | 静态字段到处 new 单例、SendMessage/BroadcastMessage | 难追踪、易泄漏 |

- 订阅事件必须在 OnDestroy/OnDisable 退订（模板都已示范）。
- 暂停时 `Time.timeScale = 0`；UI 动画/音乐淡变用 `Time.unscaledDeltaTime`。

## 7. 生命周期与执行顺序

- 常见坑：`NullReferenceException` 因为 Awake 顺序不确定。规则：
  - Awake：取自己身上的组件、初始化容器；
  - Start：依赖其他对象的初始化（此时所有 Awake 已完成）；
  - OnEnable 订阅，OnDisable 退订；
  - 需要严格顺序时用 `[DefaultExecutionOrder]` 或在 GameManager 启动流程里显式调用。
- 物理放 FixedUpdate（本套控制器移动在 Update 驱动 CharacterController，是官方建议的角色移动方式；纯 Rigidbody 物理才在 FixedUpdate）。
- 相机逻辑放 LateUpdate，保证玩家移动完再更新相机（PlayerLook 已如此）。
