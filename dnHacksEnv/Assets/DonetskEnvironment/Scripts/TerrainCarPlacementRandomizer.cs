using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Perception.Randomization.Parameters;
using UnityEngine.Perception.Randomization.Randomizers;
using UnityEngine.Perception.Randomization.Samplers;

/// <summary>
/// Each iteration: picks a random focus point on the terrain, scatters a random
/// number of car prefabs in a cluster around it (snapped to the ground via
/// raycast), and exposes the focus point so DroneCameraRandomizer can aim at it.
/// Cars are rejected on rooftops (non-terrain colliders) and steep slopes.
/// Must be ordered ABOVE DroneCameraRandomizer in the Scenario's randomizer list.
/// </summary>
[Serializable]
[AddRandomizerMenu("dnHacks/Terrain Car Placement Randomizer")]
public class TerrainCarPlacementRandomizer : Randomizer
{
    [Tooltip("Labeled car prefabs to scatter")]
    public CategoricalParameter<GameObject> carPrefabs;

    public FloatParameter carCount = new FloatParameter { value = new UniformSampler(8, 35) };
    public FloatParameter clusterRadius = new FloatParameter { value = new UniformSampler(35, 110) };

    [Tooltip("Terrain-local XZ bounds to sample focus points from (keep inside terrain edges)")]
    public Vector2 areaMin = new Vector2(200, 200);
    public Vector2 areaMax = new Vector2(4300, 3300);

    public float raycastHeight = 500f;

    [Tooltip("Minimum ground normal Y to accept a spawn point (1 = flat only)")]
    public float minGroundNormalY = 0.90f;

    public static Vector3 FocusPoint { get; private set; }

    /// <summary>Cars spawned for the current iteration, consumed by CarDatasetCapture.</summary>
    public static readonly List<GameObject> ActiveCars = new List<GameObject>();

    FloatParameter m_Unit = new FloatParameter { value = new UniformSampler(0f, 1f) };
    GameObject m_Container;

    protected override void OnIterationStart()
    {
        if (m_Container == null)
            m_Container = new GameObject("Spawned Cars");

        var fx = Mathf.Lerp(areaMin.x, areaMax.x, m_Unit.Sample());
        var fz = Mathf.Lerp(areaMin.y, areaMax.y, m_Unit.Sample());
        FocusPoint = RaycastGround(fx, fz, out var focusHit)
            ? focusHit.point
            : new Vector3(fx, 0f, fz);

        var target = (int)carCount.Sample();
        var radius = clusterRadius.Sample();
        int spawned = 0, attempts = 0;
        while (spawned < target && attempts < target * 10)
        {
            attempts++;
            var angle = m_Unit.Sample() * Mathf.PI * 2f;
            var dist = Mathf.Sqrt(m_Unit.Sample()) * radius;
            var x = Mathf.Clamp(FocusPoint.x + Mathf.Cos(angle) * dist, areaMin.x, areaMax.x);
            var z = Mathf.Clamp(FocusPoint.z + Mathf.Sin(angle) * dist, areaMin.y, areaMax.y);

            if (!RaycastGround(x, z, out var hit)) continue;
            if (!(hit.collider is TerrainCollider)) continue; // rooftop or building blocking
            if (hit.normal.y < minGroundNormalY) continue;    // too steep

            var yaw = m_Unit.Sample() * 360f;
            var car = UnityEngine.Object.Instantiate(carPrefabs.Sample(), hit.point,
                Quaternion.Euler(0f, yaw, 0f), m_Container.transform);
            ActiveCars.Add(car);
            spawned++;
        }
    }

    bool RaycastGround(float x, float z, out RaycastHit hit)
    {
        return Physics.Raycast(new Vector3(x, raycastHeight, z), Vector3.down,
            out hit, raycastHeight * 2f);
    }

    protected override void OnIterationEnd()
    {
        ActiveCars.Clear();
        if (m_Container == null) return;
        for (var i = m_Container.transform.childCount - 1; i >= 0; i--)
            UnityEngine.Object.Destroy(m_Container.transform.GetChild(i).gameObject);
    }
}
