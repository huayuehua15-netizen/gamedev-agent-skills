// 通用对象池：子弹、命中特效、掉落物、敌人尸体等高频生成对象统一走池。
// 用法：var pool = new ObjectPool(prefab, 16, parent); var go = pool.Get(); pool.Release(go);
// 预制体根节点要求挂 PooledObject（或在外部控制 Release）。
using System.Collections.Generic;
using UnityEngine;

namespace {{NS}}
{
    public class ObjectPool
    {
        private readonly GameObject _prefab;
        private readonly Transform _parent;
        private readonly Stack<GameObject> _available = new();
        private readonly List<GameObject> _all = new();

        public int CountAll => _all.Count;

        public ObjectPool(GameObject prefab, int prewarm = 0, Transform parent = null)
        {
            _prefab = prefab;
            _parent = parent;
            for (int i = 0; i < prewarm; i++)
            {
                var go = Create();
                go.SetActive(false);
                _available.Push(go);
            }
        }

        public GameObject Get(Vector3 position, Quaternion rotation)
        {
            GameObject go = _available.Count > 0 ? _available.Pop() : Create();
            go.transform.SetPositionAndRotation(position, rotation);
            go.SetActive(true);

            if (go.TryGetComponent(out PooledObject pooled))
            {
                pooled.Bind(this);
            }

            return go;
        }

        public void Release(GameObject go)
        {
            if (go == null)
            {
                return;
            }

            go.SetActive(false);
            _available.Push(go);
        }

        private GameObject Create()
        {
            var go = Object.Instantiate(_prefab, _parent);
            _all.Add(go);
            return go;
        }
    }

    public class PooledObject : MonoBehaviour
    {
        private ObjectPool _pool;

        public void Bind(ObjectPool pool)
        {
            _pool = pool;
        }

        public void Release()
        {
            _pool?.Release(gameObject);
        }
    }
}
