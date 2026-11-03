# 3D 素材库大全与选型授权

> 目录：1. 选型优先级 → 2. 国际库（CC0/混合/市场）→ 3. 国内库 → 4. 角色与动画 → 5. AI 生成 → 6. 格式与转换坑 → 7. 授权规则与台账 → 8. 搜索关键词

## 1. 选型优先级

按"游戏可用度 + 授权风险 + 风格统一性"排序，搜索也按这个顺序，能在前面解决就不往后找：

1. **MCP 内置**（Sketchfab / Poly Haven，Blender 内直接搜直接下）
2. **CC0 游戏向素材站**（Kenney、Quaternius、KayKit、Poly Haven）——风格统一、面数合理、带图集
3. **CC0/CC-BY 聚合库**（Poly Pizza、OpenGameArt、PolygonalMind）
4. **大市场免费区**（CGTrader、TurboSquid、Fab、BlenderKit）——质量参差，必须审计
5. **国内库**（3d66、模之屋、爱给网等）——授权和格式坑最多，逐件核
6. **AI 生成**（Rodin/Hunyuan/Tripo/Meshy）
7. **自建**

## 2. 国际素材库

| 站点 | 授权 | 格式 | 特点与注意 |
|---|---|---|---|
| **Poly Haven**（polyhaven.com） | CC0 | glTF/Blend/FBX，1K-16K | 写实模型 500+、PBR 贴图 850+、HDRI 990+；无需密钥 API；MCP 内置 |
| **Sketchfab**（sketchfab.com） | 混合（CC0/CC-BY/CC-BY-NC…），逐件标注 | glTF/FBX/OBJ/USDZ | 数百万模型，量最大；**必须筛 Downloadable + 授权**，避开 NC；MCP 内置，下载给 `target_size` |
| **Kenney**（kenney.nl） | CC0 | GLB/glTF/OBJ/FBX | 最优先：数百包、6 万+ 资源，风格统一、共享贴图、面数合理，无需账号 |
| **Quaternius**（quaternius.com） | CC0 | glTF/GLB/FBX | 风格化低模角色/怪物/载具，**多带绑定和动画**，有通用动画库 |
| **KayKit**（kaylousberg.itch.io） | CC0 | glTF/FBX/OBJ | 地下城、角色、地形、Bits 道具包，骨骼规范带动作 |
| **Poly Pizza**（poly.pizza） | 主要 CC-BY，部分 CC0 | GLB/GLTF/OBJ | 1 万+ 低模（Google Poly 存档），CC-BY 需在鸣谢署名 |
| **OpenGameArt**（opengameart.org） | CC0/CC-BY/CC-BY-SA/OGA-BY/GPL | Blend/OBJ/FBX/glTF | 开源游戏美术；**GPL 有传染风险**，商业项目优先筛 CC0 |
| **Fab**（fab.com，原 Quixel Megascans/Unreal 商城） | Fab Standard，部分 CC | Unity/glTF/Unreal | 1500+ 免费 Megascans 写实扫描；授权允许入游戏但不可单独转售 |
| **CGTrader**（cgtrader.com/free-3d-models） | 免版税（15 万+ 免费） | FBX/OBJ/Blend/glTF/MAX | 数量大、质量参差；必须审计面数/贴图；不可转售原始文件 |
| **TurboSquid**（turbosquid.com） | 免版税 | MAX/FBX/OBJ/Blend/glTF | 写实硬表面/载具强；免费区允许入游戏，玩家不可提取源文件 |
| **BlenderKit**（blenderkit.com，插件内置） | 免版税 / CC0 | 原生 Blend | 1.7 万+ 免费模型、2.6 万材质、2000 HDRI，拖入即用；免费账号 |
| **Smithsonian / NASA**（3d.si.edu / science.nasa.gov） | CC0 / 政府作品 | OBJ/glTF/FBX | 博物馆扫描、航天器；扫描模型面数高，需减面 |
| **Unity Asset Store**（assetstore.unity） | Unity 资产 EULA | Unity 包/FBX | 可入游戏，**不可二次分发/转售**；导入后用本管线清洗 |

## 3. 国内素材库（逐件核授权，默认不信任"免费"标签）

| 站点 | 内容 | 格式坑 | 授权注意 |
|---|---|---|---|
| **3D溜溜网 3d66**（3d66.com） | 建筑/室内/人物/道具，中文检索最顺手 | 大量是 **.max（3ds Max），Blender 原生打不开**；只有部分提供 FBX/OBJ/Blend | 免费件多用于学习/会员体系，**商用游戏授权不明确**，付费件看具体协议；上线项目需留存授权凭证，拿不准就换源 |
| **模之屋**（aplaybox.com） | 手办/二次元角色/MMD/VRChat | PMX/VRM/FBX | 很多 CC-BY-NC 或禁止再配布，**商用基本不可用**，仅作参考或买授权 |
| **爱给网**（aigei.com） | 模型/特效/音效，免费额度 | FBX/OBJ 居多 | 免费与付费授权分开，商用看会员等级和页面标注 |
| **CG模型网 / 游美网 / 3Dsky** | 建筑、室内、家具 | 3dsky 以 `.skp`(SketchUp) 为主 | 同 3d66，多为效果图生态，游戏商用授权弱 |
| **3D Warehouse**（3dwarehouse.sketchup.com） | 海量建筑/家具 | `.skp`（需 SketchUp 或 Blender 导入插件） | 授权混杂，质量两极，只做白盒/占位优先 |

