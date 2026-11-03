// UI 管理器：面板注册、打开/关闭、栈式返回（ESC 逐层关闭）。
// 挂在 UI 根 Canvas 上，面板预制体在 Inspector 数组里登记（按类型名字查找）。
// 打开独占面板时自动关闭当前面板；HUD 这类常驻面板不进栈，用 ShowHud 显式控制。
using System;
using System.Collections.Generic;
using UnityEngine;

namespace {{NS}}
{
    public class UIManager : PersistentSingleton<UIManager>
    {
        [SerializeField] private UIPanel[] registeredPanels;
        [SerializeField] private UIPanel hudPanel;

        private readonly Stack<UIPanel> _stack = new Stack<UIPanel>();
        private readonly Dictionary<Type, UIPanel> _panelMap = new Dictionary<Type, UIPanel>();

        protected override void Awake()
        {
            base.Awake();
            foreach (var panel in registeredPanels)
            {
                if (panel != null)
                {
                    _panelMap[panel.GetType()] = panel;
                    panel.gameObject.SetActive(false);
                }
            }
        }

        private void OnEnable()
        {
            EventBus.Subscribe<InteractionPromptEvent>(OnPrompt);
        }

        private void OnDisable()
        {
            EventBus.Unsubscribe<InteractionPromptEvent>(OnPrompt);
        }

        public T Open<T>() where T : UIPanel
        {
            if (!_panelMap.TryGetValue(typeof(T), out var panel))
            {
                Debug.LogWarning($"[UIManager] 未注册面板: {typeof(T).Name}");
                return null;
            }

            // 已经打开的直接返回，不要重复入栈。
            // 否则连续 Open<T>() 会推入同一个面板两次，返回键永远关不掉它。
            if (_stack.Count > 0 && _stack.Peek() == panel)
            {
                return (T)panel;
            }

            // 栈里已有该面板（深层重复打开）：先把它从栈中移除，避免重复引用
            if (_stack.Contains(panel))
            {
                var tmp = new Stack<UIPanel>();
                while (_stack.Count > 0)
                {
                    var p = _stack.Pop();
                    if (p != panel)
                    {
                        tmp.Push(p);
                    }
                }
                while (tmp.Count > 0)
                {
                    _stack.Push(tmp.Pop());
                }
                panel.Close();
            }

            if (_stack.Count > 0)
            {
                _stack.Peek().Close();
            }

            panel.Open();
            _stack.Push(panel);
            return (T)panel;
        }

        public void CloseCurrent()
        {
            if (_stack.Count == 0)
            {
                return;
            }

            var current = _stack.Pop();
            current.Close();
            if (_stack.Count > 0)
            {
                _stack.Peek().Open();
            }
        }

        public void HandleBack()
        {
            if (_stack.Count == 0)
            {
                return;
            }

            if (_stack.Peek().HandleBack())
            {
                return;
            }

            CloseCurrent();
        }

        public void ShowHud(bool show)
        {
            if (hudPanel == null)
            {
                return;
            }

            if (show)
            {
                hudPanel.Open();
            }
            else
            {
                hudPanel.Close();
            }
        }

        // 交互提示由 HUD 面板实现；这里只做转发，不直接引用具体 HUD 组件
        private void OnPrompt(InteractionPromptEvent evt)
        {
            if (hudPanel is HUDController hud)
            {
                hud.SetPrompt(evt.PromptText);
            }
        }
    }
}
