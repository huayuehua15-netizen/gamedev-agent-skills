// HUD：血条、准星交互提示、（可选）字幕。
// 场景里把玩家 Health 拖到 playerHealth；血条用普通 Slider，交互提示用 Text。
// 想升级 TextMeshPro：把 Text 换成 TMP_Text，逻辑不变。
using UnityEngine;
using UnityEngine.UI;

namespace {{NS}}
{
    public class HUDController : UIPanel
    {
        [SerializeField] private Health playerHealth;
        [SerializeField] private Slider healthBar;
        [SerializeField] private Text promptText;
        [SerializeField] private Text subtitleText;
        [SerializeField] private GameObject crosshair;

        protected override void OnOpen()
        {
            if (playerHealth != null)
            {
                playerHealth.Changed += OnHealthChanged;
                OnHealthChanged(playerHealth.Current, playerHealth.Normalized);
            }

            EventBus.Subscribe<DialogueLineEvent>(OnDialogueLine);
            SetPrompt(string.Empty);
        }

        protected override void OnClose()
        {
            if (playerHealth != null)
            {
                playerHealth.Changed -= OnHealthChanged;
            }

            EventBus.Unsubscribe<DialogueLineEvent>(OnDialogueLine);
        }

        public void SetPrompt(string text)
        {
            if (promptText != null)
            {
                promptText.text = text;
                promptText.gameObject.SetActive(!string.IsNullOrEmpty(text));
            }

            if (crosshair != null)
            {
                crosshair.SetActive(true);
            }
        }

        private void OnHealthChanged(float current, float normalized)
        {
            if (healthBar != null)
            {
                healthBar.normalizedValue = normalized;
            }
        }

        private void OnDialogueLine(DialogueLineEvent evt)
        {
            if (subtitleText != null)
            {
                subtitleText.text = $"[{evt.Speaker}] {evt.Text}";
            }
        }
    }
}
