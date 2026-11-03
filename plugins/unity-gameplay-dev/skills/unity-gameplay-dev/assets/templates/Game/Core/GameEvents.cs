// 全局事件定义：集中放跨系统事件结构，避免事件类型散落在各处。
// 按系统分块排列；字段尽量用 readonly（不可变）。
namespace {{NS}}
{
    public readonly struct HealthChangedEvent
    {
        public readonly float Normalized;

        public HealthChangedEvent(float normalized)
        {
            Normalized = normalized;
        }
    }

    public readonly struct PlayerDiedEvent
    {
        public readonly bool IsPlayer;

        public PlayerDiedEvent(bool isPlayer)
        {
            IsPlayer = isPlayer;
        }
    }

    public readonly struct ItemChangedEvent
    {
        public readonly string ItemId;
        public readonly int Count;

        public ItemChangedEvent(string itemId, int count)
        {
            ItemId = itemId;
            Count = count;
        }
    }

    public readonly struct InteractionPromptEvent
    {
        public readonly string PromptText; // 为空字符串表示隐藏提示

        public InteractionPromptEvent(string promptText)
        {
            PromptText = promptText;
        }
    }

    public readonly struct DialogueLineEvent
    {
        public readonly string Speaker;
        public readonly string Text;

        public DialogueLineEvent(string speaker, string text)
        {
            Speaker = speaker;
            Text = text;
        }
    }
}
