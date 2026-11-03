# 构建与发布（Steam / Steam Deck）

> 目录：1. 构建设置 → 2. 命令行/CI 构建 → 3. 跑测试门禁 → 4. Steam 上架技术清单 → 5. Steam Deck 适配 → 6. 版本与存档兼容

## 1. Build Settings

- Platform：Windows x86_64（Steam 主战场）；Deck 走同一 Linux 原生包（Linux 64），先用 Proton 兜底验证。
- Scenes In Build：按启动顺序（Boot/主菜单 → Level_01 → ...），加载场景用名字或索引常量。
- Player Settings：
  - Company Name / Product Name / Version（语义化，如 1.0.0）；
  - Scripting Backend=IL2CPP、Api Compatibility Level=.NET Standard 2.1（或 2.0 视插件）；
  - 勾选 Fullscreen/窗口模式、分辨率对话框；图标全套；Splash 按授权。
- URP：质量设置（URP Assets）高/中/低三档，Deck 单独。
- Development Build 仅内部用；正式包关 Profiler、Script Debugging。

## 2. 命令行/CI 构建（MCP manage_build 等价）

```bash
Unity.exe -batchmode -quit -projectPath <proj> \
  -executeMethod Game.EditorBuildScripts.BuildWindows \
  -logFile build.log
```

- Editor 脚本放 Game.Editor 或 Assets/Editor：BuildPlayerOptions 设场景、locationPathName、options、target；Development/AutoconnectProfiler 用开关参数控制。
- Linux 包：`BuildTarget.StandaloneLinux64`；包内包含 Data、GameAssembly（IL2CPP）、.so。
- 输出目录：`Builds/Windows/`、`Builds/Linux/`，每次构建带子版本号文件夹。

## 3. 构建前测试门禁（必过）

- `run_tests`：EditMode 全绿；PlayMode 关键流程（新建存档→移动→拾取→战斗→存档读档）绿。
- 命令行：`-runTests -testPlatform editmode -testResults results.xml`（PlayMode 同理）。
- 出包冒烟：构建完成后启动一次（或 -automated 冒烟脚本），确认无首场景崩溃、无缺资产粉色。
- 禁止：Console 有任何 error 时出包；warning 要清零或记录白名单。

## 4. Steam 技术清单（参见 GDD 技能的 12 验收表）

- Steamworks：下载 SDK，游戏接入 `steam_api64.dll`/`libsteam_api.so`（或 Steamworks.NET 包）；AppID 测试用 480。
- 成就/云存档：云存档目录对准 Application.persistentDataPath；Steam Cloud 路径配置。
- 商店素材：胶囊图、截图、预告片、横幅（尺寸按 Steamworks 文档，GDD 技能清单里有）。
- Depot/分支：默认分支 + beta；构建上传 SteamPipe（脚本化）。
- 本地化：系统语言检测；至少中英；字体覆盖所用字符集。
- 手柄：Steam Input 启用；键鼠/手柄全流程可玩（见 04）。
- 隐私/分级：隐私政策（如收集数据）、内容分级问卷（IARC/ESRB/PEGI）。

## 5. Steam Deck 适配

- 分辨率 1280×800（16:10），UI 安全区与字号（见 04）。
- 性能：画质档目标 40~60fps（可锁 40 + 可变刷新）；Profiler 实测（见 08）。
- 手柄：右摇杆视角、A 交互、B 返回、Start 菜单、触控板可选；死区与灵敏度菜单可调。
- 文字输入（命名/控制台）：接 Steam Deck 虚拟键盘（Steam Input）。
- 验证：Steam Deck 兼容性测试走官方验证（Verified/Playable）；Linux 原生包测启动、音频、云存档。

## 6. 版本与存档兼容

- SaveData.version 每改结构 +1，迁移链保留；新版必须能读旧 N 个版本（Beta 起所有公开版本）。
- 字段只加不删（旧字段保留忽略）；枚举追加在末尾；不要重排 [Serializable] 字段顺序导致 JsonUtility 错位（JsonUtility 按名字序列化，安全）。
- 发布前：用上一版本存档在新版本读档冒烟一次（准备存档样本库）。
- 构建号写进菜单/启动日志（Application.version），便于玩家报 bug。
