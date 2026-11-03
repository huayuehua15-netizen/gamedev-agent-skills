# 玩法系统：血量 / 背包 / 对话 / 存档 / 对象池

> 目录：1. Health → 2. Inventory（含 SO 物品）→ 3. DialogueRunner → 4. SaveSystem → 5. ObjectPool → 6. 新系统接入规范

## 1. Health（血量/死亡）

- 事件：`Changed(int current, int max)`、`Died(GameObject owner)`；表现层订阅，逻辑层不写 UI。
- 受伤/治疗只走 `Damage(int)` / `Heal(int)`，做下限钳制；死亡后 `IsDead` 标志防重复触发。
- 玩家死亡走 GameManager 状态（死亡界面/读档）；敌人死亡发事件给掉落/任务/计分。
- 伤害来源：攻击动画事件里做 OverlapSphere（Layer=Enemy），调 Health.Damage，不要让动画脚本直接改血量外的其它状态。
- 无敌帧、护盾、护甲：在 Damage 内做策略判断，不要在调用方各写一套。

## 2. Inventory（背包）

- 数据：`ItemDefinition`（ScriptableObject：id、显示名、图标、最大堆叠、类型）；
  运行时：`ItemStack(itemId, count)`，不直接改 SO。
- 容量固定槽位（默认 24，GDD 决定）；`Add(id, amount, maxStack)` 返回放不下的数量；`Remove` 不足返回 false。
- 事件：`InventoryChanged`，UI 刷新只订阅事件；存取档遍历槽位存 id+count。
- id 全局唯一：`类别_名_序号`，如 `key_keycard_01`、`consumable_medkit`；SO 资产放 `GameData/Items/`。
- 堆叠规则：先填已有同类未满格，再开新格；任务道具 maxStack=1。
- 测试：容量边界、堆叠、移除不足（脚手架 InventoryTests 已覆盖）。

## 3. DialogueRunner（线性对话）

- 数据：`DialogueData`（SO：行列表，每行 speaker、text、可选时长）；分支对话另建 choices 列表（扩展点）。
- 运行：`Play(DialogueData)` → 逐行推进（按 Interact/继续键）→ 结束回调 `OnDialogueEnded`；HUD 字幕订阅事件。
- 对话期间：游戏输入关闭（Interactor 停用、玩家移动可冻结）、时间可保持流动或 timeScale=0（GDD 定）。
- 台词来自 GDD 对话单页；多语言：text 字段用 key，本地化表（i18n）查表，别把中文写死在逻辑里。

## 4. SaveSystem（存档）

- 每个需要持久化的组件实现 `ISaveable { string Id; object Capture(); void Restore(object data); }`；静态注册表在 OnEnable 注册、OnDisable 注销。
- 槽位：`%persistentDataPath%/saves/slot_<n>.json`；先写 `.tmp` 再原子替换（防写一半损坏）。
- `SaveData` 顶层 `version`（当前 1）；读档遇到旧版本走迁移函数链，禁止直接反序列化后假装兼容。
- 只存：场景名、玩家位置/朝向、血量、背包 id+count、剧情标志位/任务状态、已用/已拾取物 id。
- 不存：SO 资产、组件引用、运行时临时对象；读档后按 id 重建（物品查 SO、敌人按场景重刷）。
- 加字段时：version+1、写迁移；发布后绝不能改旧版本的字段语义。

## 5. ObjectPool（对象池）

- 高频生成对象（子弹、命中特效、音效、敌人）走池，禁止 Instantiate/Destroy 每帧调用。
- 预制体挂 `PooledObject`（Release 回池）；`ObjectPool.Prewarm(prefab, n)` 在加载时预热。
- 池对象必须实现重置（位置、速度、状态、材质参数），防止"上次的血/特效"残留。
- 容量按需增长，设上限防泄漏；切场景时清空场景级池，全局池（特效）保留。

## 6. 新系统接入规范（照此顺序，不破坏架构）

1. 数据用 SO 或 SerializeField；状态放组件，不写静态可变字段。
2. 对外发事件，订阅者在 OnDisable 退订。
3. 需要持久化就实现 ISaveable，定义好存档字段与 version。
4. 纯逻辑写 EditMode 测试；表现（动画/音效/UI）通过事件订阅实现。
5. 每个系统对 GDD 单页的 DoD 负责：参数、边界、反馈逐项可验收。
