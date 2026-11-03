# 敌人 AI 与 NavMesh 导航

> 目录：1. 烘焙 NavMesh → 2. 敌人预制体 → 3. 状态机与调参 → 4. 感知（视锥）→ 5. 攻击与动画事件 → 6. 扩展状态/Boss → 7. 验收

## 1. 烘焙 NavMesh

- 装包 `com.unity.ai.navigation`（Unity 6 导航包）；静态场景物体勾选 Navigation Static。
- 打开 Navigation 窗口：Agent Radius 0.5、Height 2.0、Max Slope 45°、Step Height 0.4（与玩家一致）。
- 地面/可行走区域 Area=Walkable；墙/障碍不勾；缺口处用 NavMeshLink 做跳跃/翻越。
- 改了场景几何后必须重新 Bake（`manage_graphics` 或菜单 AI/Navigation）；运行时动态关卡用 NavMeshSurface 局部烘焙。
- 多层（楼层/平台）：NavMeshSurface 分区，或用 Area + 链接；验收时画出 NavMesh 可视化（蓝色区域连续、无穿墙）。

## 2. 敌人预制体（PF_Enemy_Grunt）

```
PF_Enemy (Layer: Enemy)
├── 模型（带动画，Animator：Avatar=Humanoid，Root Motion=关）
├── Eye（视锥起点，眼睛高度 1.6m）
├── [CapsuleCollider]（高 1.8 半径 0.3）
├── [NavMeshAgent]（半径 0.3、高 1.8、speed 3.2、acceleration 20、stoppingDistance 1.6）
├── [EnemyPerception]
├── [EnemyAI]
└── [Health]
```

- 巡逻点：场景放 PatrolPath 空物体组（Transform 数组），Gizmos 画线；Agent 按序 Goto。
- Agent 与角色：Root Motion 关闭，位移由 Agent 驱动；Animator 的 Speed 由 Agent.velocity.magnitude 驱动。

## 3. 状态机与调参（数值来自 GDD，下列为行业默认）

| 状态 | 进入条件 | 行为 | 关键参数 |
|---|---|---|---|
| Patrol | 默认/丢失目标超过 loseTime | 巡逻点间走，速度 1.5 | 巡逻等待 1~3s |
| Chase | 感知到目标 | 转向追击，速度 3.2 | 追击视野保持；离开 loseRange 计时 5s |
| Attack | 与目标距离 ≤ stoppingDistance | 停下，面向目标，间隔攻击 | 攻击间隔 1.6s，伤害 10，判定距离 1.8 |
| Dead | Health.Died | 停 Agent、播死亡、销毁/尸体 | 尸体停留 5s |

- 转向：NavMeshAgent.angularSpeed 默认 120°/s；攻击前需要正面对准（点积 >0.9）才出手。
- 防堆叠：多个敌人时 Agent.obstacleAvoidanceType=GoodQuality；或用简单的阵型/冷却错峰。

## 4. 感知（EnemyPerception）

- 视锥：距离 sightRange（默认 12m）、半 FOV 60°（总 120°）、loseRange（16m）、扫描间隔 0.15s。
- 视线遮挡：RayCast 从 Eye 到目标，命中层含墙（sightBlockers）则视为没看见。
- 事件：`TargetSpotted(Transform)` / `TargetLost()`；丢失用 hysteresis（看见距离短、丢失距离长），避免边界反复横跳。
- 额外感知（按需扩展）：听觉（噪声事件）、近距离 360° 兜底（玩家贴脸必发现）。

## 5. 攻击与动画事件

- 攻击动画加 `NotifyAttackPerformed` 事件（GDD 定帧，如挥下第 10 帧）；回调里做一次：
  - 距离 ≤ attackRange 且角度在前方 ±30° → 目标 Health.Damage(damage)；
  - 判定窗口结束（第二个事件）关闭，避免一次攻击多次伤害。
- 受击：Health.Damage 或 Hit Trigger 播受击，攻击被打断的规则按 GDD（硬直/霸体）。
- 死亡：IsDead 触发，isStopped=true，死亡动画结束后 Destroy/对象池回收。

## 6. 扩展状态 / Boss

- 新状态（如 Investigate 调查最后看到位置、Strafe 绕圈、Flee）：继承/扩展 StateMachine 状态类，实现 Enter/Update/Exit；转换条件在 EnemyAI 里集中写。
- Boss：多阶段（血量阈值切状态与技能）、技能选择器（冷却+距离+权重）、多目标/召唤；参数全部 SO 化（EnemyDefinition），数值与 GDD Boss 单页一致。
- 避免每帧 GetComponent/Find：目标缓存；感知扫描间隔化（0.15s）。

## 7. 验收

- [ ] 巡逻沿路径循环，不卡墙角、不抖动；NavMesh 连续
- [ ] 进视野发现、隔墙不发现、超出丢失距离计时后放弃
- [ ] 追击不绕远路、不互相卡死；停下距离准确
- [ ] 攻击只在判定帧造成一次伤害；背对玩家不出手
- [ ] 死亡停得干净（无继续攻击、无悬空碰撞）
- [ ] 20 个同屏敌人 Profiler 无明显 AI 尖峰（见 08）
