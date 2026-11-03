# 2D 玩法开发（Unity 6 / URP 2D）

> 3D 那一套（角色控制器、NavMesh、三角面预算）在 2D 里**不适用**。本篇是 2D 的对照说明：
> 凡是与 `02-input-and-fp-controller.md`、`06-ai-navigation.md`、`08-performance.md` 冲突的地方，以本篇为准。

## 0. 先装包（不装就是硬的墙）

Unity 6 的 3D/URP 模板**不含** `com.unity.2d.*`。不装包时 `SpriteRenderer` 能编译，但
`Tilemap`、`PixelPerfectCamera`、`SpriteAtlas`、`2D Animation` 的类直接不存在。

`Packages/manifest.json` 需要（版本按编辑器内置为准，用 Package Manager 装最稳）：

```json
"com.unity.2d.sprite": "1.0.0",
"com.unity.2d.tilemap": "1.0.0",
"com.unity.2d.animation": "10.1.4",
"com.unity.2d.pixel-perfect": "5.0.3",
"com.unity.2d.aseprite": "1.1.6"
```

装完把 2D 模板的 `Sprite (URP)` / `Sprite Unlit` 材质用起来；2D 场景不需要 `Directional Light`。

## 1. Sprite 导入设置（比 3D 贴图严格，错一项就废）

| 项 | 像素风 | 高清 2D |
|---|---|---|
| Texture Type | `Sprite (2D and UI)` | `Sprite (2D and UI)` |
| Filter Mode | **Point (no filter)** | Bilinear |
| Compression | None | Normal Quality |
| Generate Mip Maps | **关** | 关 |
| Wrap Mode | **Clamp** | Clamp |
| Pixels Per Unit | 全项目统一（常用 16/32/100） | 100 |
| Mesh Type | Full Rect | Tight |
| Sprite Mode | Single，或 Multiple + Sprite Editor 切图 | 同左 |

> `Pixels Per Unit` 必须全项目一致。一边 100 一边 16，角色和场景比例会差 6 倍，而且不会有任何报错。
>
> 本仓库的 `unity-blender-mcp` 自带 `AssetPostprocessor.cs` 已针对 2D 加了分支：
> 文件名以 `spr_` 开头、含 `_spr`，或位于 `/Sprites/`、`/Tiles/` 下时，自动按 Sprite 导入
> （Point 过滤、无 Mipmap、Clamp、不压缩）。不满足命名约定就仍按 3D 贴图处理——记得改名或改路径。

## 2. 2D 物理（和 3D 是两套完全独立的模拟）

- 组件是 `Rigidbody2D` / `BoxCollider2D` / `CapsuleCollider2D` / `CircleCollider2D`，
  **不是** 3D 的同名类；`Physics2D` 与 `Physics` 的层碰撞矩阵也是分开的两份。
- 重力在 `Project Settings → Physics 2D → Gravity`（默认 `(0, -9.81)`），不是 3D 的 Physics 设置。
- 查询用 `Physics2D.Raycast` / `OverlapCircle`；3D 的 `Physics.Raycast` 打不到 2D 碰撞体。
- `FixedUpdate` 里改速度；`rb.velocity`（Unity 6 仍可用，新 API 是 `linearVelocity`）。
- **单向平台**：`PlatformEffector2D` + `usedByEffector`，或在角色下落时临时忽略该层碰撞。
- 层矩阵：至少分出 `Player / Ground / OneWayPlatform / Enemy / Trigger` 五层，并在
  `Physics2D` 的碰撞矩阵里显式勾选——2D 项目最常见的"能穿墙"或"跳不上去"都出在这里。

## 3. 2D 角色控制器要点（替代 CharacterController 方案）

3D 模板的 `FirstPersonController` 用 `CharacterController`，2D 用不了。2D 平台跳跃的必备件：

- `Rigidbody2D`（Gravity Scale 按手感调，不要用默认 1）+ `CapsuleCollider2D`。
- **地面检测**：脚底一个空物体加 `Physics2D.OverlapCircle` 检测，不要用 `collision.normal.y > 0.5` 判地面。
- **Coyote Time**（离开平台后 ~0.1s 仍可跳）+ **Jump Buffer**（落地前 ~0.1s 按跳，落地立即起跳）。
  这两个是"手感好不好"的分水岭，缺了会明显觉得"跳得很粘"。
