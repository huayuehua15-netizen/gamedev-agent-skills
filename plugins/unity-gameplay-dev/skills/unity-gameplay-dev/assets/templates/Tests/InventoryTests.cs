using NUnit.Framework;
using UnityEngine;

namespace {{NS}}.Tests
{
    public class InventoryTests
    {
        [Test]
        public void Add_WithinCapacity_NoLeftover()
        {
            var go = new GameObject("inventory");
            var inventory = go.AddComponent<Inventory>();

            int leftover = inventory.Add("coin", 3, 10);

            Assert.AreEqual(0, leftover);
            Assert.AreEqual(3, inventory.CountOf("coin"));
            Object.DestroyImmediate(go);
        }

        [Test]
        public void Add_OverCapacity_ReturnsLeftover()
        {
            var go = new GameObject("inventory");
            var inventory = go.AddComponent<Inventory>();

            int leftover = inventory.Add("coin", 30, 1);

            Assert.AreEqual(6, leftover); // 容量 24 格，每格 1 个
            Assert.AreEqual(24, inventory.CountOf("coin"));
            Object.DestroyImmediate(go);
        }

        [Test]
        public void Remove_InsufficientCount_FailsAndKeepsItems()
        {
            var go = new GameObject("inventory");
            var inventory = go.AddComponent<Inventory>();
            inventory.Add("coin", 2, 10);

            bool removed = inventory.Remove("coin", 5);

            Assert.IsFalse(removed);
            Assert.AreEqual(2, inventory.CountOf("coin"));
            Object.DestroyImmediate(go);
        }
    }
}
