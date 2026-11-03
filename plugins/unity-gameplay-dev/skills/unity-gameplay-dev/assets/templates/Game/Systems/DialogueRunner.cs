// 线性对话系统：ScriptableObject 存台词，Runner 负责逐行推进并发事件。
// 字段与 GDD 对话单页对齐（speaker/text/动作/等待时长）；分支对话在此数据结构上扩展 choices。
// UI 订阅 DialogueLineEvent 显示文字，输入层调用 Advance()。
using System;
using System.Collections.Generic;
using UnityEngine;

namespace {{NS}}
{
    [Serializable]
    public class DialogueLine
    {
        public string speaker;
        [TextArea] public string text;
        [Tooltip("说话时触发的动画/表情 key，可空")]
        public string action;
        [Tooltip("自动推进前等待秒数；0 表示等待玩家输入")]
        public float autoDelay;
    }

    [CreateAssetMenu(fileName = "Dialogue_", menuName = "Game/Dialogue")]
    public class DialogueData : ScriptableObject
    {
        [SerializeField] private List<DialogueLine> lines = new();

        public IReadOnlyList<DialogueLine> Lines => lines;
    }

    public class DialogueRunner : MonoBehaviour
    {
        [SerializeField] private InputReader input;

        private DialogueData _data;
        private int _index;

        public bool IsRunning { get; private set; }

        public event Action<DialogueLine> LineStarted;
        public event Action DialogueEnded;

        private void OnEnable()
        {
            if (input != null)
            {
                input.InteractPerformed += Advance;
            }
        }

        private void OnDisable()
        {
            if (input != null)
            {
                input.InteractPerformed -= Advance;
            }
        }

        public void Begin(DialogueData data)
        {
            if (data == null || data.Lines.Count == 0)
            {
                return;
            }

            _data = data;
            _index = 0;
            IsRunning = true;
            ShowCurrent();
        }

        public void Advance()
        {
            if (!IsRunning)
            {
                return;
            }

            _index++;
            if (_index >= _data.Lines.Count)
            {
                End();
            }
            else
            {
                ShowCurrent();
            }
        }

        private void ShowCurrent()
        {
            var line = _data.Lines[_index];
            LineStarted?.Invoke(line);
            EventBus.Publish(new DialogueLineEvent(line.speaker, line.text));
        }

        private void End()
        {
            IsRunning = false;
            DialogueEnded?.Invoke();
        }
    }
}
