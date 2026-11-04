// 第三人称移动控制器（CharacterController 方案，与 FirstPersonController 同源）。
//
// 与第一人称的关键区别只有两点，其余（重力/跳跃/加速/Animator 参数）完全一致：
//   1. 移动方向相对**相机水平朝向**，不是相对角色朝向
//      —— 否则角色转身时输入方向会跟着转，手感立刻崩。
//   2. 角色模型需要**转向到移动方向**，且转向有转向速度上限
//      —— 瞬间转身会让动画看起来像在抽搐。
//
// 相机本身不在这里：第三人称相机用 Cinemachine 更省事（见 references/12），
// 这个脚本只负责「告诉相机往哪看」所需的角色状态。
using UnityEngine;

namespace {{NS}}
{
    [RequireComponent(typeof(CharacterController))]
    public class ThirdPersonController : MonoBehaviour
    {
        [SerializeField] private InputReader input;
        [Tooltip("相机水平朝向的参考物体；填主相机的 Transform")]
        [SerializeField] private Transform cameraReference;
        [Tooltip("角色朝向参考（一般是模型根节点，可与本对象相同）")]
        [SerializeField] private Transform modelRoot;
        [SerializeField] private Animator animator;

        [Header("速度（m/s）")]
        [SerializeField] private float walkSpeed = 3.2f;
        [SerializeField] private float sprintSpeed = 6.0f;
        [SerializeField] private float crouchSpeed = 1.6f;
        [SerializeField] private float groundAcceleration = 14f;
        [SerializeField] private float airAcceleration = 3f;

        [Header("跳跃与重力")]
        [SerializeField] private float jumpHeight = 1.1f;
        [SerializeField] private float gravity = -20f;
        [SerializeField] private float terminalVelocity = -40f;

        [Header("转向")]
        [Tooltip("每秒最大转向角度。180 表示半秒转完；太小会很迟钝")]
        [SerializeField] private float turnSpeedDegPerSec = 720f;
        [Tooltip("勾选后角色只在移动时转向（站桩时保持面朝相机前方）")]
        [SerializeField] private bool onlyTurnWhileMoving = true;

        [Header("蹲伏")]
        [SerializeField] private float standHeight = 1.8f;
        [SerializeField] private float crouchHeight = 1.1f;
        [SerializeField] private float crouchLerpSpeed = 10f;
        [Tooltip("起身前检测头顶的层；勾选后头顶有物体会拒绝起身")]
        [SerializeField] private LayerMask ceilingLayers = ~0;

        [Header("地面检测")]
        [SerializeField] private float groundStickForce = -3f;
        [Tooltip("斜坡上允许的最大坡度，超过会被重力推下去")]
        [SerializeField] private float slopeLimit = 45f;

        private CharacterController _controller;
        private Vector3 _horizontalVelocity;
        private float _verticalVelocity;
        private Vector3 _externalVelocity;
        private bool _isSprinting;
        private bool _isCrouching;

        public bool IsGrounded { get; private set; }
        public float CurrentSpeed { get; private set; }
        /// <summary>供相机/瞄准系统读取的角色朝向。</summary>
        public Vector3 FacingDirection =>
            modelRoot != null ? modelRoot.forward : transform.forward;

        private void Awake()
        {
            _controller = GetComponent<CharacterController>();
            _controller.slopeLimit = slopeLimit;
            if (modelRoot == null)
            {
                modelRoot = transform;
            }
        }

        private void OnEnable()
        {
            if (input == null)
            {
                return;
            }

            input.JumpPerformed += OnJump;
            input.SprintChanged += OnSprintChanged;
            input.CrouchChanged += OnCrouchChanged;
        }

        private void OnDisable()
        {
            if (input == null)
            {
                return;
            }

            input.JumpPerformed -= OnJump;
            input.SprintChanged -= OnSprintChanged;
            input.CrouchChanged -= OnCrouchChanged;
        }

