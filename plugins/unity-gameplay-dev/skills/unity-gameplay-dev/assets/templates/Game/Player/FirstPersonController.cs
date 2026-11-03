// 第一人称移动控制器（CharacterController 方案，不依赖刚体）。
// 数值按 GDD 手感规格可调：期望移速、加速度、跳跃高度都在 Inspector，禁止硬编码。
// 挂在 Player 根对象，要求同对象有 CharacterController；移动方向相对相机偏航。
using System;
using UnityEngine;

namespace {{NS}}
{
    [RequireComponent(typeof(CharacterController))]
    public class FirstPersonController : MonoBehaviour
    {
        [SerializeField] private InputReader input;
        [SerializeField] private Transform cameraRig;
        [SerializeField] private Animator animator;

        [Header("速度（m/s）")]
        [SerializeField] private float walkSpeed = 4.5f;
        [SerializeField] private float sprintSpeed = 7.0f;
        [SerializeField] private float crouchSpeed = 2.2f;
        [SerializeField] private float groundAcceleration = 12f;
        [SerializeField] private float airAcceleration = 2.5f;

        [Header("跳跃与重力")]
        [SerializeField] private float jumpHeight = 1.2f;
        [SerializeField] private float gravity = -20f;
        [SerializeField] private float terminalVelocity = -40f;

        [Header("蹲伏")]
        [SerializeField] private float standHeight = 1.8f;
        [SerializeField] private float crouchHeight = 1.0f;
        [SerializeField] private float standCameraY = 1.6f;
        [SerializeField] private float crouchCameraY = 0.9f;
        [SerializeField] private float crouchLerpSpeed = 10f;

        [Header("地面检测")]
        [SerializeField] private float groundStickForce = -3f;

        private CharacterController _controller;
        private Vector3 _horizontalVelocity;
        private float _verticalVelocity;
        private bool _isSprinting;
        private bool _isCrouching;
        private Vector3 _externalVelocity; // 击退/爆炸等一次性冲量，逐帧衰减

        public bool IsGrounded { get; private set; }
        public float CurrentSpeed { get; private set; }

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
        }

        private void OnEnable()
        {
            if (input != null)
            {
                input.JumpPerformed += OnJump;
                input.SprintChanged += OnSprintChanged;
                input.CrouchChanged += OnCrouchChanged;
            }
        }

        private void OnDisable()
        {
            if (input != null)
            {
                input.JumpPerformed -= OnJump;
                input.SprintChanged -= OnSprintChanged;
                input.CrouchChanged -= OnCrouchChanged;
            }
        }

        private void Update()
        {
            if (input == null)
            {
                return;
            }

            UpdateCrouch();
            UpdateMovement(Time.deltaTime);
            UpdateAnimator();
        }

        /// <summary>外部系统施加的冲量（如爆炸击退）。</summary>
        public void AddImpulse(Vector3 impulse)
        {
            _externalVelocity += impulse;
        }

        private void OnSprintChanged(bool pressed)
        {
            _isSprinting = pressed && !_isCrouching;
        }

        private void OnCrouchChanged(bool pressed)
        {
            _isCrouching = pressed;
            if (_isCrouching)
            {
                _isSprinting = false;
            }
        }

        private void OnJump()
        {
            if (IsGrounded && !_isCrouching)
            {
                _verticalVelocity = Mathf.Sqrt(2f * Mathf.Abs(gravity) * jumpHeight);
            }
        }

        private void UpdateCrouch()
        {
            float targetHeight = _isCrouching ? crouchHeight : standHeight;
            float targetCameraY = _isCrouching ? crouchCameraY : standCameraY;

            _controller.height = Mathf.Lerp(_controller.height, targetHeight,
                crouchLerpSpeed * Time.deltaTime);
            _controller.center = new Vector3(0f, _controller.height * 0.5f, 0f);

            if (cameraRig != null)
            {
                Vector3 local = cameraRig.localPosition;
                local.y = Mathf.Lerp(local.y, targetCameraY, crouchLerpSpeed * Time.deltaTime);
                cameraRig.localPosition = local;
            }
        }

        private void UpdateMovement(float dt)
        {
            IsGrounded = _controller.isGrounded;
            if (IsGrounded && _verticalVelocity < 0f)
            {
                _verticalVelocity = groundStickForce; // 贴地，防止走斜坡/台阶时离地
            }

            Vector2 moveInput = input.Move;
            Vector3 wishDir = new Vector3(moveInput.x, 0f, moveInput.y);
            wishDir = transform.TransformDirection(wishDir);
            if (wishDir.sqrMagnitude > 1f)
            {
                wishDir.Normalize();
            }

            float targetSpeed = _isCrouching ? crouchSpeed :
                (_isSprinting ? sprintSpeed : walkSpeed);
            Vector3 targetVelocity = wishDir * targetSpeed;
            float acceleration = IsGrounded ? groundAcceleration : airAcceleration;
            _horizontalVelocity = Vector3.MoveTowards(
                _horizontalVelocity, targetVelocity, acceleration * dt);

            _verticalVelocity += gravity * dt;
            _verticalVelocity = Mathf.Max(_verticalVelocity, terminalVelocity);

            Vector3 motion = _horizontalVelocity + Vector3.up * _verticalVelocity + _externalVelocity;
            _controller.Move(motion * dt);
            _externalVelocity = Vector3.MoveTowards(_externalVelocity, Vector3.zero,
                _externalVelocity.magnitude * dt * 6f);

            CurrentSpeed = new Vector3(_horizontalVelocity.x, 0f, _horizontalVelocity.z).magnitude;
        }

        private void UpdateAnimator()
        {
            if (animator == null)
            {
                return;
            }

            animator.SetFloat("MoveSpeed", CurrentSpeed, 0.1f, Time.deltaTime);
            animator.SetBool("IsGrounded", IsGrounded);
            animator.SetBool("IsCrouching", _isCrouching);
        }
    }
}
