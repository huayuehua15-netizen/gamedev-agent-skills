---
name: aaa-game-gdd
description: "3A 级 3D 游戏开发文档（GDD）设计与审校技能：把模糊的游戏想法转化为可直接交付开发、达到 Steam 上架标准、对标 3A 大作的完整文档体系。覆盖游戏愿景与 Pitch、美术圣经、场景与关卡描述、主线玩法与系统数值、剧情叙事与台词脚本、交互与 UI/UX、角色设定、物品/道具建模规格、动画与帧动画规格、音频设计、技术架构与性能预算、QA 与 Steam 上架验收。当用户要写游戏策划案、GDD、游戏设计文档、场景/关卡/玩法/台词/交互/建模/动画规格、美术需求单，或需要审校游戏文档是否达到可开发、可上架、对标 3A 的质量时使用。支持 Unity/Unreal/Godot，附带一键脚手架脚本生成整套文档树。 English: AAA-grade game design document (GDD) authoring and review for Steam-ready games. Covers vision/pitch, art bible, level specs, gameplay systems and numbers, narrative and dialogue, UI/UX, character/prop/animation/audio specs, tech performance budgets, and QA plus Steam release checklists. Supports Unity, Unreal and Godot. Use when writing or reviewing a GDD, game design doc, level/scene spec, art brief, or release QA checklist."
---

# 3A 级游戏开发文档（GDD）技能

> **路径约定**：本文件中所有 `scripts/`、`references/`、`assets/` 都**相对于本 SKILL.md 所在目录**。
> 执行 `python scripts/new_gdd.py` 前先定位该目录（Cursor/Codex 由 `install.ps1` 装到 `<项目>/skills/game-dev/aaa-game-gdd/`）。
> 不确定就先找到本 SKILL.md 的绝对路径，再用绝对路径调用脚本；在项目根直接敲相对路径会 file-not-found。

## 这个技能做什么

把「我有个游戏想法」变成「团队照着文档直接开发就能做出可上架 Steam、对标 3A 的游戏」的整套文档。核心交付物是一套结构化、量化、可验收的中文 Markdown 文档（GDD），而不是一份泛泛而谈的策划案。

产出的每份文档必须满足三条铁律：

1. **可开发**：开发拿到文档不需要追问「具体做什么、做多大、什么标准」。一切可量化的东西都写死数值（面数、帧数、时长、分辨率、频率、延迟、触发条件）。
2. **可验收**：每份资产、每个系统、每个场景都有 Definition of Done（完成定义）检查表，做完能逐条打勾判定。
3. **一致性**：所有文档共享同一份愿景支柱、美术圣经、命名规范、性能预算；文档之间互相引用编号，禁止互相矛盾。

## 文档地图（references 按需读取）

**不要一次性读完所有参考文档**。先按下表确定用户要做哪类文档，再只读对应那一篇。每篇 reference 的结构都是：解决什么问题 → 何时写 → 章节结构 → 每章怎么写（含量化标准）→ 好坏示例 → 完成定义检查表。

| 文档 | 何时读这篇 reference | 对应模板（assets/templates） |
|---|---|---|
| 00 文档体系总览 | 新项目立项、需要确定文档清单与阶段计划 | `README.md` |
| 01 愿景与 Pitch | 项目刚有想法、需要一页纸讲清游戏、对外路演 | `01-vision-pitch.md` |
| 02 美术圣经 | 定美术风格、统一团队审美、出美术需求 | `02-art-bible.md` |
| 03 场景与关卡 | 写场景描述、关卡流程、动线、遭遇、环境叙事 | `03-scene-level.md`、`scene-sheet.md`、`level-sheet.md` |
| 04 玩法系统 | 设计核心循环、战斗、养成、经济、数值表 | `04-gameplay-systems.md`、`system-sheet.md` |
| 05 剧情与台词 | 写故事大纲、章节 beat、分支、台词脚本、配音 | `05-narrative-dialogue.md`、`dialogue-sheet.md` |
| 06 交互与 UI/UX | 定操作、交互矩阵、游戏手感、HUD、菜单、可访问性 | `06-interaction-uiux.md` |
| 07 角色规格 | 主角/敌人/NPC 的设定、外观、动作集、AI、数值 | `07-character-spec.md`、`character-sheet.md` |
| 08 物品建模规格 | 道具/武器/环境资产的建模、贴图、LOD、命名交付 | `08-prop-modeling.md`、`prop-sheet.md` |
| 09 动画规格 | 3D 骨骼动画、动画状态机、过场、2D 帧动画 | `09-animation-spec.md`、`animation-sheet.md` |
| 10 音频设计 | 音乐、音效、配音、动态音乐、总线响度 | `10-audio-spec.md` |
| 11 技术与性能 | 引擎选型、渲染管线、帧率/内存/包体预算、平台 | `11-tech-performance.md` |
| 12 3A 质量与 Steam 验收 | 阶段门禁、QA 计划、Steam 商店与上架、3A 对标评分 | `12-steam-qa-checklist.md` |

## 工作流程

### 流程 A：新项目（从想法到完整文档体系）

