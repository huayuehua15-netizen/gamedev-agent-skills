// 物品定义（ScriptableObject，数据驱动）：在 Assets/GameData/Items 下建资产。
// 背包容器：固定容量、堆叠、增删事件；存档时序列化为 ItemStack 数组。
using System;
using System.Collections.Generic;
using UnityEngine;

namespace {{NS}}
{
    [CreateAssetMenu(fileName = "Item_", menuName = "Game/Item Definition")]
    public class ItemDefinition : ScriptableObject
    {
        [SerializeField] private string itemId;
        [SerializeField] private string displayName;
        [TextArea] [SerializeField] private string description;
        [SerializeField] private Sprite icon;
        [SerializeField] private int maxStack = 1;
        [SerializeField] private bool discardable = true;

        public string ItemId => itemId;
        public string DisplayName => displayName;
        public string Description => description;
        public Sprite Icon => icon;
        public int MaxStack => maxStack;
        public bool Discardable => discardable;
    }

    [Serializable]
    public class ItemStack
    {
        public string ItemId;
        public int Count;

        public ItemStack(string itemId, int count)
        {
            ItemId = itemId;
            Count = count;
        }
    }

    public class Inventory : MonoBehaviour
    {
        [SerializeField] private int capacity = 24;

        private readonly List<ItemStack> _slots = new();

        public IReadOnlyList<ItemStack> Slots => _slots;
        public int Capacity => capacity;

        public event Action Changed;
        public event Action<string> ItemAdded;

        public int CountOf(string itemId)
        {
            int total = 0;
            foreach (var slot in _slots)
            {
                if (slot.ItemId == itemId)
                {
                    total += slot.Count;
                }
            }

            return total;
        }

        /// <summary>添加物品；返回实际未能装入的数量（0 表示全装下）。</summary>
        public int Add(string itemId, int count, int maxStack = 1)
        {
            if (string.IsNullOrEmpty(itemId) || count <= 0)
            {
                return count;
            }

            int remaining = count;
            foreach (var slot in _slots)
            {
                if (slot.ItemId != itemId || slot.Count >= maxStack)
                {
                    continue;
                }

                int space = maxStack - slot.Count;
                int moved = Mathf.Min(space, remaining);
                slot.Count += moved;
                remaining -= moved;
                if (remaining == 0)
                {
                    break;
                }
            }

            while (remaining > 0 && _slots.Count < capacity)
            {
                int moved = Mathf.Min(maxStack, remaining);
                _slots.Add(new ItemStack(itemId, moved));
                remaining -= moved;
            }

            if (remaining != count)
            {
                Changed?.Invoke();
                ItemAdded?.Invoke(itemId);
            }

            return remaining;
        }

        public bool Remove(string itemId, int count)
        {
            if (CountOf(itemId) < count)
            {
                return false;
            }

            int remaining = count;
            for (int i = _slots.Count - 1; i >= 0 && remaining > 0; i--)
            {
                var slot = _slots[i];
                if (slot.ItemId != itemId)
                {
                    continue;
                }

                int moved = Mathf.Min(slot.Count, remaining);
                slot.Count -= moved;
                remaining -= moved;
                if (slot.Count <= 0)
                {
                    _slots.RemoveAt(i);
                }
            }

            Changed?.Invoke();
            return true;
        }

        public void Clear()
        {
            _slots.Clear();
            Changed?.Invoke();
        }

        public List<ItemStack> Snapshot()
        {
            return new List<ItemStack>(_slots);
        }

        public void Restore(IEnumerable<ItemStack> slots)
        {
            _slots.Clear();
            if (slots != null)
            {
                _slots.AddRange(slots);
            }

            Changed?.Invoke();
        }
    }
}
