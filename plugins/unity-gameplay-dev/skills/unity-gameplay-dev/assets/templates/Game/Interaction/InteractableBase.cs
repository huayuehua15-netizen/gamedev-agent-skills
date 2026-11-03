// 可交互物接口 + 抽象基类。
// 实现示例：门、拾取物、NPC 对话、开关。交互层只依赖接口，不依赖具体类型。
using UnityEngine;

namespace {{NS}}
{
    public interface IInteractable
    {
        string PromptText { get; }
        void Interact(GameObject interactor);
        void SetHighlight(bool highlighted);
    }

    public abstract class InteractableBase : MonoBehaviour, IInteractable
    {
        [SerializeField] private string promptText = "交互";

        public virtual string PromptText => promptText;

        public abstract void Interact(GameObject interactor);

        public virtual void SetHighlight(bool highlighted)
        {
            // 用物体层描边/材质高亮时在这里实现；保持空也合法
        }
    }
}
