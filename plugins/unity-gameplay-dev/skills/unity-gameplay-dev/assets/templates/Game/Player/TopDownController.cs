// 俯视角 / 双摇杆移动控制器（CharacterController 方案，与另两个控制器同源）。
//
// 与第一/第三人称最本质的区别：**输入方向不相对相机**。
// 俯视角游戏里相机是固定的俯角，玩家按「上」就是屏幕上的上方，
// 如果按第三人称那样相对相机做投影，斜俯角会让"上"变成"斜后方"，手感立刻错。
//
// 双摇杆射击在此基础上再加一条：**移动方向与瞄准方向解耦**。
// 左摇杆移动、右摇杆瞄准，角色朝向跟随瞄准而不是移动。
using UnityEngine;
using UnityEngine.InputSystem;

namespace {{NS}}
{
    [RequireComponent(typeof(CharacterController))]
    public class TopDownController : MonoBehaviour
    {
        [SerializeField] private InputReader input;
        [Tooltip("角色模型根节点；朝向会转到这里。留空则用本对象")]
        [SerializeField] private Transform modelRoot;
        [SerializeField] private Animator animator;

        [Header("移动（m/s）")]
        [SerializeField] private float moveSpeed = 5.0f;
        [SerializeField] private float sprintSpeed = 8.0f;
        [SerializeField] private float acceleration = 40f;
        [SerializeField] private float deceleration = 55f;

        [Header("转向")]
        [Tooltip("移动时朝移动方向；false 时只朝瞄准方向（纯双摇杆）")]
        [SerializeField] private bool faceMoveWhenNoAim = true;
        [SerializeField] private float turnSpeedDegPerSec = 1080f;

        [Header("双摇杆")]
        [Tooltip("勾选启用右摇杆瞄准；关闭则角色朝移动方向")]
        [SerializeField] private bool twinStickAim = false;
        [Tooltip("右摇杆死区，低于此值视为没有瞄准输入")]
        [Range(0f, 0.9f)]
        [SerializeField] private float aimDeadzone = 0.25f;

        [Header("重力（贴地用的最小实现）")]
        [SerializeField] private float gravity = -25f;
        [SerializeField] private float groundStickForce = -2f;

        private CharacterController _controller;
        private Vector3 _horizontalVelocity;
        private float _verticalVelocity;
        private bool _isSprinting;
        private Vector2 _aimInput;

        public bool IsGrounded { get; private set; }
        public float CurrentSpeed { get; private set; }
        /// <summary>当前朝向，供射击/交互系统取用。</summary>
        public Vector3 FacingDirection =>
            modelRoot != null ? modelRoot.forward : transform.forward;
        /// <summary>是否正在被玩家用右摇杆瞄准。</summary>
        public bool HasAimInput { get; private set; }

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            if (modelRoot == null)
            {
                modelRoot = transform;
            }
        }

        private void OnEnable()
        {
            if (input != null)
            {
                input.SprintChanged += OnSprintChanged;
            }
        }

        private void OnDisable()
        {
            if (input != null)
            {
                input.SprintChanged -= OnSprintChanged;
            }
        }

        private void OnSprintChanged(bool pressed)
        {
            _isSprinting = pressed;
        }

        private void Update()
        {
            if (input == null)
            {
                return;
            }

            float dt = Time.deltaTime;
            UpdateAim();
            UpdateMovement(dt);
            UpdateFacing(dt);
            UpdateAnimator();
        }

        private void UpdateAim()
        {
            if (!twinStickAim)
            {
                HasAimInput = false;
                return;
            }

            _aimInput = input.LookStick;
            HasAimInput = _aimInput.magnitude > aimDeadzone;
        }

        private void UpdateMovement(float dt)
        {
            IsGrounded = _controller.isGrounded;
            if (IsGrounded && _verticalVelocity < 0f)
            {
                _verticalVelocity = groundStickForce;
            }

            // 关键：直接用输入的世界轴向，不投影到相机。
            Vector2 move = input.Move;
            Vector3 wishDir = new Vector3(move.x, 0f, move.y);
            if (wishDir.sqrMagnitude > 1f)
            {
                wishDir.Normalize();
            }

            float targetSpeed = _isSprinting ? sprintSpeed : moveSpeed;
            Vector3 targetVelocity = wishDir * targetSpeed;
            bool hasInput = wishDir.sqrMagnitude > 0.0025f;
            float rate = hasInput ? acceleration : deceleration;

            _horizontalVelocity = Vector3.MoveTowards(
                _horizontalVelocity, targetVelocity, rate * dt);

            _verticalVelocity += gravity * dt;

            Vector3 motion = _horizontalVelocity + Vector3.up * _verticalVelocity;
            _controller.Move(motion * dt);

            CurrentSpeed = new Vector3(_horizontalVelocity.x, 0f, _horizontalVelocity.z).magnitude;
        }

        private void UpdateFacing(float dt)
        {
            Vector3 lookDir;

            if (twinStickAim && HasAimInput)
            {
                // 有瞄准输入：朝瞄准方向，与移动解耦
                lookDir = new Vector3(_aimInput.x, 0f, _aimInput.y);
            }
            else if (_horizontalVelocity.sqrMagnitude > 0.01f)
            {
                lookDir = _horizontalVelocity;
                lookDir.y = 0f;
            }
            else if (faceMoveWhenNoAim)
            {
                return; // 站着不动就保持当前朝向
            }
            else
            {
                return;
            }

            if (lookDir.sqrMagnitude < 0.0001f)
            {
                return;
            }

            Quaternion target = Quaternion.LookRotation(lookDir.normalized, Vector3.up);
            modelRoot.rotation = Quaternion.RotateTowards(
                modelRoot.rotation, target, turnSpeedDegPerSec * dt);
        }

        private void UpdateAnimator()
        {
            if (animator == null)
            {
                return;
            }

            animator.SetFloat("MoveSpeed", CurrentSpeed, 0.1f, Time.deltaTime);
            animator.SetBool("IsGrounded", IsGrounded);

            if (twinStickAim)
            {
                animator.SetBool("IsAiming", HasAimInput);
                animator.SetFloat("AimX", _aimInput.x, 0.1f, Time.deltaTime);
                animator.SetFloat("AimY", _aimInput.y, 0.1f, Time.deltaTime);
            }
        }
    }
}
