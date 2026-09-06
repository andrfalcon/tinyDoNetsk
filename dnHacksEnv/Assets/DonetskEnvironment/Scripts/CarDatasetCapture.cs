using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

/// <summary>
/// URP-compatible replacement for PerceptionCamera: each frame (after warmup),
/// renders this camera to a texture, saves a PNG, and writes YOLO-format
/// bounding boxes for every visible car spawned by TerrainCarPlacementRandomizer.
/// Output: &lt;project root&gt;/CarDataset/{images,labels}/NNNNNN.{png,txt} + dataset.yaml
/// Attach to the same camera as DroneCameraRandomizerTag. Stops play mode when done.
/// </summary>
[RequireComponent(typeof(Camera))]
public class CarDatasetCapture : MonoBehaviour
{
    public int imageWidth = 1280;
    public int imageHeight = 720;

    [Tooltip("Frames to skip at startup (shader warmup, first scenario iterations)")]
    public int warmupFrames = 5;

    public int totalCaptures = 1000;

    [Tooltip("Skip cars whose on-screen box is smaller than this (pixels)")]
    public float minBoxPixels = 8f;

    [Tooltip("Skip cars whose center is blocked by buildings/terrain")]
    public bool occlusionCheck = true;

    Camera m_Camera;
    RenderTexture m_RT;
    Texture2D m_Tex;
    int m_Frame;
    int m_Captured;
    string m_ImgDir, m_LblDir;

    void Start()
    {
        m_Camera = GetComponent<Camera>();
        var root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "CarDataset"));
        m_ImgDir = Path.Combine(root, "images");
        m_LblDir = Path.Combine(root, "labels");
        Directory.CreateDirectory(m_ImgDir);
        Directory.CreateDirectory(m_LblDir);
        File.WriteAllText(Path.Combine(root, "dataset.yaml"),
            $"path: {root}\ntrain: images\nval: images\nnc: 1\nnames: [car]\n");
        m_RT = new RenderTexture(imageWidth, imageHeight, 24);
        m_Tex = new Texture2D(imageWidth, imageHeight, TextureFormat.RGB24, false);
        Debug.Log($"[CarDatasetCapture] writing dataset to {root}");
    }

    void LateUpdate()
    {
        m_Frame++;
        if (m_Frame <= warmupFrames || m_Captured >= totalCaptures)
            return;
        StartCoroutine(CaptureEndOfFrame());
    }

    IEnumerator CaptureEndOfFrame()
    {
        yield return new WaitForEndOfFrame();
        if (m_Captured >= totalCaptures)
            yield break;

        var prevTarget = m_Camera.targetTexture;
        m_Camera.targetTexture = m_RT; // set before projecting so aspect matches output

        var lines = new List<string>();
        foreach (var car in TerrainCarPlacementRandomizer.ActiveCars)
        {
            if (car == null || !car.activeInHierarchy) continue;
            if (TryGetYoloBox(car, out var box))
                lines.Add(box);
        }

        m_Camera.Render();
        var prevActive = RenderTexture.active;
        RenderTexture.active = m_RT;
        m_Tex.ReadPixels(new Rect(0, 0, imageWidth, imageHeight), 0, 0);
        m_Tex.Apply();
        RenderTexture.active = prevActive;
        m_Camera.targetTexture = prevTarget;

        File.WriteAllBytes(Path.Combine(m_ImgDir, $"{m_Captured:D6}.png"), m_Tex.EncodeToPNG());
        File.WriteAllLines(Path.Combine(m_LblDir, $"{m_Captured:D6}.txt"), lines);
        m_Captured++;

        if (m_Captured % 50 == 0)
            Debug.Log($"[CarDatasetCapture] {m_Captured}/{totalCaptures}");
        if (m_Captured >= totalCaptures)
        {
            Debug.Log($"[CarDatasetCapture] done: {totalCaptures} images");
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#endif
        }
    }

    bool TryGetYoloBox(GameObject car, out string line)
    {
        line = null;

        if (occlusionCheck)
        {
            var probe = car.transform.position + Vector3.up * 0.8f;
            var toCam = m_Camera.transform.position - probe;
            // cars have no colliders, so any hit means a building or terrain is in the way
            if (Physics.Raycast(probe, toCam.normalized, toCam.magnitude - 0.5f))
                return false;
        }

        float minX = float.MaxValue, minY = float.MaxValue;
        float maxX = float.MinValue, maxY = float.MinValue;
        foreach (var renderer in car.GetComponentsInChildren<MeshRenderer>())
        {
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null) continue;
            var b = filter.sharedMesh.bounds; // tight local bounds -> oriented box in world
            var toWorld = renderer.localToWorldMatrix;
            for (var i = 0; i < 8; i++)
            {
                var corner = new Vector3(
                    (i & 1) == 0 ? b.min.x : b.max.x,
                    (i & 2) == 0 ? b.min.y : b.max.y,
                    (i & 4) == 0 ? b.min.z : b.max.z);
                var vp = m_Camera.WorldToViewportPoint(toWorld.MultiplyPoint3x4(corner));
                if (vp.z <= 0f) return false; // behind camera
                minX = Mathf.Min(minX, vp.x); maxX = Mathf.Max(maxX, vp.x);
                minY = Mathf.Min(minY, vp.y); maxY = Mathf.Max(maxY, vp.y);
            }
        }
        if (minX >= maxX) return false;

        // clip to frame
        minX = Mathf.Clamp01(minX); maxX = Mathf.Clamp01(maxX);
        minY = Mathf.Clamp01(minY); maxY = Mathf.Clamp01(maxY);
        var w = maxX - minX;
        var h = maxY - minY;
        if (w * imageWidth < minBoxPixels || h * imageHeight < minBoxPixels)
            return false; // off-frame or too small

        // YOLO: class cx cy w h, normalized, y measured from the top
        var cx = minX + w / 2f;
        var cy = 1f - (minY + h / 2f);
        line = string.Format(CultureInfo.InvariantCulture,
            "0 {0:F6} {1:F6} {2:F6} {3:F6}", cx, cy, w, h);
        return true;
    }

    void OnDestroy()
    {
        if (m_RT != null) m_RT.Release();
    }
}
