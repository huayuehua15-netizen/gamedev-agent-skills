// 游戏流程状态机：Boot → MainMenu → Playing ↔ Paused；加关卡流程时扩展 Loading。
// 暂停由 Time.timeScale 控制；UI 订阅 StateChanged 弹/关菜单。
using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace {{NS}}
{
    public enum GameState
    {
        Boot,
        MainMenu,
        Loading,
        Playing,
        Paused
    }

    public class GameManager : PersistentSingleton<GameManager>
    {
        private readonly StateMachine _fsm = new StateMachine();

        public GameState State { get; private set; } = GameState.Boot;

        public event Action<GameState, GameState> StateChanged;

        protected override void Awake()
        {
            base.Awake();
            _fsm.StateChanged += OnFsmStateChanged;
        }

        private void Start()
        {
            GoToMenu();
        }

        private void Update()
        {
            _fsm.Tick();
        }

        private void OnFsmStateChanged(IState previous, IState current)
        {
            var oldState = State;
            State = current switch
            {
                MenuState => GameState.MainMenu,
                LoadingState => GameState.Loading,
                PlayingState => GameState.Playing,
                PausedState => GameState.Paused,
                _ => State
            };
            StateChanged?.Invoke(oldState, State);
        }

        public void GoToMenu()
        {
            _fsm.Change(new MenuState());
        }

        public void StartGame()
        {
            _fsm.Change(new PlayingState());
        }

        public void LoadSceneThenPlay(string sceneName)
        {
            _fsm.Change(new LoadingState(sceneName, () => _fsm.Change(new PlayingState())));
        }

        public void TogglePause()
        {
            if (State == GameState.Playing)
            {
                _fsm.Change(new PausedState());
            }
            else if (State == GameState.Paused)
            {
                _fsm.Change(new PlayingState());
            }
        }

        public void QuitGame()
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit();
#endif
        }

        // ---------- 状态实现 ----------

        private class MenuState : IState
        {
            public void Enter() { Time.timeScale = 1f; }
            public void Tick() { }
            public void FixedTick() { }
            public void Exit() { }
        }

        private class LoadingState : IState
        {
            private readonly string _scene;
            private readonly Action _onLoaded;
            private AsyncOperation _op;

            public LoadingState(string scene, Action onLoaded)
            {
                _scene = scene;
                _onLoaded = onLoaded;
            }

            public void Enter()
            {
                _op = SceneManager.LoadSceneAsync(_scene);
            }

            public void Tick()
            {
                if (_op != null && _op.isDone)
                {
                    _onLoaded?.Invoke();
                }
            }

            public void FixedTick() { }
            public void Exit() { }
        }

        private class PlayingState : IState
        {
            public void Enter() { Time.timeScale = 1f; }
            public void Tick() { }
            public void FixedTick() { }
            public void Exit() { }
        }

        private class PausedState : IState
        {
            public void Enter() { Time.timeScale = 0f; }
            public void Tick() { }
            public void FixedTick() { }
            public void Exit() { Time.timeScale = 1f; }
        }
    }
}
