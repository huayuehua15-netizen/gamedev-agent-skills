// 敌人感知：视锥 + 距离检测，发现目标后回调。只负责"看没看见"，不负责移动。
// 挂在敌人上，与 NavMeshAgent 同层级；隔墙看不见（视线被碰撞体遮挡时丢失）。
using System;
using UnityEngine;

namespace {{NS}}
{
    public class EnemyPerception : MonoBehaviour
    {
        [SerializeField] private Transform eye;
        [SerializeField] private float sightRange = 12f;
        [SerializeField] private float halfFieldOfView = 60f; // 半 FOV，总视角 120°
        [SerializeField] private float loseRange = 16f;
        [SerializeField] private LayerMask sightBlockers = ~0;
        [SerializeField] private LayerMask targetLayers = ~0;
        [SerializeField] private float scanInterval = 0.15f;

        public Transform Target { get; private set; }
        public bool HasTarget => Target != null;

        public event Action<Transform> TargetAcquired;
        public event Action TargetLost;

        private float _nextScan;

        private void Reset()
        {
            eye = transform;
        }

        private void Update()
        {
            if (Time.time < _nextScan)
            {
                return;
            }

            _nextScan = Time.time + scanInterval;
            Scan();
        }

        private void Scan()
        {
            Vector3 eyePos = eye != null ? eye.position : transform.position + Vector3.up * 1.6f;

            if (HasTarget)
            {
                if (Target == null || Vector3.Distance(eyePos, Target.position) > loseRange
                    || !HasLineOfSight(eyePos, Target))
                {
                    Target = null;
                    TargetLost?.Invoke();
                }

                return;
            }

            Collider[] hits = Physics.OverlapSphere(eyePos, sightRange, targetLayers);
            Transform best = null;
            float bestDistance = float.MaxValue;
            foreach (var hit in hits)
            {
                var candidate = hit.transform;
                float distance = Vector3.Distance(eyePos, candidate.position);
                if (distance >= bestDistance)
                {
                    continue;
                }

                Vector3 direction = candidate.position + Vector3.up * 1.0f - eyePos;
                float angle = Vector3.Angle(transform.forward, direction);
                if (angle <= halfFieldOfView && HasLineOfSight(eyePos, candidate))
                {
                    best = candidate;
                    bestDistance = distance;
                }
            }

            if (best != null)
            {
                Target = best;
                TargetAcquired?.Invoke(best);
            }
        }

        private bool HasLineOfSight(Vector3 eyePos, Transform target)
        {
            Vector3 targetPoint = target.position + Vector3.up * 1.4f;
            Vector3 direction = targetPoint - eyePos;
            if (Physics.Raycast(eyePos, direction, out RaycastHit hit, direction.magnitude,
                    sightBlockers, QueryTriggerInteraction.Ignore))
            {
                return hit.transform.IsChildOf(target) || hit.transform == target;
            }

            return true;
        }

        private void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1f, 0.6f, 0.2f, 0.6f);
            Gizmos.DrawWireSphere(transform.position, sightRange);
        }
    }
}
