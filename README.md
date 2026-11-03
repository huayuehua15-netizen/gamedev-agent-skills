# game-dev-skills

面向游戏开发的 AI 技能套件。四个技能，一个仓库，一套可执行的验收门禁。**3D 为主，2D 有专门的落地方案**（见下文「2D 支持边界」）。

> 定位：让 AI 不做蠢事、交付能过检查的东西。
> 它不承诺"AI 能做出好看的模型"——造型方向、美术判断、玩法手感仍然需要人。

## 包含四个技能

| 技能 | 负责 | 明确不负责 |
|---|---|---|
| `aaa-game-gdd` | 把想法写成可派工、可验收的文档体系（12 类文档 + 单页模板 + 脚手架） | 不做美术，不做代码 |
| `unity-blender-mcp` | 素材优先的资产管线：搜索复用 → 审计 → 清洗 → FBX → Unity 导入验收 | 不透支从零建模 |
| `blender-modeling-craft` | 真要自建时的手艺与几何门禁：尺寸、blockout、拓扑、UV、剪影比对 | 不做角色绑定与动画 |
| `unity-gameplay-dev` | GDD 落地为可玩功能：输入、控制器、交互、UI、系统、AI、测试、出包 | 不做资产，不做联机 |

## 2D 支持边界（先说清楚，别误用）

诚实说明现状，免得有人拿去做 2D 项目然后踩坑：

| 环节 | 3D | 2D |
|---|---|---|
| 设计文档（`aaa-game-gdd`） | 完整 | 部分：帧动画规格（09）可直接用；场景/关卡按网格重写 |
| 资产管线（`unity-blender-mcp`） | 完整 | 有限：`AssetPostprocessor.cs` 已加 Sprite 分支（自动按 2D 设置导入）；但素材库仍以 3D 为主 |
| 建模（`blender-modeling-craft`） | 完整 | 不适用：Blender 不做像素画与贴片 |
| 玩法代码（`unity-gameplay-dev`） | 完整 | **有专门文档** `references/11-2d-gameplay.md`：2D 包安装、Sprite 导入、Physics2D、2D 平台跳跃、Tilemap、像素完美、overdraw 预算。C# 模板里与维度无关的部分（事件总线/状态机/背包/存档/UI 栈/音频）可直接复用，控制器与导航需重写 |

脚手架支持 `--dimension 2d`，会额外写入 `com.unity.2d.*` 包；`AssetPostprocessor.cs` 对
`spr_*` / `*_spr` / `/Sprites/` / `/Tiles/` 下的图自动走 Sprite 导入，不会被 3D 贴图规则毁掉。

## 目录结构

```
game-dev-skills/
├── marketplace.json              # ZCode / 自带市场清单
├── .claude-plugin/marketplace.json  # Claude Code 市场清单（build 生成）
├── LICENSE
├── README.md
├── tools/
│   ├── build.py                  # 生成各宿主产物到 dist/
│   └── install.ps1               # 按宿主安装
├── tests/
│   └── test_silhouette_gate.py   # 剪影门禁单元测试
└── plugins/
    ├── aaa-game-gdd/
    │   ├── .zcode-plugin/plugin.json
    │   └── skills/aaa-game-gdd/
    │       ├── SKILL.md
    │       ├── references/
    │       ├── assets/templates/
    │       └── scripts/new_gdd.py
    ├── blender-modeling-craft/
    ├── unity-blender-mcp/
    └── unity-gameplay-dev/
```

每个技能遵循同一套分层：`SKILL.md` 只放边界、铁律和索引；`references/` 按需读取；`scripts/` 是可执行检查；`assets/` 是模板与数据。

## 兼容与安装

技能本体是 `SKILL.md`（Anthropic Agent Skills 格式），外层 `marketplace.json` 只是打包清单。先跑一次生成器，再按宿主安装：

```bash
python tools/build.py          # 产物全部在 dist/
```

| 宿主 | 用哪份产物 | 安装 |
|---|---|---|
| Trae | `dist/skills/` | `powershell tools/install.ps1 -Target trae -Path <技能目录>` |
| Claude Code | 仓库根 `.claude-plugin/` | 推到 Git 后 `/plugin marketplace add <仓库地址>` |
| Cursor | `dist/cursor/` | `install.ps1 -Target cursor -Path <项目>` |
| Codex | `dist/codex/` | `install.ps1 -Target codex -Path <项目>` |
| 上传式（Claude.ai 等） | `dist/upload/*.zip` | 在设置里逐个上传 |
| ZCode | 根目录 `marketplace.json` | 导入插件市场，无需复制 |
| 其他认 SKILL.md 的宿主（含 DSH） | `dist/skills/` | `install.ps1 -Target generic -Path <技能目录>` |

