// 简单拾取物示例：玩家进入交互范围后准星交互，拾取进 Inventory 并自毁。
// 演示 IInteractable 的标准写法；门/开关照此模式扩展。
using UnityEngine;

namespace {{NS}}
{
    public class PickupItem : InteractableBase
    {
        [SerializeField] private string itemId;
        [SerializeField] private int amount = 1;
        [SerializeField] private int maxStack = 1;
        [SerializeField] private float rotateSpeed = 45f;

        public override string PromptText => $"拾取 {itemId}";

        private void Update()
        {
            transform.Rotate(Vector3.up, rotateSpeed * Time.deltaTime, Space.World);
        }

        public override void Interact(GameObject interactor)
        {
            var inventory = interactor.GetComponentInChildren<Inventory>()
                            ?? interactor.GetComponent<Inventory>();
            if (inventory == null)
            {
                return;
            }

            int leftover = inventory.Add(itemId, amount, maxStack);
            if (leftover == 0)
            {
                Destroy(gameObject);
            }
        }
    }
}
