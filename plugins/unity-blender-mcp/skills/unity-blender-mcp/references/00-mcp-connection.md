# MCP 连接、工具发现与安全

> 目录：1. MCP 架构 → 2. 工具发现（必做）→ 3. 标准能力对照表 → 4. 连接排查 → 5. 无 MCP 时的命令行退化 → 6. 安全铁律

## 1. MCP 架构

- **Blender MCP**：Blender 内装插件（如 `ahujasid/blender-mcp`，3D 视图侧栏 N 面板 BlenderMCP 标签），点 Connect 后在本地起 socket 服务，MCP 客户端把工具暴露给 AI。
- **Unity MCP**：Unity 包（编辑器内桥接）+ 本地 MCP 服务端两段。社区常用 `CoplayDev/unity-mcp`（fork 众多，如 kafka2306 版本）；Unity 官方包为 `com.unity.ai.assistant`（AI > Unity MCP Server 面板显示 Running）。
- 两个软件之间**不直接通信**，文件通过磁盘中转：约定 Unity 项目内的 `Assets/Imports/<资产名>/` 为暂存目录，Blender 导出的 FBX 放这里，Unity 刷新后导入。

## 2. 工具发现（每次会话第一步，禁止跳过）

1. 列出当前会话实际可用的 MCP 工具（不同实现命名不同，例如执行代码有的叫 `execute_blender_code`，有的叫 `execute_code`）。
2. 按下表把实际工具名映射到标准能力；**以实际工具的参数说明为准**，不要凭记忆传参。
3. 若没有任何 Blender/Unity 工具：先不要假设，检查客户端 MCP 配置是否加载、软件是否开启、桥接是否 Running；仍无则用第 5 节命令行退化。

## 3. 标准能力对照表

### Blender（ahujasid/blender-mcp 常见工具名，其它实现可能是短名）

| 能力 | 常见工具名 | 关键参数/返回 |
|---|---|---|
| 场景总览 | `get_scene_info` | 无参；返回对象/材质/灯光/相机 JSON |
| 单个对象信息 | `get_object_info` | `object_name`；变换、材质、网格数据 |
| 视口截图 | `get_viewport_screenshot` | `max_size`（默认 800）；返回 PNG，用于验证 |
| 执行 Python | `execute_blender_code`（或 `execute_code`） | `code`；在 Blender 内执行任意 bpy，约 180s 超时 |
| Poly Haven | `get_polyhaven_status` / `search_polyhaven_assets` / `download_polyhaven_asset` | `asset_type=hdris/textures/models/all`、`resolution=1k/2k/4k` |
| Sketchfab | `search_sketchfab_models` / `get_sketchfab_model_preview` / `download_sketchfab_model` | `query, categories, count, downloadable=True`；下载必须给 `target_size`（米，按尺寸归一化） |
| AI 生成（Rodin） | `generate_hyper3d_model_via_text` / `poll_rodin_job_status` / `import_generated_asset` | 异步：提交→轮询→导入；`bbox_condition=[长,宽,高]` |
| AI 生成（Hunyuan3D） | `generate_hunyuan3d_model` / `poll_hunyuan_job_status` / `import_generated_asset_hunyuan` | 同上 |

### Unity（CoplayDev/unity-mcp 常见工具名）

| 能力 | 常见工具名 |
|---|---|
| 编辑器状态/设置 | `manage_editor`、`refresh_unity` |
| 控制台 | `read_console`（读/清） |
| 场景 CRUD | `manage_scene` |
| 游戏对象 | `manage_gameobject`、`find_gameobjects` |
| 组件 | `manage_components` |
| 资产操作 | `manage_asset`、`manage_prefabs`、`manage_packages`、`manage_material`、`manage_texture` |
| 脚本 | `create_script`、`apply_text_edits`、`script_apply_edits`、`validate_script`、`execute_code`（编辑器内执行 C#） |
| 菜单/构建 | `execute_menu_item`、`manage_build` |
| 渲染/物理/动画 | `manage_graphics`、`manage_physics`、`manage_animation`、`manage_vfx`、`manage_camera` |
| 导入与生成 | `import_model_file`（本地 FBX/glTF）、`import_model`（Sketchfab）、`generate_model`（Tripo/Meshy）、`generate_image`、`generate_audio` |
| 测试/性能 | `run_tests`、`get_test_job`、`manage_profiler` |
| 文档 | `unity_docs`（官方文档）、`unity_reflect`（反射真实 API） |
| 批量 | `batch_execute`（多命令合并，减少往返） |

官方 `com.unity.ai.assistant` 的工具集相近但命名与分组不同，以工具实际描述为准。

## 4. 连接排查

| 现象 | 排查 |
|---|---|
| 找不到 Blender 工具 | 客户端 MCP 配置未加载；Blender 插件未装/未点 Connect；重启后第一条命令偶发失败，重试一次 |
| `Timeout waiting for Blender response` | 单块代码执行超过约 180s；拆小步骤，先存盘 |
| 找不到 Unity 工具 | Unity 包未安装/桥接未 Running；AI > Unity MCP Server 面板看绿灯；直连需用户在弹窗批准 |
| Unity 操作无响应 | 编辑器在编译/播放模式/弹窗阻塞；先 `read_console` 看是否有编译错误 |
| 工具参数不确定 | 读工具 schema；Unity 侧用 `unity_docs`/`unity_reflect` 查真实 API，禁止猜参数 |

## 5. 无 MCP 时的命令行退化

- **Blender（后台批处理，无头）**：
  ```powershell
  # 审计
  & "D:\Blender\blender.exe" --background --python scripts/blender_asset_audit.py -- "C:\path\asset.fbx"
  # 清洗+导出（脚本参数见 01）
  & "D:\Blender\blender.exe" --background --python scripts/blender_prep_unity.py -- "C:\in\asset.fbx" "C:\out\SM_asset.fbx"
  ```
  找不到 blender.exe 时常见路径：`C:\Program Files\Blender Foundation\Blender X.X\blender.exe`、Steam 目录、用户自定义盘。
- **Unity（batchmode）**：
  ```powershell
  & "C:\Program Files\Unity\Hub\Editor\<版本>\Editor\Unity.exe" -batchmode -quit -projectPath "项目路径" -executeMethod <Editor类.方法> -logFile -
  ```
  批量导入设置优先用本技能 `AssetPostprocessor.cs`，资产一进项目即自动处理，无需保持连接。

## 6. 安全铁律

1. 改动用户现有场景前先另存（Blender `save_as_mainfile`、Unity `manage_scene` 保存副本）。
2. 所有外来素材先在独立 Blender 场景和 Unity `Assets/Imports/` 处理，验收后再移动。
3. 单块代码自包含：自带 `import bpy`；按名字重新选取对象；不假设上一块的变量还在。
4. 每次只做一类操作并立即验证（截图/控制台/层级查询），失败两次换方法。
5. 删除、批量改名、覆盖导出前先列出受影响对象清单；不覆盖用户原件。
6. 操作过程产出的中间文件放暂存区，任务结束时向用户说明哪些可删。
