# 排错对照表（编译 / 运行时 / 输入 / 导航 / UI / 构建）

> 症状 → 原因 → 修法。每条都来自真实高频问题。

## 编译错误

| 症状 | 原因 | 修法 |
|---|---|---|
| CS0246 type not found | 缺 using 或缺程序集引用 | 补 using；asmdef 加包引用（GUID）；脚手架重跑回填 |
| CS0234 'UI' not in UnityEngine | 未引用 UGUI | manifest 加 com.unity.ugui（脚手架自动 2.0.0）；Game.asmdef 引用 2bafac87... |
| CS0103 InputAction 不存在 | 未引用 InputSystem | Game.asmdef 引用 Unity.InputSystem；确认包已导入后重跑脚手架 |
| CS0266 T/UIPanel 转换 | 泛型返回基类 | `return (T)panel;`（约束 where T : UIPanel） |
| CS0506 override 失败 | 基类成员非 virtual | 基类属性/方法加 virtual |
| CS0579 重复定义 | 同名类两份 | 检查复制残留；asmdef 范围重叠；删重复文件 |
| 引用了但还是找不到 | 包导入未完成 / asmdef 未刷新 | 开一次 Unity 解析包；重跑脚手架；read_console 确认 |
| NavMeshAgent 找不到 | 缺 using 或 ai.navigation 包 | using UnityEngine.AI；装 com.unity.ai.navigation |

## 运行时异常

| 症状 | 原因 | 修法 |
|---|---|---|
| NullReferenceException（Awake/Start） | 引用未拖、Awake 顺序 | 缓存引用在 Awake；跨组件在 Start；预制体拖全；空值防御在边界 |
| 事件订阅后泄漏/重复响应 | OnDisable 没退订 | OnEnable 订阅、OnDisable 退订（模板示范） |
| 重启场景后单例多份 | 重复创建 | PersistentSingleton 判重；场景内非持久对象不继承它 |
| 改 SO 数值，停 Play 后还在 | 运行时改了共享 SO | 运行时状态复制进组件；SO 只读 |
| 存档读出来对象没还原 | 只存了引用/id 没查回 | 按 id 查 SO 重建；位置/状态显式恢复 |
| 协程随对象销毁中断 | 协程挂在被销毁对象 | 长流程挂 GameManager 或用异步 |
| timeScale=0 后 UI 不动 | 用了 deltaTime | 全部 unscaledDeltaTime |

## 输入

| 症状 | 修法 |
|---|---|
| 键盘/鼠标完全没反应 | Active Input Handling 不是 Both/New；脚手架写 activeInputHandler=2 后重启 |
| 鼠标视角抖/跳 | Look 用 `<Mouse>/delta`；相机在 LateUpdate；灵敏度单位确认 |
| 手柄无响应 | 设备在 Input Debugger 识别；动作绑定 Gamepad 路径；UI 模块换 InputSystemUIInputModule |
| 菜单时游戏仍在动 | 打开面板时禁用游戏输入；GameManager 切 Paused |
| UI 点不到又收不到游戏输入 | 两个 Input Module 并存；只保留一个 InputSystemUIInputModule |
| 打包后输入失效 | 后台焦点丢失；检查 Application.runInBackground / 焦点处理 |

## 导航 / 动画

| 症状 | 修法 |
|---|---|
| Agent 不动 | 未烘焙 NavMesh；NavMeshSurface/Static 没勾；Agent 不在 NavMesh 上方（检查高度） |
| 敌人原地踏步/脚滑 | 关 Root Motion；Speed 参数跟 Agent.velocity；Blend Tree 阈值匹配 |
| 穿门而过/掉边 | 烘焙半径与 Agent 半径不符；动态门用 NavMeshLink；缺口处挡住 |
| T-pose | Avatar 未建成/动作没引 Avatar；Animator 控制器为空 |
| 攻击没伤害 | 动画事件函数名与组件方法不一致；判定窗口没开；事件在被 Override 的层 |
| 动画事件只在编辑器响 | 事件名在脚本里不存在（含名字空间/签名）；AnimationClip 必须是对应 Avatar 可用 |

## UI / 构建

| 症状 | 修法 |
|---|---|
| UGUI 编译失败 | manifest 缺 com.unity.ugui；asmdef 引用 GUID（脚手架处理） |
| 高分辨率文字糊 | CanvasScaler 参考分辨率；TMP SDF |
| 构建报找不到场景 | Build Settings 未加场景；场景路径拼错 |
| IL2CPP 构建失败 | 装对应平台 Build Support（Linux/Windows IL2CPP）；看构建日志 |
| 首包粉色/缺资源 | 材质/贴图未随构建（Resources/Addressables 配置）；shader 不兼容 URP |
| 构建巨慢/巨大 | 未压缩贴图、未剥离引擎模块、Development 包；正式包关 Development、压缩格式 |
| Linux 包 Deck 启动失败 | 缺 libsteam_api.so 权限；测试 Proton 与原生；音频/显示后端日志 |

## 通用排查动作（MCP）

1. `read_console` 取第一条错误（后面的级联错误先忽略）。
2. 无法判断时 `execute_code` 打印对象状态：组件引用、Transform、NavMesh.SamplePosition、事件订阅数。
3. 编辑器正常、打包异常：差异点通常是 Resources/Addressables、shader、平台设置、Development 宏。
4. 每修一个问题就重新编译验证，不要攒着改一批。