**`.max` 打不开怎么办**：Blender 无官方 `.max` 导入；路径只有：①找该素材的 FBX/OBJ 版本（3d66 详情页常提供）；②用 3ds Max / 试用版导出 FBX；③在线转换（涉及上传版权与商业敏感，不推荐）。搜不到可转换版本就直接换源，不要卡在这里。

## 4. 角色与动画（不要自己绑骨骼）

- **Mixamo**（mixamo.com，Adobe，免费）：上传网格自动绑定（标准 65 骨，无指手套角色选 25 骨）；数千全身动作（走跑跳攻击受击），直接下 FBX；是独立游戏动作主力。
- **Quaternius Universal Base Characters + Modular Outfits**：CC0 人形角色 + 62 个可换装部件 + 通用动画库。
- **PolygonalMind 100 Avatars**：200+ 已绑骨 CC0 低模人群。
- Mixamo 动作进 Unity 用 Humanoid 重定向（见 06）；同一套骨架的角色可共用全部动作。
- 商业注意：Mixamo 资源免费用于游戏，**但不要把原始文件作为素材包再分发**。

## 5. AI 生成（MCP 已内置的优先）

- Blender MCP：Hyper3D Rodin（`generate_hyper3d_model_via_text`/`via_images`）、Hunyuan3D；异步提交→轮询→导入；免费额度每日有限。
- Unity MCP：`generate_model`（Tripo/Meshy），可直接进项目；`generate_image`（贴图/原画）、`generate_audio`（音效）。
- **适用边界**：只生成**单个、轮廓明确、不带复杂可动结构**的物体（道具、容器、武器、雕像）。不生成整场景、地形、角色面部、大量零件组合。
- AI 件普遍问题：拓扑乱、UV 差、面数虚高、贴图烘焙糊；**必须过审计、重拓扑/减面、重展 UV**（见 05），验收标准与下载素材相同。

## 6. 格式与转换坑

| 格式 | 用途 | 坑 |
|---|---|---|
| `.fbx` | Blender↔Unity 主格式 | 轴向/比例/材质（FBX 不存节点材质，只存贴图引用）；动画/骨骼用它 |
| `.glb/.gltf` | 实时渲染、Web、Unreal 支持好 | Unity 原生不导入 glTF（需 glTFast 包），进 Unity 一律先转 FBX |
| `.obj` | 静态网格、最通用 | 无骨骼/动画、无 PBR 材质结构，贴图靠 MTL 常丢 |
| `.blend` | Blender 原生 | Unity 不直接用；导出 FBX |
| `.max` | 3ds Max | **Blender 打不开**，见上 |
| `.skp` | SketchUp | 需插件/转换，面是反的情况多 |
| `.c4d/.ma/.mb` | 其它 DCC | 一般用对应软件另存 FBX，Blender 直读不稳 |

## 7. 授权规则（上线前必须合规）

- **CC0**：公共领域，可商用、可改、无需署名，首选。
- **CC-BY**：可商用，必须在游戏鸣谢/版权页署名（记作者名 + 链接）。
- **CC-BY-SA**：衍生作品要同协议开源，**商业闭源游戏不建议**。
- **CC-BY-NC**：禁止商用，Steam 卖钱的游戏一律不可用。
- **免版税（Royalty-Free）**：可入游戏但不得单独转售源文件，玩家不可提取（打包进构建一般满足）。
- 市场/会员素材（含 3d66、Unity Asset Store）：保存购买页/授权页截图与订单。
- **台账**：每个非 CC0 资产登记 `assets/asset-ledger.csv`（名称、来源 URL、作者、授权、署名要求、用途、下载日期）。发版前过一遍，有未登记/存疑件一律替换。

## 8. 搜索关键词技巧

- 英文关键词命中率更高（国际库）：`prop`、`game ready`、`low poly`、`pbr`、`rigged`、`animated`、`modular`、加 `cc0`、`free download`。
- 国内库用中文：`游戏 道具 低模`、`PBR 次世代`、`带动画 绑定`，并显式筛选"FBX/OBJ 格式"。
- Sketchfab 搜索固定叠加：`Downloadable` 开 + License 选 CC0/CC-BY + 按面数/标签筛。
- 找不到一件，先拆词：不要搜"破旧医院走廊轮椅"，拆成 `wheelchair` / `hospital bed` / `gurney` 分别找。
- 同场景批量资产优先整包（Kenney/Quaternius 的 pack），比东拼西凑更容易保证风格统一。
