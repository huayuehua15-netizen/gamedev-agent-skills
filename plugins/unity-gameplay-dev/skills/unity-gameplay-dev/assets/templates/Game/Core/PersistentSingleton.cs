// PersistentSingleton<T> — 跨场景存活的泛型单例。
// 用法：public class AudioManager : PersistentSingleton<AudioManager>
// 注意：只给真正全局的管理器用；场景内服务用普通组件 + 引用。
using UnityEngine;

namespace {{NS}}
{
    public abstract class PersistentSingleton<T> : MonoBehaviour where T : MonoBehaviour
    {
        public static T Instance { get; private set; }

        protected virtual void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }

            Instance = this as T;
            DontDestroyOnLoad(gameObject);
        }

        protected virtual void OnDestroy()
        {
            if (Instance == this)
            {
                Instance = null;
            }
        }
    }
}
