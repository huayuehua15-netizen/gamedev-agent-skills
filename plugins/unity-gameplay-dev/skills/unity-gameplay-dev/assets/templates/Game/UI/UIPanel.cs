// UI 面板基类：Show/Hide 走 CanvasGroup，支持栈式导航（ESC 返回上一面板）。
// 每个面板预制体挂一个子类：MainMenuPanel、SettingsPanel、InventoryPanel...
using UnityEngine;
using UnityEngine.UI;

namespace {{NS}}
{
    [RequireComponent(typeof(CanvasGroup))]
    public abstract class UIPanel : MonoBehaviour
    {
        private CanvasGroup _group;

        public bool IsOpen { get; private set; }

        protected virtual void Awake()
        {
            _group = GetComponent<CanvasGroup>();
            SetVisible(false);
        }

        public void Open()
        {
            if (IsOpen)
            {
                return;
            }

            IsOpen = true;
            gameObject.SetActive(true);
            SetVisible(true);
            OnOpen();
        }

        public void Close()
        {
            if (!IsOpen)
            {
                return;
            }

            IsOpen = false;
            OnClose();
            SetVisible(false);
            gameObject.SetActive(false);
        }

        protected virtual void OnOpen() { }
        protected virtual void OnClose() { }

        /// <summary>ESC/返回键：返回 true 表示该面板自行处理了返回（如先关子弹窗）。</summary>
        public virtual bool HandleBack()
        {
            return false;
        }

        private void SetVisible(bool visible)
        {
            if (_group == null)
            {
                _group = GetComponent<CanvasGroup>();
            }

            _group.alpha = visible ? 1f : 0f;
            _group.interactable = visible;
            _group.blocksRaycasts = visible;
        }
    }
}
