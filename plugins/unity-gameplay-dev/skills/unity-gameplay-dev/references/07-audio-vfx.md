# 音频与 VFX

> 目录：1. AudioMixer 分组 → 2. AudioManager 用法 → 3. 音效资产规范 → 4. 音乐与暂停 → 5. 粒子/VFX 选型 → 6. 常见问题

## 1. AudioMixer 分组（Settings/MX_Main.mixer）

```
Master
├── Music   （背景音乐、环境长音）
└── Sfx     （交互/战斗/UI；可再分 Player/Enemy/Env/UI）
```

- Exposed Parameters：`MusicVolume`、`SfxVolume`（0~1 滑块值，内部转 dB：`dB = 20*log10(v)`，v=0 时钳到 -80dB）。
- 选项菜单调这两个参数并存档（SaveSystem）；Master 不做静音外的其它逻辑。

## 2. AudioManager 用法

- 双音乐源做淡变（CrossFade 1.5~2s）；16 个音效源组成池（模板已实现），避免每声效 Instantiate。
- **实际方法签名以 `AudioManager.cs` 为准**（模板里没有 `SfxGroup` 枚举）：
  - 2D 音效（UI/拾取）：`PlaySfx(clip, volume, pitchVariance)`；
  - 3D 音效（脚步/门/敌人）：`PlaySfxAtPoint(clip, position, volume)`。
- ⚠️ `AudioSource` 的 3D 衰减 Unity 默认是 **1m~500m**，模板**没有**改这两个值。要"近 3m / 远 25m"必须自己设
  `minDistance`/`maxDistance`，并把 `spatialBlend = 1f`，否则 3D 音效听起来像全场同响。
- 循环音（环境/机器）：单独起源，可淡入淡出。
- 动画音效走动画事件（Footstep、AttackSwing、Impact），与动画帧对齐（见 03）。

## 3. 音效资产规范

- 命名：`MX_`（音乐）、`AMB_`（环境）、`SFX_类别_名_序号`（如 `SFX_Weapon_PistolShot_01`）。
- 格式：短音效 WAV（避免循环点失真）或 Vorbis（语音/音乐）；音乐流式加载（Load Type=Streaming）。
- 同一声事件准备 3~6 个变体随机播放，避免重复感；音量在源内归一，混合靠 Mixer。
- 素材授权登记（资产管线的台账）；CC0：Freesound（逐个看协议）、Kenney audio、OpenGameArt。

## 4. 音乐与暂停

- 暂停时音乐可继续但降低音量（-6dB）或保持（GDD 定）；UI 音效不受 timeScale 影响（AudioSource 忽略 timeScale，天然成立）。
- 淡变用协程，读 `Time.unscaledDeltaTime`，暂停菜单里也能淡。
- 切场景：GameManager 加载流程中换曲，淡出新曲淡入；不要在 Awake 里播。

## 5. 粒子 / VFX 选型

| 需求 | 方案 | 要点 |
|---|---|---|
| 命中火花、枪口闪光、烟雾、简单爆炸 | Built-in Particle System（Shuriken） | 成本低、资料多；命名 `VFX_` |
| 大量同屏/ GPU 粒子、复杂光效 | VFX Graph（URP/HDRP 支持） | 与 Shuriken 不混用同一效果 |
| 枪烟/血雾/环境尘 | 粒子 + 少量透明材质 | Overdraw 杀手，控制数量与尺寸 |
| 屏幕反馈（受击红屏/命中标记） | UGUI/后处理 Volume | 比贴粒子便宜 |
| 光柱/体积光 | URP Volume + 光锥模型 | 移动端谨慎 |

- 特效必须有**对象池/自动停止**：粒子 Play 完 Stop 回池（见 05），不要在场景里堆积。
- 命中特效生成点 = 动画事件判定点/碰撞点，朝向 = 命中法线。
- 每发子弹/每刀的特效数量写进 GDD 性能预算（见 08）。

## 6. 常见问题

| 现象 | 修法 |
|---|---|
| 音效偶尔丢失 | 音频源池耗尽；增大池数量或缩短音效 |
| 3D 音没方位感 | AudioListener 在主相机；Spatial Blend=1；检查距离/音量衰减 |
| 暂停后音乐也停 | 淡变用 unscaledDeltaTime；音乐源不要被 timeScale 控制（Audio 本身不受影响，检查协程） |
| 特效拖帧 | 粒子数过高、透明 Overdraw、每发新建；上池、减粒子、限屏上数量 |
| 打包后没声 | 音频加载方式/平台；音频 Listener 被切场景销毁（随 DontDestroy 的相机） |
