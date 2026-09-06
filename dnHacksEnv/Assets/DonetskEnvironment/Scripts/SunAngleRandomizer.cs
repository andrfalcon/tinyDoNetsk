using System;
using UnityEngine;
using UnityEngine.Perception.Randomization.Parameters;
using UnityEngine.Perception.Randomization.Randomizers;
using UnityEngine.Perception.Randomization.Samplers;

/// <summary>
/// Each iteration: randomizes the rotation and intensity of every light tagged
/// with SunAngleRandomizerTag, for time-of-day and shadow variety.
/// </summary>
[Serializable]
[AddRandomizerMenu("dnHacks/Sun Angle Randomizer")]
public class SunAngleRandomizer : Randomizer
{
    [Tooltip("Sun elevation above horizon, degrees")]
    public FloatParameter elevation = new FloatParameter { value = new UniformSampler(12f, 65f) };

    public FloatParameter azimuth = new FloatParameter { value = new UniformSampler(0f, 360f) };

    public FloatParameter intensity = new FloatParameter { value = new UniformSampler(0.8f, 1.4f) };

    protected override void OnIterationStart()
    {
        foreach (var tag in tagManager.Query<SunAngleRandomizerTag>())
        {
            tag.transform.rotation = Quaternion.Euler(elevation.Sample(), azimuth.Sample(), 0f);
            var light = tag.GetComponent<Light>();
            if (light != null)
                light.intensity = intensity.Sample();
        }
    }
}
