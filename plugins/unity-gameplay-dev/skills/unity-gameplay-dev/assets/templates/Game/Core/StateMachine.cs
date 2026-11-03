// 轻量状态机：玩家/游戏流程/敌人 AI 通用。
// 状态是普通类（持有上下文），避免每个状态一个 MonoBehaviour 的开销。
using System;

namespace {{NS}}
{
    public interface IState
    {
        void Enter();
        void Tick();      // Update
        void FixedTick(); // FixedUpdate
        void Exit();
    }

    public class StateMachine
    {
        public IState Current { get; private set; }

        public event Action<IState, IState> StateChanged;

        public void Change(IState next)
        {
            if (next == null)
            {
                throw new ArgumentNullException(nameof(next));
            }

            Current?.Exit();
            var previous = Current;
            Current = next;
            Current.Enter();
            StateChanged?.Invoke(previous, Current);
        }

        public void Tick()
        {
            Current?.Tick();
        }

        public void FixedTick()
        {
            Current?.FixedTick();
        }
    }
}
