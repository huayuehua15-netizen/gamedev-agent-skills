# 性能：60fps 定位流程与预算

> 目录：1. 预算（PC/Steam Deck）→ 2. Profiler 定位流程 → 3. 常见热点与修法 → 4. 内存与加载 → 5. 每阶段性能检查点

## 1. 帧预算（目标 60fps ≈ 16.6ms/帧）

| 项 | 中端 PC | Steam Deck |
|---|---|---|
| 渲染（含后处理） | ≤8ms | ≤11ms |
| 游戏逻辑（脚本/AI/物理） | ≤4ms | ≤4ms |
| 物理（PhysX） | ≤2ms | ≤2.5ms |
| GC 触发 | 帧内 0 次（重点） | 0 次 |
| 同屏三角面（全场景，含角色/地形/特效） | 300~500 万 | 100~200 万，资产部分另按建模技能 07 的 1~3M 预算 |
| Draw Calls | <2000（SRP Batcher/GPU Instancing 后） | <1000 |
| 可见敌人 | 30 | 15（再远降频/简化） |

- 30fps 为最低兜底（Deck 画质档）；优先保稳定帧时间，而非最高画质。
- 画质档：低/中/高（分辨率比例、阴影距离/级联、后处理开关、LOD 偏差），Deck 单独一套。

## 2. Profiler 定位流程（MCP manage_profiler）

1. 复现掉帧场景（固定存档点），Development Build + Autoconnect Profiler。
2. 看 CPU Usage Hierarchy：
   - PlayerLoop 按线程拆 Main/Render；找最宽的帧（最坏帧，不看平均）。
   - GC.Alloc 列：帧内有分配就是问题（字符串拼接、GetComponent、LINQ、装箱、闭包）。
3. 渲染：Frame Debugger 看 Draw Call 构成（SRP Batcher 是否 compatible、动态合批/实例化）。
4. 内存：Memory Profiler 快照（前后对比），查泄漏（未释放贴图/音频/池）。
5. 改一处、复测一次，记录前后 ms；不要同时改多个变量。

## 3. 常见热点与修法

| 热点 | 修法 |
|---|---|
| 每帧 GetComponent/Find | 缓存到 Awake 字段；查询结果缓存 |
| GC.Alloc（UI 刷新/字符串） | 文本用 StringBuilder/缓存；事件参数复用；避免 Update 里 new |
| 子弹/特效/敌人频繁 Instantiate | 对象池（见 05） |
| Draw Calls 高 | 材质合批（同 Shader/贴图集）、SRP Batcher、GPU Instancing；静态合批场景 |
| 阴影贵 | 减少实时阴影灯（1 主光）、调级联距离与距离遮蔽；远场景烘焙 |
| 后处理堆叠 | 移动端降配置：关 DOF/Motion Blur/SSAO，Bloom 廉价 |
| 透明 Overdraw | 烟/雾/粒子减数量、减尺寸、近景禁透明堆叠 |
| AI 全频更新 | 感知扫描 0.15~0.3s；远处敌人状态机降频（距离分桶） |
| 物理卡顿 | 减少 MeshCollider（用凸包/复合盒）、控制碰撞体数量、层碰撞矩阵裁剪 |
| 动画开销 | 动画 Culling（不可见不更新）、骨骼 LOD、远景关 Animator |

## 4. 内存与加载

- 贴图：按用途限尺寸（道具 1K、场景 2K、主角 2K）、生成 mipmap、压缩格式（PC BC7、ASTC 移动）。
- 场景分块 + Addressables 异步加载（Loading 状态已在 GameManager 预留）；卸载不用的组。
- 音频：音乐 Streaming，短音效 Decompress on Load/CompressedInMemory 按数量定。
- 切场景 GC：加载完主动 `Resources.UnloadUnusedAssets()` + GC.Collect，避免游戏中卡顿。

## 5. 每阶段性能检查点

- 灰盒：帧率、控制器逻辑开销、物理参数。
- 垂直切片：代表性战斗 20+ 敌人/满特效压测；内存峰值；加载时间。
- Alpha：全关卡 Profiler 走查；Deck 实测。
- Beta：固定画质档跑分；出包前留存 Profiler 截图数据（存档点→ms 表），作为验收依据。
