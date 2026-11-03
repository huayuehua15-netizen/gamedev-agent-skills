# UGUI：HUD、菜单与面板栈

> 目录：1. 基础搭建 → 2. 面板栈规范 → 3. HUD 构成 → 4. 暂停与输入切换 → 5. 适配（分辨率/手柄/Steam Deck）→ 6. 常见问题

## 1. 基础搭建（MCP 流程）

1. 场景建 Canvas：Render Mode=Screen Space - Overlay；UI Scale Mode=Scale With Screen Size，参考分辨率 1920×1080，Match=0.5（宽高均衡）。
2. Canvas 下挂 `CanvasScaler`、`GraphicRaycaster`（默认就有）。
3. 场景唯一 EventSystem：Input System 项目用 `InputSystemUIInputModule`（不是 StandaloneInputModule）。
4. 所有面板放 `Resources/UI/` 或 Addressables 组（见 05 资源加载）；UIManager 负责实例化。
5. 文本用 TextMeshPro（TMP）；脚手架 HUD 用 `UnityEngine.UI.Text`（零额外依赖）。
   **切 TMP 时要注意**：TMP 是独立程序集 `Unity.TextMeshPro`（GUID `6055be8ebefd69e48b49212b09b47b2f`），
   与 UGUI（`2bafac87e7f4b9b418d9448d219b01ab`）**不是同一个**。切过去必须在 `Game.asmdef` 里补这条引用，
   否则报 `CS0246: TMP_Text could not be found`（旧文档曾错误地说"GUID 相同，无需改 asmdef"）。

## 2. 面板栈规范

- 每个面板一个预制体 + 一个继承 `UIPanel` 的脚本：重写 `OnOpen()` / `OnClose()`（**无参数**），
  用 `CanvasGroup.interactable` 管理输入；`HandleBack()` 返回 true 表示该面板自己消费了返回键。
- `UIManager` 维护栈：`Open<T>()` 入栈、`CloseCurrent()` 出栈、`HandleBack()` 统一处理 ESC
  （模板里**没有** `Push<T>(args)` / `Pop()` 这种签名）。`Open<T>()` 对同一面板做了去重，
  重复打开不会把同一个面板压两次导致关不掉。
- 面板只通过参数/事件与系统通信，不直接 Find 玩家组件；如 HUD 血条订阅 `Health.Changed`。
- 面板打开策略：HUD 常驻（不进栈）；菜单/背包/对话/暂停进栈；栈顶下面的面板 `interactable=false`（CanvasGroup 已经做了）。
- 过渡：0.12~0.2s 淡入淡出/缩放，用 unscaled time（暂停时也能动）。

## 3. HUD 构成（第一人称）

- 准星（居中，交互时可变色/扩散）。
- 交互提示（准星下方文本，如「按 E 拾取」）。
- 血量条（Slider，订阅 Health.Changed，受伤方向/红屏反馈）。
- 字幕（对话/广播，底部安全区上方，逐字或整句，见 05）。
- 弹药/资源/任务目标（按 GDD 取舍）。
- 准星与提示在 1920×1080 与 Deck 1280×800 都要居中且不遮挡安全区。

## 4. 暂停与输入切换

- 暂停：`Time.timeScale = 0`；`InputReader` 增加全局开关（UI 打开时禁用游戏输入），菜单输入走 unscaled 或直接事件响应。
- `UIManager` 与 GameManager 联动：面板栈深度>0 时 GameManager 进 Paused，关闭最深菜单回 Playing。
- 鼠标：游戏中锁定（`Cursor.lockState = Locked`、`Cursor.visible = false`）；菜单解锁。
- 手柄：UI 按钮必须支持方向键导航（默认即可），设好每个面板的默认选中按钮（`EventSystem.current.SetSelectedGameObject`）。

## 5. 适配

- 锚点（Anchor）优先：四角信息锚四角，中心信息锚中心；避免靠绝对坐标排版。
- 安全区：刘海/Deck 用 `Screen.safeArea` 对根 RectTransform 做边距（写一个 SafeArea 组件或在 UIManager 处理）。
- 字号/按钮：手柄操作最小可点区域约 48px@1080p；Steam Deck 掌机距离更远，字号 ≥18。
- 多分辨率测试：16:9、16:10（Deck）、21:9，用 Game View 分辨率预设逐一切。

## 6. 常见问题

| 现象 | 修法 |
|---|---|
| 按钮点不到 | 缺 GraphicRaycaster；面板被全屏透明 Image 挡住；CanvasGroup.interactable=false |
| 手柄 UI 不动 | EventSystem 不是 InputSystemUIInputModule；没设默认选中 |
| 暂停时 UI 动画卡死 | 用 Time.unscaledDeltaTime，DOTween 用 SetUpdate(true) |
| 文本模糊 | Canvas 参考分辨率/Scale 模式不对；TMP 用 SDF 不受影响 |
| 切场景 UI 残留 | 常驻 Canvas 放 DontDestroyOnLoad 的 UIManager 下；场景 UI 随场景销毁 |
