// 通用生命值组件（玩家/敌人共用）。
// 数值与事件分离：表现层（血条、音效、死亡动画）订阅事件，不写进这里。
using System;
using UnityEngine;

namespace {{NS}}
{
    public class Health : MonoBehaviour
    {
        [SerializeField] private float maxHealth = 100f;
        [SerializeField] private bool invulnerable = false;

        public float Current { get; private set; }
        public float Normalized => maxHealth <= 0f ? 0f : Current / maxHealth;
        public bool IsDead { get; private set; }

        public event Action<float, float> Changed; // (current, normalized)
        public event Action Died;
        public event Action<float> Damaged;

        private void Awake()
        {
            Current = maxHealth;
        }

        private void Start()
        {
            Changed?.Invoke(Current, Normalized);
        }

        public void Damage(float amount)
        {
            if (IsDead || invulnerable || amount <= 0f)
            {
                return;
            }

            Current = Mathf.Max(0f, Current - amount);
            Damaged?.Invoke(amount);
            Changed?.Invoke(Current, Normalized);

            if (Current <= 0f)
            {
                IsDead = true;
                Died?.Invoke();
            }
        }

        public void Heal(float amount)
        {
            if (IsDead || amount <= 0f)
            {
                return;
            }

            Current = Mathf.Min(maxHealth, Current + amount);
            Changed?.Invoke(Current, Normalized);
        }

        public void ResetToFull()
        {
            IsDead = false;
            Current = maxHealth;
            Changed?.Invoke(Current, Normalized);
        }
    }
}
