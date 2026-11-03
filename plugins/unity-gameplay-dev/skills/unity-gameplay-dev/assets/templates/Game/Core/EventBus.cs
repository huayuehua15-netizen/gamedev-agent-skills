// 类型化事件总线：系统间解耦（UI 不直接引用库存、音效不直接引用血量）。
// 定义事件结构：public readonly struct PlayerDiedEvent { public readonly int Cause; ... }
// 订阅：EventBus.Subscribe<PlayerDiedEvent>(OnDied);  OnDestroy 里 Unsubscribe。
// 注意：不要在热路径上滥用；输入和高频物理仍走直接引用。
using System;
using System.Collections.Generic;

namespace {{NS}}
{
    public static class EventBus
    {
        private static readonly Dictionary<Type, Delegate> Handlers = new();

        public static void Subscribe<T>(Action<T> handler)
        {
            if (handler == null)
            {
                return;
            }

            Handlers.TryGetValue(typeof(T), out var existing);
            Handlers[typeof(T)] = Delegate.Combine(existing, handler);
        }

        public static void Unsubscribe<T>(Action<T> handler)
        {
            if (handler == null)
            {
                return;
            }

            if (!Handlers.TryGetValue(typeof(T), out var existing))
            {
                return;
            }

            var result = Delegate.Remove(existing, handler);
            if (result == null)
            {
                Handlers.Remove(typeof(T));
            }
            else
            {
                Handlers[typeof(T)] = result;
            }
        }

        public static void Publish<T>(T evt)
        {
            if (Handlers.TryGetValue(typeof(T), out var existing))
            {
                ((Action<T>)existing)?.Invoke(evt);
            }
        }

        public static void Clear()
        {
            Handlers.Clear();
        }
    }
}
