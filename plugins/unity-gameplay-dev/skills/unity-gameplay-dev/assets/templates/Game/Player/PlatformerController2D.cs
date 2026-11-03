// 2D 平台跳跃控制器（Rigidbody2D 方案）。
// 与 FirstPersonController 的关键区别：
//   - 用 Rigidbody2D.velocity 驱动，不用 transform.position（直接改位置会穿墙）
//   - 地面检测用 Physics2D.OverlapCircle，不用 collision.normal.y（后者在斜坡/角落会误判）
//   - 带 Coyote Time 与 Jump Buffer：这两个是"跳得粘不粘"的分水岭，缺了手感明显差
//   - 用独立层矩阵（groundLayers），不靠 Tag
// 挂在玩家根对象，要求同对象有 Rigidbody2D + CapsuleCollider2D。
// 数值按 GDD 手感规格可调，禁止硬编码。
using UnityEngine;

namespace {{NS}}
{
    [RequireComponent(typeof(Rigidbody2D))]
    public class PlatformerController2D : MonoBehaviour
    {
        [SerializeField] private InputReader input;

        [Header("移动（单位/秒）")]
        [SerializeField] private float moveSpeed = 7f;
        [SerializeField] private float runSpeed = 11f;
        [SerializeField] private float groundAcceleration = 90f;
        [SerializeField] private float groundDeceleration = 110f;
        [SerializeField] private float airAcceleration = 40f;
        [SerializeField] private float airDeceleration = 30f;

        [Header("跳跃")]
        [SerializeField] private float jumpVelocity = 14f;
        [SerializeField] private float gravityScale = 3.2f;
        [Tooltip("松开跳跃键后上升速度乘以此值（可变跳跃高度）")]
        [SerializeField] private float jumpCutMultiplier = 0.45f;
        [Tooltip("最大下落速度，防止高速穿过触发器")]
        [SerializeField] private float maxFallSpeed = 22f;

        [Header("手感辅助")]
        [Tooltip("离开平台后仍可起跳的宽限时间（秒）")]
        [SerializeField] private float coyoteTime = 0.10f;
        [Tooltip("落地前提前按跳的缓冲时间（秒）")]
        [SerializeField] private float jumpBufferTime = 0.10f;

        [Header("地面检测")]
        [Tooltip("脚底检测点（空物体，放在胶囊底部）")]
        [SerializeField] private Transform groundCheck;
        [SerializeField] private float groundCheckRadius = 0.14f;
        [Tooltip("哪些层算地面；必须在 Physics2D 碰撞矩阵里与该层互相勾选")]
        [SerializeField] private LayerMask groundLayers;

        private Rigidbody2D _rb;
        private bool _isRunning;
        private bool _jumpHeld;

        private float _coyoteCounter;      // 剩余可起跳宽限
        private float _jumpBufferCounter;  // 剩余缓冲
        private float _defaultGravityScale;

        public bool IsGrounded { get; private set; }
        public float CurrentSpeed => Mathf.Abs(_rb != null ? _rb.linearVelocity.x : 0f);

        private void Awake()
        {
            _rb = GetComponent<Rigidbody2D>();
            _defaultGravityScale = gravityScale;
            _rb.gravityScale = gravityScale;
            // 防止角色自己转圈
            _rb.freezeRotation = true;
            // 连续碰撞检测：快速下落时不穿地板
            _rb.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            _rb.interpolation = RigidbodyInterpolation2D.Interpolate;
        }

        private void OnEnable()
        {
            if (input == null)
            {
                return;
            }

            input.JumpPerformed += OnJumpPressed;
            input.SprintChanged += OnSprintChanged;
        }

        private void OnDisable()
        {
            if (input == null)
            {
                return;
            }

            input.JumpPerformed -= OnJumpPressed;
            input.SprintChanged -= OnSprintChanged;
        }

        private void OnJumpPressed()
        {
            // 按键不直接起跳，而是充能缓冲。真正起跳在 FixedUpdate 里判定，
            // 这样"落地前一瞬间按下"也能生效。
            _jumpBufferCounter = jumpBufferTime;
            _jumpHeld = true;
        }

        private void OnSprintChanged(bool sprinting)
        {
            _isRunning = sprinting;
        }

        private void FixedUpdate()
        {
            UpdateGrounded();
            UpdateTimers();
            HandleHorizontal();
            HandleJump();
            ClampFall();
        }

        private void UpdateGrounded()
        {
            if (groundCheck == null)
            {
                IsGrounded = false;
                return;
            }

            IsGrounded = Physics2D.OverlapCircle(
                groundCheck.position, groundCheckRadius, groundLayers) != null;

            if (IsGrounded)
            {
                _coyoteCounter = coyoteTime;
            }
        }

        private void UpdateTimers()
        {
            if (_coyoteCounter > 0f)
            {
                _coyoteCounter -= Time.fixedDeltaTime;
            }

            if (_jumpBufferCounter > 0f)
            {
                _jumpBufferCounter -= Time.fixedDeltaTime;
            }

            // 松开跳跃键 → 终止上升（可变跳跃高度）
            if (_jumpHeld && !IsJumpStillHeld())
            {
                _jumpHeld = false;
                if (_rb.linearVelocity.y > 0f)
                {
                    _rb.linearVelocity = new Vector2(
                        _rb.linearVelocity.x, _rb.linearVelocity.y * jumpCutMultiplier);
                }
            }
        }

        private bool IsJumpStillHeld()
        {
            // Input System 的 Button 是否仍按住；用 wasPressedThisFrame 之类会漏持续态，
            // 这里直接查动作状态，避免与 InputReader 的事件模型耦合过深。
            var action = input != null ? input.JumpAction : null;
            return action != null && action.IsPressed();
        }

        private void HandleHorizontal()
        {
            float target = 0f;
            if (input != null && Mathf.Abs(input.Move.x) > 0.2f)
            {
                float speed = _isRunning ? runSpeed : moveSpeed;
                target = input.Move.x * speed;
            }

            bool hasInput = Mathf.Abs(target) > 0.01f;
            float rate;
            if (IsGrounded)
            {
                rate = hasInput ? groundAcceleration : groundDeceleration;
            }
            else
            {
                rate = hasInput ? airAcceleration : airDeceleration;
            }

            float newX = Mathf.MoveTowards(
                _rb.linearVelocity.x, target, rate * Time.fixedDeltaTime);
            _rb.linearVelocity = new Vector2(newX, _rb.linearVelocity.y);
        }

        private void HandleJump()
        {
            bool canJump = _coyoteCounter > 0f && _jumpBufferCounter > 0f;
            if (!canJump)
            {
                return;
            }

            // 消费缓冲与土狼时间，防止一次按键连跳
            _jumpBufferCounter = 0f;
            _coyoteCounter = 0f;
            _rb.linearVelocity = new Vector2(_rb.linearVelocity.x, jumpVelocity);

            // 起跳瞬间恢复正常重力（若曾被 jumpCut 改过）
            _rb.gravityScale = _defaultGravityScale;
        }

        private void ClampFall()
        {
            if (_rb.linearVelocity.y < -maxFallSpeed)
            {
                _rb.linearVelocity = new Vector2(_rb.linearVelocity.x, -maxFallSpeed);
            }
        }

        private void OnDrawGizmosSelected()
        {
            if (groundCheck == null)
            {
                return;
            }

            Gizmos.color = IsGrounded ? Color.green : Color.red;
            Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
        }
    }
}
