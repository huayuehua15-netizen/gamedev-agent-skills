// 音频管理器：2D 音乐淡入淡出 + 3D 音效池（同一音效高频触发不抢声道）。
// 挂在启动场景的常驻对象上；AudioMixer 暴露 "MusicVolume"、"SfxVolume" 两个 Exposed Parameter。
// 音量设置存 PlayerPrefs（0..1，内部转 dB）；更复杂的方案接 Settings 存档。
using System.Collections;
using UnityEngine;
using UnityEngine.Audio;

namespace {{NS}}
{
    public class AudioManager : PersistentSingleton<AudioManager>
    {
        [SerializeField] private AudioMixer mixer;
        [SerializeField] private AudioSource musicSourceA;
        [SerializeField] private AudioSource musicSourceB;
        [SerializeField] private int sfxPoolSize = 16;

        private AudioSource[] _sfxPool;
        private int _sfxCursor;
        private AudioSource _activeMusic;
        private Coroutine _musicFade;

        private const string MusicKey = "Settings.MusicVolume";
        private const string SfxKey = "Settings.SfxVolume";

        protected override void Awake()
        {
            base.Awake();
            _activeMusic = musicSourceA;
            _sfxPool = new AudioSource[sfxPoolSize];
            for (int i = 0; i < sfxPoolSize; i++)
            {
                var go = new GameObject($"Sfx_{i:D2}");
                go.transform.SetParent(transform);
                _sfxPool[i] = go.AddComponent<AudioSource>();
                _sfxPool[i].playOnAwake = false;
                _sfxPool[i].spatialBlend = 0f;
            }

            ApplyVolumes();
        }

        public void PlaySfx(AudioClip clip, float volume = 1f, float pitchVariance = 0.04f)
        {
            if (clip == null)
            {
                return;
            }

            var source = _sfxPool[_sfxCursor];
            _sfxCursor = (_sfxCursor + 1) % _sfxPool.Length;

            source.clip = clip;
            source.volume = volume;
            source.pitch = 1f + Random.Range(-pitchVariance, pitchVariance);
            source.spatialBlend = 0f;
            source.Play();
        }

        public void PlaySfxAtPoint(AudioClip clip, Vector3 position, float volume = 1f)
        {
            if (clip == null)
            {
                return;
            }

            var source = _sfxPool[_sfxCursor];
            _sfxCursor = (_sfxCursor + 1) % _sfxPool.Length;
            source.clip = clip;
            source.transform.position = position;
            source.volume = volume;
            source.spatialBlend = 1f;
            source.Play();
        }

        public void PlayMusic(AudioClip clip, float fadeSeconds = 1.5f)
        {
            if (clip == null || _activeMusic.clip == clip)
            {
                return;
            }

            if (_musicFade != null)
            {
                StopCoroutine(_musicFade);
            }

            _musicFade = StartCoroutine(CrossFadeMusic(clip, fadeSeconds));
        }

        public void SetMusicVolume(float value01)
        {
            PlayerPrefs.SetFloat(MusicKey, Mathf.Clamp01(value01));
            SetMixerVolume("MusicVolume", value01);
        }

        public void SetSfxVolume(float value01)
        {
            PlayerPrefs.SetFloat(SfxKey, Mathf.Clamp01(value01));
            SetMixerVolume("SfxVolume", value01);
        }

        private void ApplyVolumes()
        {
            SetMixerVolume("MusicVolume", PlayerPrefs.GetFloat(MusicKey, 0.8f));
            SetMixerVolume("SfxVolume", PlayerPrefs.GetFloat(SfxKey, 0.9f));
        }

        private void SetMixerVolume(string parameter, float value01)
        {
            if (mixer == null)
            {
                return;
            }

            float db = value01 <= 0.001f ? -80f : Mathf.Log10(Mathf.Clamp01(value01)) * 20f;
            mixer.SetFloat(parameter, db);
        }

        private IEnumerator CrossFadeMusic(AudioClip nextClip, float seconds)
        {
            var fadingOut = _activeMusic;
            var fadingIn = fadingOut == musicSourceA ? musicSourceB : musicSourceA;
            fadingIn.clip = nextClip;
            fadingIn.volume = 0f;
            fadingIn.Play();

            float elapsed = 0f;
            while (elapsed < seconds)
            {
                elapsed += Time.unscaledDeltaTime;
                float t = Mathf.Clamp01(elapsed / seconds);
                fadingIn.volume = t;
                fadingOut.volume = 1f - t;
                yield return null;
            }

            fadingOut.Stop();
            _activeMusic = fadingIn;
        }
    }
}