- **可变跳跃高度**：松开跳跃键立即把上升速度乘 0.5（或削减到固定值）。
- 水平移动用 `rb.velocity = new Vector2(dir * speed, rb.velocity.y)`，不要直接改 `transform.position`（会穿墙）。
- 相机跟随用 `Cinemachine 2D` 或简单的 Lerp + `Camera.main.orthographicSize`。

## 4. Tilemap

- `Grid` → `Tilemap`（多层：`Background / Midground / Collision / Foreground`），
  用 `Sorting Layer` + `Order in Layer` 控制前后关系，不要靠 Z 轴。
- `Tile Palette` 里画图；`Rule Tile` 做自动拼接（草地/墙壁自动连边）。
- **从 Tile 生成碰撞**：在 Tilemap 上挂 `TilemapCollider2D` + `CompositeCollider2D` + `Rigidbody2D (Static)`，
  否则每一格都是独立碰撞体，角色会被格子缝卡住。
- 大世界用 `Chunk` 模式（`Tilemap Renderer → Mode: Chunk`），否则每次画图都会重建整张 mesh，很卡。

## 5. 2D 预算（不是三角面！）

2D 的瓶颈**不是三角形**，是 **overdraw（填充率）** 和 **合批打断**。用三角面预算表评判 2D 项目会得出错误结论。

| 指标 | 2D 参考上限 | 说明 |
|---|---|---|
| Overdraw 层数 | 同屏像素平均 ≤ 4 层 | 全屏叠加的半透明层是 2D 最大杀手 |
| Draw Call / Batch | ≤ 200（移动端 ≤ 100） | 主要来自不同 atlas / Sorting Layer 交替 |
| 同屏 Sprite 数 | ≤ 2000（合批良好的话） | 超过就考虑合图 |
| Atlas 张数 | 单场景 ≤ 8 张 2048² | 一张 atlas 一次合批 |
| Tilemap Chunk 重建 | 帧内 ≤ 2ms | 用 Profiler 看 `Tilemap.RebuildChunk` |

- **合批规则**：同 atlas + 同材质 + 同 Sorting Layer + 相邻渲染顺序才能合批。
  所以 `Sorting Layer` 不要滥用，把静态背景、角色、UI 各归一层即可。
- 半透明和粒子是 overdraw 大户；UI 全屏遮罩（黑边淡入）尤其贵。
- 用 Frame Debugger 看 batch 数，用 Profiler 看 `Gfx.WaitForPresent` 判断是不是 GPU 填充率瓶颈。

## 6. 像素完美（像素风必做）

- 装 `com.unity.2d.pixel-perfect`，相机挂 `Pixel Perfect Camera`：
  `Assets Pixels Per Unit` 与 sprite 的 PPU 一致，`Reference Resolution` 设为设计分辨率（如 320×180）。
- **整数倍缩放**：`Pixel Perfect Camera` 勾 `Upscale Render Texture` + `Pixel Snapping`，
  否则非整数倍缩放会出现"像素大小不一"的抖动。
- 相机 `orthographicSize` = `参考高度 / (2 × PPU)`。例：180 / (2 × 16) = 5.625。
- 移动像素风角色时不要把位置 snap 到整像素（会和物理冲突），靠 Pixel Perfect Camera 统一处理。
- 分辨率策略：优先整数倍（1x/2x/3x）+ 上下黑边，不要拉伸到 16:9 非整数倍。

## 7. 2D 动画

- 帧动画：`Sprite` 序列 → `AnimationClip` → `Animator`；或 2D Animation 包做骨骼。
- `Sprite Library` + `Sprite Resolver` 可做换装/换武器，不用拆成多个 Animator。
- 采样帧率按美术帧率走（12/15/24fps），**不要**插值成 60fps 去"更顺滑"——像素风插值只会糊。
- 动画事件（脚步声、攻击判定帧）与 3D 一致，见 `03-interaction-animation.md`。

## 8. 2D 也要跑的验收项

- [ ] 全项目 PPU 一致，无 2 倍/6 倍比例错乱
- [ ] 像素风：Point 过滤、无 Mipmap、整数倍缩放、无像素抖动
- [ ] Physics2D 层碰撞矩阵显式配置，单向平台行为正确
- [ ] Tilemap 碰撞合并成 Composite，无格子缝卡顿
- [ ] Overdraw 与 Batch 数在预算内（用 Frame Debugger 实测，不是估）
- [ ] 键鼠与手柄都能操作（2D 尤其容易漏手柄）
- [ ] 在 1280×800（Deck）与 1920×1080 下 HUD 不遮挡、不出屏
