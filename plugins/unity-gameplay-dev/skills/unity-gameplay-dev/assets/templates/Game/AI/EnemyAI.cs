// 敌人 AI：巡逻 → 追击 → 攻击 的状态机骨架（NavMeshAgent）。
// 死亡/受击/特殊技能在此基础上扩展状态；动画参数在各状态内设置。
// 前置：场景烘焙 NavMesh（Window > AI > Navigation，或 NavMeshSurface）；
// 敌人对象需要 NavMeshAgent + 碰撞体；巡逻点在 Inspector 配置。
using System;
using UnityEngine;
using UnityEngine.AI;

namespace {{NS}}
{
    [RequireComponent(typeof(NavMeshAgent))]
    public class EnemyAI : MonoBehaviour
    {
        [SerializeField] private EnemyPerception perception;
        [SerializeField] private Animator animator;
        [SerializeField] private Transform[] patrolPoints;

        [Header("数值")]
        [SerializeField] private float patrolSpeed = 1.5f;
        [SerializeField] private float chaseSpeed = 4.5f;
        [SerializeField] private float attackRange = 1.8f;
        [SerializeField] private float attackCooldown = 1.2f;
        [SerializeField] private float waypointTolerance = 0.5f;

        public NavMeshAgent Agent { get; private set; }
        public EnemyPerception Perception => perception;
        public Transform[] PatrolPoints => patrolPoints;
        public float PatrolSpeed => patrolSpeed;
        public float ChaseSpeed => chaseSpeed;
        public float AttackRange => attackRange;
        public float AttackCooldown => attackCooldown;
        public float WaypointTolerance => waypointTolerance;
        public Animator Animator => animator;

        public readonly StateMachine Fsm = new StateMachine();

        private void Awake()
        {
            Agent = GetComponent<NavMeshAgent>();
        }

        private void Start()
        {
            if (perception != null)
            {
                perception.TargetAcquired += OnTargetAcquired;
                perception.TargetLost += OnTargetLost;
            }

            Fsm.Change(new EnemyPatrolState(this));
        }

        private void Update()
        {
            Fsm.Tick();
        }

        private void FixedUpdate()
        {
            Fsm.FixedTick();
        }

        private void OnTargetAcquired(Transform target)
        {
            Fsm.Change(new EnemyChaseState(this));
        }

        private void OnTargetLost()
        {
            Fsm.Change(new EnemyPatrolState(this));
        }

        public void NotifyAttackPerformed()
        {
            // 攻击判定帧：由动画事件（Animation Event）调用，做伤害/击退
            if (Perception != null && Perception.HasTarget &&
                Vector3.Distance(transform.position, Perception.Target.position) <= attackRange + 0.2f
                && Perception.Target.TryGetComponent(out Health health))
            {
                health.Damage(10f);
            }
        }
    }

    // ---------- 状态 ----------

    public class EnemyPatrolState : IState
    {
        private readonly EnemyAI _enemy;
        private int _index;

        public EnemyPatrolState(EnemyAI enemy)
        {
            _enemy = enemy;
        }

        public void Enter()
        {
            _enemy.Agent.speed = _enemy.PatrolSpeed;
            GotoNextPoint();
            _enemy.Animator?.SetBool("IsChasing", false);
        }

        public void Tick()
        {
            if (_enemy.Perception != null && _enemy.Perception.HasTarget)
            {
                _enemy.Fsm.Change(new EnemyChaseState(_enemy));
                return;
            }

            if (_enemy.PatrolPoints.Length == 0)
            {
                return;
            }

            Transform point = _enemy.PatrolPoints[_index];
            if (Vector3.Distance(_enemy.transform.position, point.position) <= _enemy.WaypointTolerance)
            {
                GotoNextPoint();
            }
        }

        public void FixedTick() { }
        public void Exit() { }

        private void GotoNextPoint()
        {
            if (_enemy.PatrolPoints.Length == 0)
            {
                return;
            }

            _index = (_index + 1) % _enemy.PatrolPoints.Length;
            _enemy.Agent.SetDestination(_enemy.PatrolPoints[_index].position);
        }
    }

    public class EnemyChaseState : IState
    {
        private readonly EnemyAI _enemy;

        public EnemyChaseState(EnemyAI enemy)
        {
            _enemy = enemy;
        }

        public void Enter()
        {
            _enemy.Agent.speed = _enemy.ChaseSpeed;
            _enemy.Animator?.SetBool("IsChasing", true);
        }

        public void Tick()
        {
            if (_enemy.Perception == null || !_enemy.Perception.HasTarget)
            {
                _enemy.Fsm.Change(new EnemyPatrolState(_enemy));
                return;
            }

            Transform target = _enemy.Perception.Target;
            float distance = Vector3.Distance(_enemy.transform.position, target.position);
            if (distance <= _enemy.AttackRange)
            {
                _enemy.Fsm.Change(new EnemyAttackState(_enemy));
                return;
            }

            _enemy.Agent.SetDestination(target.position);
        }

        public void FixedTick() { }
        public void Exit() { }
    }

    public class EnemyAttackState : IState
    {
        private readonly EnemyAI _enemy;
        private float _nextAttackTime;

        public EnemyAttackState(EnemyAI enemy)
        {
            _enemy = enemy;
        }

        public void Enter()
        {
            _enemy.Agent.ResetPath();
            _enemy.Agent.isStopped = true;
            _enemy.Animator?.SetBool("IsChasing", false);
        }

        public void Tick()
        {
            if (_enemy.Perception == null || !_enemy.Perception.HasTarget)
            {
                _enemy.Fsm.Change(new EnemyPatrolState(_enemy));
                return;
            }

            Transform target = _enemy.Perception.Target;
            FaceTarget(target);

            float distance = Vector3.Distance(_enemy.transform.position, target.position);
            if (distance > _enemy.AttackRange * 1.2f)
            {
                _enemy.Fsm.Change(new EnemyChaseState(_enemy));
                return;
            }

            if (Time.time >= _nextAttackTime)
            {
                _nextAttackTime = Time.time + _enemy.AttackCooldown;
                _enemy.Animator?.SetTrigger("Attack");
                // 实际伤害由动画事件 NotifyAttackPerformed 触发，保证与出手帧对齐
            }
        }

        public void FixedTick() { }

        public void Exit()
        {
            _enemy.Agent.isStopped = false;
        }

        private void FaceTarget(Transform target)
        {
            Vector3 direction = target.position - _enemy.transform.position;
            direction.y = 0f;
            if (direction.sqrMagnitude > 0.001f)
            {
                Quaternion rotation = Quaternion.LookRotation(direction);
                _enemy.transform.rotation =
                    Quaternion.Slerp(_enemy.transform.rotation, rotation, 8f * Time.deltaTime);
            }
        }
    }
}
