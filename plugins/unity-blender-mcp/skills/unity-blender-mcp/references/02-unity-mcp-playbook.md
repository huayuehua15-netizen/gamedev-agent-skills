# Unity MCP 操作手册

> 目录：1. 通用操作循环 → 2. 导入资产 → 3. 场景/对象/组件 → 4. 材质与贴图 → 5. 模型导入设置 → 6. 碰撞/LOD/Prefab → 7. 角色动画 → 8. 脚本与构建 → 9. 编辑器自动化脚本
> 工具名以会话实际发现的为准（见 00）；下列为 CoplayDev/unity-mcp 常见命名，官方包等价能力按 schema 映射。

## 1. 通用操作循环

1. 动作前 `refresh_unity` 确保磁盘新文件已导入；
2. 每步动作后 `read_console` 查错（编译/导入错误立即暴露）；
3. 用 `find_gameobjects`/`manage_scene` 查询确认改动生效；
4. 多个相关操作用 `batch_execute` 合并，减少往返。

## 2. 导入资产（Blender 导出之后）

- Blender 导出的 FBX 直接落到项目暂存目录：`Assets/Imports/<资产名>/`。
- `import_model_file`：导入磁盘上已存在的 FBX/OBJ/glTF（Blender 出的 FBX 走这里）。
- `import_model`：直接从 Sketchfab 市场拉取；`manage_asset`：导入/创建/移动/删除资产。
- 首次使用把 `assets/unity/Editor/AssetPostprocessor.cs` 放进 `Assets/Editor/`：贴图和模型一进 `Assets/Imports/` 就自动套用标准设置（见第 9 节，门控目录可在文件顶部改）。

## 3. 场景、对象、组件

- 场景：`manage_scene`（新建/打开/保存/列对象）；外来资产先在空场景或专门的 `_ImportCheck.unity` 里验收。
- 对象：`manage_gameobject`（增删改查）、`find_gameobjects`（按名字/标签/层级/组件类型查）。
- 组件：`manage_components`（加/删/改属性）。典型：加 MeshRenderer、MeshCollider（凸）、Rigidbody、Animator、LODGroup。
- 相机：`manage_camera`（含 Cinemachine）；灯光/体积/后处理：`manage_graphics`；物理：`manage_physics`。

## 4. 材质与贴图（URP 为默认，HDRP 见 06）

- 用 `manage_material` 建材质，shader 选 URP/Lit（HDRP 选 HDRP/Lit）。
- URP Lit 关键属性（设置前可用 `unity_reflect` 确认）：
  - `_BaseColor` 基础色；`_BaseMap` 颜色贴图（sRGB）
  - `_Metallic` 金属度；`_Smoothness` 平滑度
  - `_MetallicGlossMap` 金属/平滑遮罩（**R=Metallic，A=Smoothness=1−粗糙度**；Linear）
  - `_BumpMap` / `_BumpScale` 法线；`_OcclusionMap` AO；`_EmissionMap`/`_EmissionColor` 自发光
- 贴图设置由 AssetPostprocessor 按后缀自动完成（`_BC`=sRGB、`_N`=法线、`_M`/`_RMA`=Linear）。
- 出现粉色材质：shader 与管线不匹配或贴图丢失，按 `07-troubleshooting.md` 处理。

## 5. 模型导入设置（FBX 选中后）

Model 页：
- Scale Factor 1（Blender 与 Unity 都是米）；Mesh Compression 视预算；Read/Write 默认关（需要网格合并/布料时才开）。
- Normals：Import；Tangents：Calculate Mikoto/legacy 或让 Blender 切线（导出已开 `use_tspace`）。
- Materials：新 Unity 用 "Import via MaterialDescription"；材质缺失时手动按第 4 节连。
- Animation：非动画角色/道具不勾 Import Animation；带骨骼见第 7 节。

可通过 `execute_code` 用 `ModelImporter`/`TextureImporter` 批量设置（与 Postprocessor 同源，二选一即可）：

```csharp
var path = "Assets/Imports/chair/SM_chair.fbx";
var imp = (ModelImporter)AssetImporter.GetAtPath(path);
imp.globalScale = 1f;
imp.importNormals = ModelImporterNormals.Import;
imp.importTangents = ModelImporterTangents.CalculateMikk;
imp.importAnimation = false;
imp.SaveAndReimport();
```

## 6. 碰撞、LOD、Prefab

- 静态道具：关闭导入器自带网格碰撞，加 Box/Capsule/Mesh Collider（凸）；建筑墙体用复合 BoxCollider。
- 角色：CapsuleCollider + Rigidbody（约束旋转）或 CharacterController。
- LOD：对象加 `LODGroup`，把 Blender 出的 LOD0/1/2 网格分别放入 Renderer 数组，切换阈值常见 0.6/0.3/0.01。
- 验收通过后 `manage_prefabs` 生成 Prefab 到 `Assets/Art/<类别>/Prefabs/`，从暂存场景移除；再删 `Assets/Imports/` 中只用于核对的临时件。

## 7. 角色与动画（Mixamo 管线，详见 06）

- 角色模型 FBX：Animation Type = Humanoid，创建 Avatar，检查骨骼映射（人形 T-pose 站直）。
- 动作文件：同样 Humanoid，引用该 Avatar；动作来自 Mixamo 或 Blender 烘焙。
- `manage_animation` 可建 AnimationClip/控制 Animator；Animator 控制器按 GDD 状态机连 Idle/Move/Attack/Hit/Dead。
- 进 Play 模式前 `read_console` 清错；动作验收：T-pose、脚滑、朝向、根运动（Root Motion）四项。

## 8. 脚本、包与构建

- 写 C#：`create_script` 创建，改动用 `script_apply_edits`（结构化、边界安全），`validate_script` 诊断，`refresh_unity` 编译，`read_console` 查错。
- 装包：`manage_packages`（如 URP 包 `com.unity.render-pipelines.universal`、ProBuilder `com.unity.probuilder`）。
- 构建：`manage_build` 切平台/加场景/出包；出包前跑 `run_tests`（异步，用 `get_test_job` 轮询）。
- 不确定的 API：`unity_docs` 查官方文档、`unity_reflect` 反射真实程序集，禁止凭记忆写 API。

## 9. 编辑器自动化脚本（AssetPostprocessor.cs）

`assets/unity/Editor/AssetPostprocessor.cs` 做三件事：

1. **目录门控**：只处理 `Assets/Imports/` 下的资产（常量在文件顶部可改），不影响项目其它内容。
2. **贴图自动设置**：按文件名后缀判定——`_BC/_D/_Albedo` → sRGB；`_N/_Normal` → Normal map（自动关 sRGB、设法线类型）；`_M/_RMA/_R/_AO/_ORM` → Linear；`_E` → 自发光；`_HDR` → HDR。
3. **模型统一设置**：globalScale=1、导入法线、计算切线、关 Read/Write、静态对象读命名。

安装方式：用 `create_script` 或 `manage_asset` 把文件放到 `Assets/Editor/`（没有 Editor 文件夹就新建），`refresh_unity` 编译。移除时删除该文件即可，项目无其它副作用。