        private void Update()
        {
            if (input == null)
            {
                return;
            }

            float dt = Time.deltaTime;
            UpdateCrouch(dt);
            UpdateMovement(dt);
            UpdateFacing(dt);
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
            // 起身前查头顶：在低矮通道里松开蹲伏不能直接站起来穿模。
            if (!pressed && !_isCrouching)
            {
                return;
            }
            if (!pressed && BlockedFromStanding())
            {
                return; // 头顶有东西，保持蹲伏
            }

            _isCrouching = pressed;
            if (_isCrouching)
            {
                _isSprinting = false;
            }
        }

        private bool BlockedFromStanding()
        {
            if (_controller == null)
            {
                return false;
            }
            float radius = Mathf.Max(_controller.radius - 0.02f, 0.05f);
            Vector3 start = transform.position + Vector3.up * (crouchHeight + radius);
            float distance = Mathf.Max(standHeight - crouchHeight, 0f);
            return Physics.SphereCast(start, radius, Vector3.up, out _, distance,
                ceilingLayers, QueryTriggerInteraction.Ignore);
        }

        /// <summary>蹲伏时同步碰撞体高度，否则低矮通道会穿模。</summary>
        private void UpdateCrouch(float dt)
        {
            float target = _isCrouching ? crouchHeight : standHeight;
            if (Mathf.Abs(_controller.height - target) > 0.001f)
            {
                _controller.height = Mathf.MoveTowards(
                    _controller.height, target, crouchLerpSpeed * dt);
                _controller.center = new Vector3(0f, _controller.height * 0.5f, 0f);
            }
        }

        private void OnJump()
        {
            if (IsGrounded && !_isCrouching)
            {
                _verticalVelocity = Mathf.Sqrt(2f * Mathf.Abs(gravity) * jumpHeight);
            }
        }

        /// <summary>把输入方向投影到相机水平面上。相机为空时退化为世界坐标。</summary>
        private Vector3 CameraRelativeDirection(Vector2 moveInput)
        {
            if (cameraReference == null)
            {
                return new Vector3(moveInput.x, 0f, moveInput.y);
            }

            Vector3 camForward = cameraReference.forward;
            camForward.y = 0f;
            if (camForward.sqrMagnitude < 0.0001f)
            {
                // 相机正对地面时水平朝向不稳定，退化到相机右手方向
                camForward = cameraReference.up;
                camForward.y = 0f;
            }
            camForward.Normalize();

            Vector3 camRight = new Vector3(camForward.z, 0f, -camForward.x);
            Vector3 dir = camForward * moveInput.y + camRight * moveInput.x;
            if (dir.sqrMagnitude > 1f)
            {
                dir.Normalize();
            }
            return dir;
        }

        private void UpdateMovement(float dt)
        {
            IsGrounded = _controller.isGrounded;
            if (IsGrounded && _verticalVelocity < 0f)
            {
                _verticalVelocity = groundStickForce;
            }

            Vector3 wishDir = CameraRelativeDirection(input.Move);

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

        private void UpdateFacing(float dt)
        {
            Vector3 lookDir = _horizontalVelocity;
            lookDir.y = 0f;

            if (lookDir.sqrMagnitude < 0.01f)
            {
                if (onlyTurnWhileMoving)
                {
                    return;
                }
                // 站桩时朝相机前方，避免背对镜头站着的怪异感
                Vector3 camFwd = cameraReference != null ? cameraReference.forward : modelRoot.forward;
                camFwd.y = 0f;
                if (camFwd.sqrMagnitude < 0.0001f)
                {
                    return;
                }
                lookDir = camFwd;
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
            animator.SetBool("IsCrouching", _isCrouching);

            // 第三人称常需要「相对相机的移动方向」做 8 向 blendspace：
            // 局部速度 = 把世界速度转到角色空间，x 是左右、z 是前后。
            Vector3 localVel = modelRoot.InverseTransformDirection(_horizontalVelocity);
            animator.SetFloat("LocalMoveX", localVel.x, 0.1f, Time.deltaTime);
            animator.SetFloat("LocalMoveZ", localVel.z, 0.1f, Time.deltaTime);
        }
    }
}
