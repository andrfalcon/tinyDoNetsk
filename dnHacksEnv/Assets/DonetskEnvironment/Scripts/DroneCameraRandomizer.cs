using System;
using UnityEngine;
using UnityEngine.Perception.Randomization.Parameters;
using UnityEngine.Perception.Randomization.Randomizers;
using UnityEngine.Perception.Randomization.Samplers;

/// <summary>
/// Each iteration: positions every camera tagged with DroneCameraRandomizerTag
/// at a random altitude and viewing angle, aimed at the car cluster placed by
/// TerrainCarPlacementRandomizer. Order this BELOW the car placement randomizer.
/// </summary>
[Serializable]
[AddRandomizerMenu("dnHacks/Drone Camera Randomizer")]
public class DroneCameraRandomizer : Randomizer
{
    [Tooltip("Camera altitude above the focus point, meters")]
    public FloatParameter altitude = new FloatParameter { value = new UniformSampler(60f, 140f) };

    [Tooltip("Camera pitch: 90 = straight down (nadir), lower = more oblique")]
    public FloatParameter pitchDegrees = new FloatParameter { value = new UniformSampler(55f, 90f) };

    FloatParameter m_Unit = new FloatParameter { value = new UniformSampler(0f, 1f) };

    protected override void OnIterationStart()
    {
        var focus = TerrainCarPlacementRandomizer.FocusPoint;
        foreach (var tag in tagManager.Query<DroneCameraRandomizerTag>())
        {
            var alt = altitude.Sample();
            var pitch = pitchDegrees.Sample() * Mathf.Deg2Rad;
            var heading = m_Unit.Sample() * Mathf.PI * 2f;
            var groundDist = alt / Mathf.Tan(pitch);
            tag.transform.position = focus + new Vector3(
                Mathf.Cos(heading) * groundDist, alt, Mathf.Sin(heading) * groundDist);
            tag.transform.LookAt(focus);
        }
    }
}
