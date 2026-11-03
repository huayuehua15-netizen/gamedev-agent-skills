// InputReader —— 新 Input System 的代码化封装，不依赖 .inputactions 资产。
// 键盘/鼠标/手柄绑定在代码里声明；若已用 .inputactions，可直接把本类替换为
// 生成的 C# 类（见 references/02-input-and-fp-controller.md）。
//
// 用法：挂在 Player 根对象上；移动/视角用属性轮询，动作用事件订阅（Jump/Interact...）。
// 暂停时调用 SetInputEnabled(false)。
using System;
using UnityEngine;
using UnityEngine.InputSystem;

namespace {{NS}}
{
    public class InputReader : MonoBehaviour
    {
        // 全场唯一的输入源：GameManager 等系统需要直接订阅 PausePerformed 之类的事件，
        // 没有这个入口就只能靠 Inspector 各自拖引用，容易漏接。
        public static InputReader Instance { get; private set; }

        // 持续量：轮询
        public Vector2 Move { get; private set; }
        // 视角来源必须分开：鼠标 delta 的单位是像素/帧，摇杆是 -1..1，
        // 合并成一个 Vector2 会让两种设备的灵敏度差一个数量级。
        public Vector2 LookMouse { get; private set; }
        public Vector2 LookStick { get; private set; }

        // 离散动作：事件
        public event Action JumpPerformed;
        public event Action InteractPerformed;
        public event Action AttackPerformed;
        public event Action PausePerformed;
        public event Action<bool> SprintChanged; // true=按下 false=松开
        public event Action<bool> CrouchChanged;

        private InputAction _moveAction;
        private InputAction _lookMouseAction;
        private InputAction _lookStickAction;
        private InputAction _jumpAction;
        private InputAction _sprintAction;
        private InputAction _crouchAction;
        private InputAction _interactAction;
        private InputAction _attackAction;
        private InputAction _pauseAction;

        private void Awake()
        {
            Instance = this;
            BuildActions();
        }

        private void OnEnable()
        {
            EnableAll();
        }

        private void OnDisable()
        {
            DisableAll();
        }

        private void Update()
        {
            Move = _moveAction?.ReadValue<Vector2>() ?? Vector2.zero;
            LookMouse = _lookMouseAction?.ReadValue<Vector2>() ?? Vector2.zero;
            LookStick = _lookStickAction?.ReadValue<Vector2>() ?? Vector2.zero;
        }

        public void SetInputEnabled(bool enabled)
        {
            if (enabled)
            {
                EnableAll();
            }
            else
            {
                DisableAll();
                Move = Vector2.zero;
                LookMouse = Vector2.zero;
                LookStick = Vector2.zero;
            }
        }

        private void EnableAll()
        {
            _moveAction?.Enable();
            _lookMouseAction?.Enable();
            _lookStickAction?.Enable();
            _jumpAction?.Enable();
            _sprintAction?.Enable();
            _crouchAction?.Enable();
            _interactAction?.Enable();
            _attackAction?.Enable();
            _pauseAction?.Enable();
        }

        private void DisableAll()
        {
            _moveAction?.Disable();
            _lookMouseAction?.Disable();
            _lookStickAction?.Disable();
            _jumpAction?.Disable();
            _sprintAction?.Disable();
            _crouchAction?.Disable();
            _interactAction?.Disable();
            _attackAction?.Disable();
            _pauseAction?.Disable();
        }

        private void BuildActions()
        {
            // 移动：WASD 2D 复合绑定 + 手柄左摇杆
            _moveAction = new InputAction("Move", InputActionType.Value);
            _moveAction.expectedControlType = "Vector2";
            _moveAction.AddCompositeBinding("2DVector")
                .With("Up", "<Keyboard>/w")
                .With("Down", "<Keyboard>/s")
                .With("Left", "<Keyboard>/a")
                .With("Right", "<Keyboard>/d");
            _moveAction.AddBinding("<Gamepad>/leftStick");

            // 视角：鼠标增量与右摇杆分成两个 action，各自用自己的灵敏度
            _lookMouseAction = new InputAction("LookMouse", InputActionType.Value);
            _lookMouseAction.expectedControlType = "Vector2";
            _lookMouseAction.AddBinding("<Mouse>/delta");

            _lookStickAction = new InputAction("LookStick", InputActionType.Value);
            _lookStickAction.expectedControlType = "Vector2";
            _lookStickAction.AddBinding("<Gamepad>/rightStick");

            _jumpAction = new InputAction("Jump", InputActionType.Button);
            _jumpAction.AddBinding("<Keyboard>/space");
            _jumpAction.AddBinding("<Gamepad>/buttonSouth");
            _jumpAction.performed += _ => JumpPerformed?.Invoke();

            _sprintAction = new InputAction("Sprint", InputActionType.Button);
            _sprintAction.AddBinding("<Keyboard>/leftShift");
            _sprintAction.AddBinding("<Gamepad>/leftStickPress");
            _sprintAction.performed += _ => SprintChanged?.Invoke(true);
            _sprintAction.canceled += _ => SprintChanged?.Invoke(false);

            _crouchAction = new InputAction("Crouch", InputActionType.Button);
            _crouchAction.AddBinding("<Keyboard>/leftCtrl");
            _crouchAction.AddBinding("<Gamepad>/rightStickPress");
            _crouchAction.performed += _ => CrouchChanged?.Invoke(true);
            _crouchAction.canceled += _ => CrouchChanged?.Invoke(false);

            _interactAction = new InputAction("Interact", InputActionType.Button);
            _interactAction.AddBinding("<Keyboard>/e");
            _interactAction.AddBinding("<Gamepad>/buttonWest");
            _interactAction.performed += _ => InteractPerformed?.Invoke();

            _attackAction = new InputAction("Attack", InputActionType.Button);
            _attackAction.AddBinding("<Mouse>/leftButton");
            _attackAction.AddBinding("<Gamepad>/rightTrigger");
            _attackAction.performed += _ => AttackPerformed?.Invoke();

            _pauseAction = new InputAction("Pause", InputActionType.Button);
            _pauseAction.AddBinding("<Keyboard>/escape");
            _pauseAction.AddBinding("<Gamepad>/start");
            _pauseAction.performed += _ => PausePerformed?.Invoke();
        }
    }
}
