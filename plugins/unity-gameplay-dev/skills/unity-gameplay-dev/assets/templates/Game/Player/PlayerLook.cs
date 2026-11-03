// 第一人称视角：鼠标增量（像素/帧）与手柄右摇杆分别按自己的灵敏度驱动
// 身体偏航（Yaw）+ 相机俯仰（Pitch）。
// 挂在 Player 根对象上，Camera 是根对象下的子物体（如 CameraRig/Main Camera）。
// 暂停/菜单时调 SetLookEnabled(false) 并释放光标。
using UnityEngine;
using UnityEngine.InputSystem;

namespace {{NS}}
{
    public class PlayerLook : MonoBehaviour
    {
        [SerializeField] private Transform cameraTransform;
        [SerializeField] private InputReader input;

        [Header("视角")]
        [SerializeField] private float sensitivity = 0.0012f;      // 鼠标：度/像素
        [SerializeField] private float stickSensitivity = 120f;    // 手柄：度/秒
        [SerializeField] private float pitchMin = -85f;
        [SerializeField] private float pitchMax = 85f;
        [SerializeField] private bool invertY = false;

        private float _pitch;
        private bool _lookEnabled = true;

        private void Awake()
        {
            SetLookEnabled(true);
        }

        // 注意：这里不再订阅 PausePerformed。
        // 暂停的权威处理在 GameManager（Time.timeScale + 输入开关 + 光标），
        // 视角只需要跟随 GameState 变化；两边都抢着改光标会互相打架。
        private void OnEnable()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.StateChanged += OnGameStateChanged;
                OnGameStateChanged(GameManager.Instance.State, GameManager.Instance.State);
            }
        }

        private void OnDisable()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.StateChanged -= OnGameStateChanged;
            }
        }

        private void OnGameStateChanged(GameState previous, GameState current)
        {
            SetLookEnabled(current == GameState.Playing);
        }

        private void LateUpdate()
        {
            if (!_lookEnabled || input == null || cameraTransform == null)
            {
                return;
            }

            Vector2 mouse = input.LookMouse;
            Vector2 stick = input.LookStick;

            // 鼠标是逐帧像素增量（sensitivity 单位为 rad/px，需转成度）；
            // 摇杆是持续输入（度为秒），必须用 deltaTime 换算成同一量纲
            float mouseYaw = mouse.x * sensitivity * Mathf.Rad2Deg;
            float mousePitch = (invertY ? mouse.y : -mouse.y) * sensitivity * Mathf.Rad2Deg;
            float yawDelta = mouseYaw + stick.x * stickSensitivity * Time.deltaTime;
            float pitchDelta = mousePitch
                             + (invertY ? stick.y : -stick.y) * stickSensitivity * Time.deltaTime;

            transform.Rotate(Vector3.up, yawDelta, Space.Self);

            _pitch = Mathf.Clamp(_pitch + pitchDelta, pitchMin, pitchMax);
            cameraTransform.localRotation = Quaternion.Euler(_pitch, 0f, 0f);
        }

        public void SetLookEnabled(bool enabled)
        {
            // 视角只管视角；光标锁定交给 GameManager 的 PausedState/PlayingState 统一管理。
            _lookEnabled = enabled;
        }
    }
}
