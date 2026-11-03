// 存档系统：按存档槽写 JSON 到 Application.persistentDataPath。
// 用 JsonUtility（无第三方依赖）：只支持可序列化类/数组，不支持字典；
// 需要存档的系统实现 ISaveable，注册到 SaveSystem；读档时按 Key 分发 JSON。
// 注意：版本号必须随存档结构变更递增，并在 Load 时做迁移。
using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace {{NS}}
{
    public interface ISaveable
    {
        string SaveKey { get; }
        string CaptureState();
        void RestoreState(string json);
    }

    [Serializable]
    public class SaveData
    {
        public int version = 1;
        public string sceneName = string.Empty;
        public float playerX;
        public float playerY;
        public float playerZ;
        public float playerRotY;
        public List<SavedEntry> entries = new();
    }

    [Serializable]
    public class SavedEntry
    {
        public string key;
        public string json;

        public SavedEntry(string key, string json)
        {
            this.key = key;
            this.json = json;
        }
    }

    public static class SaveSystem
    {
        private const string FilePattern = "save_slot_{0}.json";
        public const int CurrentVersion = 1;

        private static readonly List<ISaveable> Saveables = new();

        public static void Register(ISaveable saveable)
        {
            if (saveable != null && !Saveables.Contains(saveable))
            {
                Saveables.Add(saveable);
            }
        }

        public static void Unregister(ISaveable saveable)
        {
            Saveables.Remove(saveable);
        }

        public static string GetPath(int slot)
        {
            return Path.Combine(Application.persistentDataPath, string.Format(FilePattern, slot));
        }

        public static bool HasSave(int slot)
        {
            return File.Exists(GetPath(slot));
        }

        public static void Write(int slot, SaveData data)
        {
            data.version = CurrentVersion;
            foreach (var saveable in Saveables)
            {
                data.entries.Add(new SavedEntry(saveable.SaveKey, saveable.CaptureState()));
            }

            string json = JsonUtility.ToJson(data, true);
            string path = GetPath(slot);
            string temp = path + ".tmp";
            File.WriteAllText(temp, json);
            if (File.Exists(path))
            {
                File.Delete(path);
            }

            File.Move(temp, path);
        }

        public static SaveData Read(int slot)
        {
            string path = GetPath(slot);
            if (!File.Exists(path))
            {
                return null;
            }

            var data = JsonUtility.FromJson<SaveData>(File.ReadAllText(path));
            if (data == null || data.version > CurrentVersion)
            {
                Debug.LogWarning($"[SaveSystem] 存档版本 {data?.version} 高于当前 {CurrentVersion}，已忽略");
                return null;
            }

            foreach (var entry in data.entries)
            {
                var target = Saveables.Find(s => s.SaveKey == entry.key);
                target?.RestoreState(entry.json);
            }

            return data;
        }

        public static void Delete(int slot)
        {
            string path = GetPath(slot);
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }
}
