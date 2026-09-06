using System.IO;
using UnityEditor;
using UnityEngine;


/// <summary>
/// Menu item that turns every car model in Assets/DonetskEnvironment/Cars into
/// a prefab with a Labeling component ("car"), ready for the placement randomizer.
/// </summary>
public static class CreateCarPrefabs
{
    const string k_ModelFolder = "Assets/DonetskEnvironment/Cars";
    const string k_PrefabFolder = "Assets/DonetskEnvironment/CarPrefabs";

    [MenuItem("dnHacks/Create Labeled Car Prefabs")]
    public static void Create()
    {
        if (!AssetDatabase.IsValidFolder(k_PrefabFolder))
            AssetDatabase.CreateFolder("Assets/DonetskEnvironment", "CarPrefabs");

        var guids = AssetDatabase.FindAssets("t:Model", new[] { k_ModelFolder });
        var count = 0;
        foreach (var guid in guids)
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (model == null) continue;

            var instance = (GameObject)PrefabUtility.InstantiatePrefab(model);
            var labeling = instance.AddComponent<UnityEngine.Perception.GroundTruth.LabelManagement.Labeling>();
            labeling.labels.Add("car");
            var name = Path.GetFileNameWithoutExtension(path);
            PrefabUtility.SaveAsPrefabAsset(instance, $"{k_PrefabFolder}/{name}.prefab");
            Object.DestroyImmediate(instance);
            count++;
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"Created {count} labeled car prefabs in {k_PrefabFolder}");
    }
}