1. **澄清最小必要信息**（一次性向用户提问，不超过 4 个问题）：游戏类型与核心玩法一句话、引擎（Unity/Unreal/Godot/未定）、平台与目标帧率（PC 60fps？Steam Deck？）、美术风格倾向。问完即可开工，不要为了信息齐全反复追问，未知项在文档中显式标 `【待确认】`。
2. **跑脚手架**：`python scripts/new_gdd.py init --name "游戏名" --out <输出目录> --engine <第一步确认的引擎>`，生成整套 GDD 文档树。**`--engine` 要用第 1 步问出来的答案，不要一律填 unity**——它会真正决定文档里的轴向、碰撞命名、导航与数据资产口径。
3. **按阶段顺序写文档**（见下「阶段门禁」），每篇先读对应 reference 再填对应模板。顺序：01 愿景 → 02 美术圣经 + 11 技术预算 → 04 核心玩法 → 07/08/09/06 规格类 → 03/05 内容类 → 12 验收。
4. **每个场景/角色/道具/动画/对话/系统** 用 `scripts/new_gdd.py sheet` 生成独立单页文档，放在 GDD 对应子目录，核心文档只放索引表，不把几百个资产堆进一个文件。
5. **过质量门禁**：每个阶段结束用 `12-steam-qa-checklist.md` 的门禁表逐项检查，不通过不进入下一阶段。

### 流程 B：单份文档（用户只需要某一类文档）

确认对象与用途 → 读对应 reference → 复制对应模板填写 → 用该篇末尾的「完成定义」自检 → 交付。用户只说「帮我写个场景」时，先问场景名/在流程中的位置/核心事件（一次问完），然后直接产出完整 scene-sheet，不要只给空模板。**填写前先读 `assets/examples/SC_01_外科楼二层走廊_示例.md`——这是场景单页的完整度样板，所有单页都要达到这个颗粒度（每一项都有具体数字、编号、可派工内容）。**

### 流程 C：审校已有文档/想法

按 `12-steam-qa-checklist.md` 的「3A 十维评分表」逐维打分（1-10 分，附证据），列出阻断上架的硬伤、缺失文档清单、按严重度排序的修改建议。评分必须引用文档原文或缺失项，禁止空泛评价。

### 阶段门禁（Stage Gates）

| 阶段 | 必须完成的文档 | 门禁（不过不进入下一阶段） |
|---|---|---|
| 概念 | 01 愿景、04 核心玩法骨架 | 核心乐趣有可玩纸面/灰盒原型验证；3 条核心支柱全员认可 |
| 垂直切片 | 02、06、11 + 每类至少 1 个样板单页（场景/角色/道具/动画/对话） | 10-15 分钟流程达到最终品质预期；所有核心系统跑通；性能预算达标 |
| 量产 | 全部核心文档 + 全部资产单页 | 每个资产单页可直接派工；产能与里程碑可排期 |
| Alpha | 全部内容 | Feature Complete：可从头通关，无占位系统 |
| Beta | 同上 + 12 验收表 | Content Complete；零 S/A 级 bug；通关全流程×3 配置档 |
| RC/上架 | 12 中 Steam 清单全部打勾 | 商店页、Deck 验证、本地化、分级、存档兼容全部通过 |

## 脚手架脚本

```bash
# 初始化整套 GDD 文档树（在输出目录下建 <游戏名>_GDD/）
python scripts/new_gdd.py init --name "游戏名" --out "D:/MyGame" --engine unity
#   --engine：unity | unreal | godot | agnostic（默认）
#             ★ 这不是装饰：选择后会真正写入该引擎的交换格式/轴向/碰撞命名/导航/数据资产/LOD 口径
#   --genre：可选，游戏类型描述，会写入愿景文档
#   --dimension：3d（默认）| 2d（额外建 sprites/ tilesets/ 子目录）

# 为单个对象生成单页文档（自动放入对应子目录）
python scripts/new_gdd.py sheet --type scene --name "废弃医院" --out "D:/MyGame/游戏名_GDD"
#   --type：scene | level | character | prop | animation | dialogue | system | sprite | tileset
#   --subtype：character 用 player/enemy/npc（CH/EN/NPC）；prop 用 item/weapon（PR/WP）
#   例：sheet --type character --subtype enemy --name "缝合者" → characters/EN_01_缝合者.md
#   例：sheet --type sprite --name "HeroIdle" → sprites/SPR_01_HeroIdle.md
```

`init` 还支持 `--dimension 2d`：额外创建 `sprites/`、`tilesets/` 子目录（2D 项目用）。

脚本自动替换 `{{GAME_NAME}}`、`{{DATE}}`、`{{ENGINE}}` 占位符。若脚本不可用，手动从 `assets/templates/` 复制模板。

## 通用写作规范

- **文档头**：每份文档开头固定写：文档编号、版本号、状态（草稿/评审中/已锁定）、最后更新日期、负责人、关联文档编号。资产单页还需写引擎内资源命名（如 `SM_Prop_HospitalWheelchair_01`）。
- **量化优先**：禁止「手感好」「画面精美」「敌人很强」这类无法验收的描述。要写「按下攻击到判定生效 8 帧（0.13s@60fps）」「敌人 HP 120、玩家满强化 DPS 45，预期战斗时长 35-45s」。
- **不确定就标**：未知数值写 `【待确认：原因/负责人/期限】`，禁止编造数字后假装确定；行业经验值可直接采用并在文档中标注「行业默认值，首测后调」。
- **图文要求**：场景、关卡、UI 必须配布局示意（ASCII 平面图、Mermaid 流程/状态图、或引用概念图编号）；状态机、对话树、菜单流程用 Mermaid 画出；参数与清单用表格承载。
- **每篇必须有 DoD**：文末附完成定义检查表（可打勾的 `- [ ]`），这是交付验收的唯一依据。
- **语言**：中文正文；专有名词、引擎 API、资源命名保留英文；台词脚本同时预留英文/其他语种字段。
- **改文档走版本**：锁定后的文档修改要在文末变更记录中记版本、日期、改了什么。

## 交付要求

- 交付物是落在用户项目目录的 Markdown 文件（脚手架目录 + 填好的文档），不是聊天里的大纲。
- 每次交付后提示用户：下一步该写哪份文档、哪些 `【待确认】` 需要他决策。
- 文档质量以「一个新加入的外包美术/程序，只读对应单页就能独立做出合格资产」为检验标准。
