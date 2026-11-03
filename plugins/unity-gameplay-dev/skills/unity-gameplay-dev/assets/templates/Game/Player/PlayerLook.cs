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

        private void OnEnable()
        {
            if (input != null)
            {
                input.PausePerformed += OnPause;
            }
        }

        private void OnDisable()
        {
            if (input != null)
            {
                input.PausePerformed -= OnPause;
            }
        }

        private void OnPause()
        {
            // 暂停时不在这里改光标，由 UI/流程层统一控制；这里只保证可恢复
            SetLookEnabled(Cursor.lockState != CursorLockMode.Locked);
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
            _lookEnabled = enabled;
            Cursor.lockState = enabled ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !enabled;
        }
    }
}