需要说清楚的三件事：

1. **只有 Claude Code 支持真正的“链接安装”**（`/plugin marketplace add <git-url>`）。Cursor 和 Codex 没有远程安装机制，本质是把技能复制进项目再生成一个规则入口。
2. **Cursor / Codex 里脚本不会自动执行**。它们的规则/指令只能告诉模型去读哪个 SKILL.md，Blender 和 Unity 的脚本仍要手动跑。
3. **`unity-blender-mcp` 与 `unity-gameplay-dev` 依赖 MCP**。宿主不支持 MCP 时，这两个技能只剩文档部分可用；`aaa-game-gdd` 只要文件读写就能用。

## 核心：验收门禁

这套仓库里真正有价值的不是提示词，是**能被机器判定的那部分**。

```bash
# `--python-exit-code 1` 不是可选参数！
# Blender 默认把 Python 异常当成功（退出码 0），不加它，脚本崩了/门禁没过，
# CI 和上层 Agent 都会看到"通过"。这是本仓库最重要的一行。

# 1) 拓扑与面数（不合格直接非零退出；三角面已计入修改器）
blender --background --python-exit-code 1 --python scripts/topology_audit.py -- asset.blend --budget-tris 3000 --require-bevel

# 2) 剪影门禁：把"像不像"变成一个数字
blender --background --python-exit-code 1 --python scripts/qa_render.py -- asset.blend \
    --gate --ref-front refs/front.png --ref-side refs/side.png \
    --stage final --outdir out

# 3) Unity 侧：把 unity-blender-mcp 自带的 AssetPostprocessor.cs 放进 Assets/Editor/
#    统一缩放、法线、贴图 sRGB/遮罩通道；2D 图（spr_*/Sprites/Tiles）自动走 Sprite 导入
```

退出码约定（脚本已实现，可直接拿去接 CI）：

| 退出码 | 含义 |
|---|---|
| `0` | 通过 |
| `1` | 审查没通过（超预算 / 剪影不符 / 审计有 warning） |
| `2` | 参数或输入有问题（文件不存在、参数拼错、没有可审计对象） |

门禁的数学逻辑有单元测试，不需要装 Blender：

```bash
python tests/test_silhouette_gate.py
```

判定口径：

- **剪影 IoU**：正交渲染（Workbench 单色 + 透明背景），按包围盒等比归一后计算交集/并集。
- **宽高比单独校验**：避免"拉伸到整帧"掩盖比例错误。
- 阈值：blockout `0.70`、成品 `0.85`；宽高比误差 blockout `10%`、成品 `5%`。
- 不通过就**不许导出**，报告写入 `qa_gate.json`。
- ⚠️ 阈值是可复现的，不是"随便定的"：因为两张 mask 都归一到同一最长边，
  **宽高比误差 5% 时 IoU 必然 ≥0.95**，所以 `final` 档实际上以宽高比为主导；
  IoU 真正在 blockout 档（0.70）才承担"多一条腿/少一条胳膊"的判别力。

## 已知限制（请先读这段）

1. 参考图必须是**正交**的正视图 / 侧视图剪影（透明底或纯色底、无透视、无投影、无渐变背景）。
   带透视的商品照片拿去比 `--stage final` 的 0.85，会因为近大远小必然失败——那不是模型的问题。
2. 剪影只能校验"外轮廓与比例"，校验不了细节、材质和气质。
3. 模型自评一轮基本无效：多数运行环境里 agent 看不到渲染图。用脚本判定，别用"目测通过"。
4. Unity 侧版本口径以 `unity-gameplay-dev` 为准（Unity 6 / 6000.x，新 Input System）。
5. 剪影门禁对**极细长物体**（剑、栏杆，长宽比 >20:1）分数不稳定：230px 归一化后宽度只剩十来个像素，
   一个像素的取整误差就能让 IoU 跳 9%。这类资产请结合人工目检，别只看数字。
6. 2D 不是"3D 换个相机"：物理、导航、预算模型都是另一套，见上文「2D 支持边界」。

## 许可

MIT，见 [LICENSE](LICENSE)。
