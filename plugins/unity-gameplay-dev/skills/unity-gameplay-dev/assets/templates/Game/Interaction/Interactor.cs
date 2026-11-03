// 从相机中心发射射线检测可交互物（FPS 准星交互）。
// 挂在 Player 上，相机引用为主相机；命中时通过 EventBus 发提示文本，
// 按下交互键时调用目标的 Interact。
using UnityEngine;

namespace {{NS}}
{
    public class Interactor : MonoBehaviour
    {
        [SerializeField] private InputReader input;
        [SerializeField] private Camera viewCamera;

        [Header("检测")]
        [SerializeField] private float range = 2.5f;
        [SerializeField] private float radius = 0.08f; // 胶囊射线半径，小物体也能命中
        [SerializeField] private LayerMask interactableLayers = ~0;
        [SerializeField] private QueryTriggerInteraction triggerInteraction =
            QueryTriggerInteraction.Collide;

        private IInteractable _current;

        private void Awake()
        {
            if (viewCamera == null)
            {
                viewCamera = Camera.main;
            }
        }

        private void OnEnable()
        {
            if (input != null)
            {
                input.InteractPerformed += OnInteract;
            }
        }

        private void OnDisable()
        {
            if (input != null)
            {
                input.InteractPerformed -= OnInteract;
            }

            ClearCurrent();
        }

        private void Update()
        {
            IInteractable target = Detect();
            if (target == _current)
            {
                return;
            }

            _current?.SetHighlight(false);
            _current = target;
            _current?.SetHighlight(true);

            EventBus.Publish(new InteractionPromptEvent(_current?.PromptText ?? string.Empty));
        }

        private IInteractable Detect()
        {
            if (viewCamera == null)
            {
                return null;
            }

            Vector3 origin = viewCamera.transform.position;
            Vector3 direction = viewCamera.transform.forward;
            RaycastHit[] hits = Physics.SphereCastAll(
                origin, radius, direction, range, interactableLayers, triggerInteraction);

            IInteractable best = null;
            float bestDistance = float.MaxValue;
            foreach (RaycastHit hit in hits)
            {
                if (hit.collider.TryGetComponent(out IInteractable interactable)
                    && hit.distance < bestDistance)
                {
                    best = interactable;
                    bestDistance = hit.distance;
                }
            }

            return best;
        }

        private void OnInteract()
        {
            _current?.Interact(gameObject);
        }

        private void ClearCurrent()
        {
            _current?.SetHighlight(false);
            _current = null;
            EventBus.Publish(new InteractionPromptEvent(string.Empty));
        }
    }
}
