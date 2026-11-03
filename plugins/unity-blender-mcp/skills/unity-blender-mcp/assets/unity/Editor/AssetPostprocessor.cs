// MCP 资产管线：Unity 自动导入后处理
// 安装：放到 Unity 项目的 Assets/Editor/ 文件夹下（没有就新建），Unity 自动编译。
// 门控：默认只处理 Assets/Imports/ 下的资产，不影响项目其它内容。
// 移除：删除本文件即可，无其它副作用。
// 贴图后缀约定：_BC/_D/_Albedo=颜色(sRGB)  _N/_Normal/_NRM=法线
//   _M/_Mask/_RMA/_ORM/_R/_Metal/_AO/_Roughness=数据贴图(Linear)  _E/_Emissive=自发光  _HDR=HDR
// 角色约定：路径含 /Characters/ 或文件名以 SK_ 开头 → Humanoid。

using System.IO;
using UnityEditor;
using UnityEngine;

namespace McpAssetPipeline
{
    internal static class AssetGate
    {
        // 只处理该目录下的导入资产；需要改范围时改这里（以 / 结尾风格的路径）
        public const string GatedRoot = "Assets/Imports";

        public static bool UnderGate(string assetPath)
        {
            string p = assetPath.Replace('\\', '/');
            return p == GatedRoot || p.StartsWith(GatedRoot + "/");
        }
    }

    /// <summary>贴图：按文件名后缀自动设置类型、sRGB/Linear、Mipmap、循环。</summary>
    public class GatedTexturePostprocessor : AssetPostprocessor
    {
        private void OnPreprocessTexture()
        {
            if (!AssetGate.UnderGate(assetPath)) return;

            var t = assetImporter as TextureImporter;
            if (t == null) return;

            string n = Path.GetFileNameWithoutExtension(assetPath).ToLowerInvariant();

            bool isNormal = n.EndsWith("_n") || n.Contains("_normal") || n.EndsWith("_nrm");
            bool isData = IsDataMask(n);
            bool isHdr = n.EndsWith("_hdr");

            if (isNormal)
            {
                t.textureType = TextureImporterType.NormalMap;
                t.sRGBTexture = false;
            }
            else
            {
                t.textureType = TextureImporterType.Default;
                // 颜色/自发光走 sRGB；遮罩/金属/粗糙/AO 走 Linear
                t.sRGBTexture = !isData;
            }

            t.mipmapEnabled = true;                       // 3D 贴图开 Mipmap
            t.wrapMode = TextureWrapMode.Repeat;
            t.alphaIsTransparency = n.Contains("alpha") && !n.EndsWith("_bc");
            if (isHdr)
            {
                t.textureShape = TextureImporterShape.Texture2D;
            }

            // 常规游戏分辨率上限 2048，避免外来 4K/8K 贴图直接进包
            t.maxTextureSize = 2048;
            t.textureCompression = TextureImporterCompression.Compressed;

            Debug.Log($"[MCP管线] 贴图已设置: {assetPath} " +
                      $"(类型={t.textureType}, sRGB={t.sRGBTexture})");
        }

        private static bool IsDataMask(string n)
        {
            string[] dataSuffix =
            {
                "_m", "_mask", "_rma", "_orm", "_r", "_rough", "_roughness",
                "_metal", "_metallic", "_ao", "_occlusion", "_mr"
            };
            foreach (var s in dataSuffix)
                if (n.EndsWith(s) || n.Contains(s + "_"))
                    return true;
            return false;
        }
    }

    /// <summary>模型：统一缩放、法线、切线、Read/Write、碰撞、角色 Humanoid。</summary>
    public class GatedModelPostprocessor : AssetPostprocessor
    {
        private void OnPreprocessModel()
        {
            if (!AssetGate.UnderGate(assetPath)) return;

            var m = assetImporter as ModelImporter;
            if (m == null) return;

            string n = Path.GetFileNameWithoutExtension(assetPath).ToLowerInvariant();
            bool isCharacter = n.StartsWith("sk_") ||
                               assetPath.Replace('\\', '/').ToLowerInvariant().Contains("/characters/");

            m.globalScale = 1f;
            m.importNormals = ModelImporterNormals.Import;
            m.importTangents = ModelImporterTangents.CalculateMikk;
            m.isReadable = false;
            m.importBlendShapes = true;
            m.importCameras = false;
            m.importLights = false;
            // 碰撞交给 Collider 组件，不直接用网格碰撞
            m.addCollider = false;
            // 新编辑器使用 MaterialDescription 导入材质（URP/HDRP）
            m.materialImportMode = ModelImporterMaterialImport.ImportViaMaterialDescription;

            if (isCharacter)
            {
                m.animationType = ModelImporterAnimationType.Human;
                m.importAnimation = true;
            }
            else
            {
                m.animationType = ModelImporterAnimationType.None;
                m.importAnimation = false;
            }

            // 需要 Lightmap UV 时，可在具体模型上手动勾选（默认不自动生成，避免边界问题）
            m.generateSecondaryUV = false;

            Debug.Log($"[MCP管线] 模型已设置: {assetPath} " +
                      $"(Humanoid={isCharacter}, 动画={m.importAnimation})");
        }
    }

    /// <summary>菜单项：对 Assets/Imports 全部资产强制重新导入，让门控规则重跑一遍。</summary>
    public static class GatedReimportMenu
    {
        [MenuItem("Tools/MCP 管线/重新处理 Assets/Imports")]
        public static void ReimportGated()
        {
            string[] guids = AssetDatabase.FindAssets(string.Empty, new[] { AssetGate.GatedRoot });
            int count = 0;
            try
            {
                for (int i = 0; i < guids.Length; i++)
                {
                    string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                    if (EditorUtility.DisplayCancelableProgressBar(
                            "MCP 管线", path, (float)i / guids.Length))
                        break;
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                    count++;
                }
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                AssetDatabase.Refresh();
            }
            Debug.Log($"[MCP管线] 强制重处理完成，共 {count} 个资产");
        }
    }
}
