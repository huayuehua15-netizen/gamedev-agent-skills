# MCP 玩法开发工作流（Unity 侧）

> 目录：1. 连接与工具发现 → 2. 工具按玩法任务映射（CoplayDev/unity-mcp 47 工具）→ 3. 代码编辑循环 → 4. Play 模式验证 → 5. 跑测试 → 6. 无 MCP 时的降级

## 1. 连接与工具发现

- 每次会话先用场景/控制台类工具确认桥接：`manage_editor`（读状态）、`read_console`（读日志）。桥接面板在 Unity：Window > MCP for Unity，Running 状态才算通。
- 工具名以本会话实际暴露的为准。下表为 CoplayDev/unity-mcp 的真实命名（47 个，分 8 组），官方包 `com.unity.ai.assistant` 按等价能力映射。
- 官方包工具：MCP 没装时，所有命令行路径（Unity batchmode、直接改文件）都能完成同一任务，不要假称调用成功。

## 2. 工具按玩法任务映射

| 玩法任务 | 工具 | 要点 |
|---|---|---|
| 读编辑器状态/版本 | `manage_editor` | 先确认 playmode、管线、目标平台 |
| 控制台排错 | `read_console` | 每步动作后查；编译错误、运行时异常、警告都在这 |
| 建 C# 脚本 | `create_script` | 自动刷新；路径在 Assets/Game 下 |
| 改脚本（首选） | `script_apply_edits` | 方法级锚点编辑（replace_method/anchor 插入），括号平衡有校验 |
| 小改文本 | `apply_text_edits` | 仅用于少量文本；整文件重写不用它 |
| 读/查脚本 | `manage_script`、`find_in_file`、`get_sha` | 改之前先读，确认锚点 |
| 诊断脚本 | `validate_script` | 编译前诊断，返回错误行 |
| 刷新/编译 | `refresh_unity` | 写文件后触发编译；传参可只编译 |
| 任意 C# | `execute_code` | Editor 环境执行：建对象、配组件、批量设置、截图 |
| 场景增删改查 | `manage_scene`、`find_gameobjects` | 打开/保存/新建；按名字/标签/组件查询 |
| 对象/组件 | `manage_gameobject`、`manage_components` | 建 Player、挂 CharacterController/Animator、设属性 |
| 预制体 | `manage_prefabs` | 场景对象存为预制体、实例化预制体 |
| 包管理 | `manage_packages` | 装 inputsystem/ai.navigation/cinemachine/test-framework |
| 动画 | `manage_animation` | 控制 Animator、建 AnimationClip |
| 相机 | `manage_camera` | 含 Cinemachine（注意 Unity 6 是 CinemachineCamera） |
| 灯光/后处理/烘焙 | `manage_graphics` | 光照烘焙、Volume、渲染统计 |
| 物理 | `manage_physics` | Layer 碰撞矩阵、物理材质、关节 |
| UI Toolkit | `manage_ui` | 本技能用 UGUI，走 manage_gameobject；只有 UXML/USS 才用它 |
| 材质 | `manage_material` | 资产管线导入后的材质修复 |
| VFX/Shader | `manage_vfx`、`manage_shader`、`manage_texture` | 粒子、VFX Graph、程序化纹理 |
| ScriptableObject | `manage_scriptable_object` | 建 ItemDefinition/DialogueData 资产 |
| Profiler | `manage_profiler` | 计数器、内存快照、Frame Debugger |
| 构建 | `manage_build` | 切平台、加场景、出包、批量构建 |
| 测试 | `run_tests` / `get_test_job` | 异步起测试，轮询 job_id 拿结果 |
| 文档/反射 | `unity_docs`、`unity_reflect` | 不确定 API 时查；反射真实程序集签名 |
| 菜单/批量 | `execute_menu_item`、`batch_execute` | 执行菜单项；多命令合并减往返 |
| Blender 桥 | `blender_bridge` | 调 Blender MCP（资产修改走 unity-blender-mcp 技能） |

## 3. 代码编辑循环（硬规则）

1. 改之前 `find_in_file` / `manage_script` 读现状；新功能脚本来自模板（`assets/templates/`），不要凭空写。
2. 建脚本 `create_script`，模板内容整文件传入；改动用 `script_apply_edits`：
   - 整个方法重写 → `replace_method`
   - 在某标记后插入 → anchor 类操作
   - 禁止用整文件正则做删除
3. 每次编辑后 `validate_script`；一批改完 `refresh_unity`；`read_console` 必须零 error 才继续。
4. 看到 CS 错误立即修，不要叠加新功能（错误会级联）。
5. 一个 `execute_blender_code` 式代码块/一次 MCP 调用只做一件事；`execute_code` 用于无法用结构化工具表达的场景操作。

## 4. Play 模式验证（手感类功能必须做）

1. 编译绿后，用 `manage_editor` 进入 playmode（或 `execute_menu_item` 执行 Edit/Play）。
2. 用 `execute_code` 模拟输入或直接调方法验证逻辑，例如：
   - 调 `Inventory.Add` 后断言 `CountOf`；
   - 读 `FirstPersonController.CurrentSpeed`、Transform 位置确认移动生效；
   - 强制 `Health.Damage` 后读血条 Slider 值。
3. 截图 Game View 留证：`execute_code` 用 `ScreenCapture.CaptureScreenshot(path)`。
4. 退出 playmode；**playmode 里的改动不会保存**，只验证逻辑，配置改动在 edit 模式做。
5. `read_console` 复查零运行时异常（NullReferenceException 最常见）。

## 5. 测试（run_tests）

- 脚手架生成 `Game.Tests` 程序集（TestAssemblies），EditMode/PlayMode 都能看到。
- 纯逻辑（背包、存档、状态机）写 EditMode；涉及协程/场景生命周期写 PlayMode。
- 流程：`run_tests`（指定 mode/assemblies）→ 返回 job_id → 轮询 `get_test_job` → 看通过数/失败栈。
- 失败的测试先修代码再修测试，禁止通过删断言让它变绿。

## 6. 无 MCP 时的降级

- 文件操作直接落盘（脚手架/模板复制），Unity 检测到文件变化会自动编译；
- 编译验证用 batchmode：`Unity.exe -batchmode -quit -projectPath <path> -logFile log.txt`，日志里搜 `error CS`；
- 跑测试：`Unity.exe -batchmode -runTests -projectPath <path> -testPlatform editmode -testResults results.xml -logFile log.txt`；
- 出包：`-executeMethod` 调 BuildScript，或 `manage_build` 的等价命令行。
- 装包：直接编辑 `Packages/manifest.json`（脚手架就是这么做的），再开 Unity 解析。
