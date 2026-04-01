using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;

public class BvhRuntimePlayer : MonoBehaviour
{
    public Animator targetAnimator;
    
    [Header("Playback Options")]
    public bool isPlaying = false;
    public float playbackSpeed = 1.0f;
    public Action onPlaybackFinished;

    [Header("Axis Conversion")]
    public Vector3 positionMultiplier = new Vector3(-1, 1, -1); // Z=-1 to fix backwards run
    public Vector3 rotationMultiplier = new Vector3(1, -1, -1);
    public Vector3 positionOffset = Vector3.zero;

    public enum InterpolationMode { Linear, SmoothWindow }
    [Header("Interpolation Settings")]
    [Tooltip("Linear: strict keyframe interpolation. SmoothWindow: moving average to remove AI-generated jitter.")]

    public InterpolationMode interpolationMode = InterpolationMode.Linear;
    [Range(1, 15)] public int smoothingWindow = 5;

    [Header("Root Motion Settings")]
    [Tooltip("If true, X and Z movements are applied to the parent GameObject so colliders move. Otherwise, applied to Hips locally.")]
    public bool applyRootXZToGameObject = true;
    [Tooltip("If true, Y movement (jumping) is applied to the GameObject. Usually false so colliders stay on the ground.")]
    public bool applyRootYToGameObject = false;

    [Header("Pose Correction (T-Pose / A-Pose Fix)")]
    [Tooltip("Offset applied to the Left Upper Arm (e.g. 0, 0, 45) to prevent clipping into body")]
    public Vector3 leftArmOffset = new Vector3(0,0,-15);
    [Tooltip("Offset applied to the Right Upper Arm (e.g. 0, 0, -45) to prevent clipping into body")]
    public Vector3 rightArmOffset = new Vector3(0,0,15);

    private float currentFrameTime = 0f;
    private int currentFrame = 0;
    private BvhData bvhData;
    private Vector3 initialHipsPosition;
    private Vector3 initialGameObjectPos;
    private Vector3 initialBvhRootPos;

    // Mappings
    private Dictionary<string, Transform> boneMap = new Dictionary<string, Transform>();

    // Corresponds to the hierarchy in template.bvh
    private readonly Dictionary<string, HumanBodyBones> bvhToHumanMap = new Dictionary<string, HumanBodyBones>()
    {
        { "Hips", HumanBodyBones.Hips },
        { "Spine", HumanBodyBones.Spine },
        { "Spine1", HumanBodyBones.Chest },
        { "Spine2", HumanBodyBones.UpperChest },
        { "Neck", HumanBodyBones.Neck },
        { "Head", HumanBodyBones.Head },
        
        { "LeftShoulder", HumanBodyBones.LeftShoulder },
        { "LeftArm", HumanBodyBones.LeftUpperArm },
        { "LeftForeArm", HumanBodyBones.LeftLowerArm },
        { "LeftHand", HumanBodyBones.LeftHand },
        
        { "RightShoulder", HumanBodyBones.RightShoulder },
        { "RightArm", HumanBodyBones.RightUpperArm },
        { "RightForeArm", HumanBodyBones.RightLowerArm },
        { "RightHand", HumanBodyBones.RightHand },

        { "LeftUpLeg", HumanBodyBones.LeftUpperLeg },
        { "LeftLeg", HumanBodyBones.LeftLowerLeg },
        { "LeftFoot", HumanBodyBones.LeftFoot },
        { "LeftToe", HumanBodyBones.LeftToes },

        { "RightUpLeg", HumanBodyBones.RightUpperLeg },
        { "RightLeg", HumanBodyBones.RightLowerLeg },
        { "RightFoot", HumanBodyBones.RightFoot },
        { "RightToe", HumanBodyBones.RightToes }
    };

    public void Initialize(Animator animator)
    {
        targetAnimator = animator;
        BuildBoneMap();
    }

    private void BuildBoneMap()
    {
        boneMap.Clear();
        if (targetAnimator == null) return;

        foreach (var kvp in bvhToHumanMap)
        {
            Transform boneTransform = targetAnimator.GetBoneTransform(kvp.Value);
            if (boneTransform != null)
            {
                boneMap[kvp.Key] = boneTransform;
            }
        }
    }

    public void LoadAndPlay(string bvhContent)
    {
        try
        {
            bvhData = ParseBVH(bvhContent);
            currentFrame = 0;
            currentFrameTime = 0f;
            
            // Re-capture initial positions
            if (targetAnimator != null)
            {
                initialGameObjectPos = targetAnimator.transform.position;
            }

            if (boneMap.TryGetValue("Hips", out Transform hips))
            {
                initialHipsPosition = hips.localPosition;
            }

            // Capture BVH frame 0 root position
            if (bvhData.frames.Count > 0 && bvhData.nodes.Count > 0 && bvhData.nodes[0].hasPosition)
            {
                float[] frame0 = bvhData.frames[0];
                initialBvhRootPos = new Vector3(frame0[0], frame0[1], frame0[2]);
            }
            else
            {
                initialBvhRootPos = Vector3.zero;
            }

            isPlaying = true;
        }
        catch (Exception e)
        {
            Debug.LogError($"[BvhRuntimePlayer] Error parsing BVH: {e.Message}");
        }
    }

    public void Stop()
    {
        isPlaying = false;
        currentFrame = 0;
    }

    void Update()
    {
        if (!isPlaying || bvhData == null || bvhData.frames.Count == 0)
            return;

        currentFrameTime += Time.deltaTime * playbackSpeed;
        
        // Calculate which frame we are on and the fractional blend between frames
        float rawFrameIndex = currentFrameTime / bvhData.frameTime;
        currentFrame = Mathf.FloorToInt(rawFrameIndex);
        float t = rawFrameIndex - currentFrame;
        
        if (currentFrame >= bvhData.frames.Count - 1)
        {
            // Reached the end
            currentFrame = bvhData.frames.Count - 1;
            ApplyFrameInterpolated(currentFrame, currentFrame, 0f);
            isPlaying = false;
            onPlaybackFinished?.Invoke();
            return;
        }

        // Apply interpolated frame
        ApplyFrameInterpolated(currentFrame, currentFrame + 1, t);
    }

    private void ApplyFrameInterpolated(int frameA, int frameB, float t)
    {
        if (frameA < 0 || frameA >= bvhData.frames.Count) return;
        if (frameB < 0 || frameB >= bvhData.frames.Count) frameB = frameA;

        float[] dataA = bvhData.frames[frameA];
        float[] dataB = bvhData.frames[frameB];
        foreach (var node in bvhData.nodes)
        {
            Vector3 pos;
            Quaternion rot;

            if (interpolationMode == InterpolationMode.SmoothWindow)
            {
                int halfWindow = smoothingWindow / 2;
                int startF = Mathf.Max(0, currentFrame - halfWindow);
                int endF = Mathf.Min(bvhData.frames.Count - 1, currentFrame + halfWindow);
                
                Vector3 posSum = Vector3.zero;
                Vector4 qSum = Vector4.zero;
                int count = 0;
                
                Quaternion qBase = Quaternion.identity;

                for (int i = startF; i <= endF; i++)
                {
                    GetNodeLocal(i, node, out Vector3 p, out Quaternion q);
                    posSum += p;
                    
                    if (count == 0) qBase = q;
                    if (Quaternion.Dot(qBase, q) < 0) q = new Quaternion(-q.x, -q.y, -q.z, -q.w);
                    qSum += new Vector4(q.x, q.y, q.z, q.w);
                    
                    count++;
                }

                pos = posSum / count;
                rot = new Quaternion(qSum.x, qSum.y, qSum.z, qSum.w).normalized;
            }
            else
            {
                GetNodeLocal(frameA, node, out Vector3 posA, out Quaternion rotA);
                GetNodeLocal(frameB, node, out Vector3 posB, out Quaternion rotB);
                pos = Vector3.Lerp(posA, posB, t);
                rot = Quaternion.Slerp(rotA, rotB, t);
            }

            // Apply to mapped bone
            if (boneMap.TryGetValue(node.name, out Transform bone))
            {
                if (node.hasPosition) // Apply root motion to Hips
                {
                    Vector3 deltaBvh = pos - initialBvhRootPos;
                    
                    Vector3 deltaUnity = new Vector3(
                        deltaBvh.x * positionMultiplier.x,
                        deltaBvh.y * positionMultiplier.y,
                        deltaBvh.z * positionMultiplier.z
                    ) + positionOffset;

                    Vector3 localHipsMovement = Vector3.zero;
                    Vector3 gameObjectMovement = Vector3.zero;

                    if (applyRootXZToGameObject)
                    {
                        gameObjectMovement.x = deltaUnity.x;
                        gameObjectMovement.z = deltaUnity.z;
                    }
                    else
                    {
                        localHipsMovement.x = deltaUnity.x;
                        localHipsMovement.z = deltaUnity.z;
                    }

                    if (applyRootYToGameObject)
                    {
                        gameObjectMovement.y = deltaUnity.y;
                    }
                    else
                    {
                        localHipsMovement.y = deltaUnity.y;
                    }

                    if (targetAnimator != null && gameObjectMovement != Vector3.zero)
                    {
                        targetAnimator.transform.position = initialGameObjectPos + gameObjectMovement;
                    }
                    
                    bone.localPosition = initialHipsPosition + localHipsMovement;
                }

                Quaternion finalRot = rot;

                // T-Pose vs A-Pose adjustments. BVH generation often uses A-pose (arms down 45 deg)
                // while VRM requires T-pose (arms straight out).
                if (node.name == "LeftArm" && leftArmOffset != Vector3.zero)
                {
                    finalRot = rot * Quaternion.Euler(leftArmOffset);
                }
                else if (node.name == "RightArm" && rightArmOffset != Vector3.zero)
                {
                    finalRot = rot * Quaternion.Euler(rightArmOffset);
                }

                bone.localRotation = finalRot;
            }
        }
    }

    private void GetNodeLocal(int frame, BvhNode node, out Vector3 pos, out Quaternion rot)
    {
        float[] frameData = bvhData.frames[frame];
        int dataIndex = node.dataOffset;
        
        pos = Vector3.zero;
        if (node.hasPosition)
        {
            pos.x = frameData[dataIndex++];
            pos.y = frameData[dataIndex++];
            pos.z = frameData[dataIndex++];
        }

        Vector3 euler = Vector3.zero;
        euler.z = frameData[dataIndex++];
        euler.y = frameData[dataIndex++];
        euler.x = frameData[dataIndex++];

        euler.x *= rotationMultiplier.x;
        euler.y *= rotationMultiplier.y;
        euler.z *= rotationMultiplier.z;

        rot = Quaternion.Euler(euler);
    }

    #region Minimal BVH Parser
    private class BvhNode
    {
        public string name;
        public bool hasPosition;
        public int dataOffset;
    }

    private class BvhData
    {
        public List<BvhNode> nodes = new List<BvhNode>();
        public List<float[]> frames = new List<float[]>();
        public float frameTime = 0.016667f; // default 60fps
    }

    private BvhData ParseBVH(string content)
    {
        BvhData data = new BvhData();
        StringReader reader = new StringReader(content);
        string line;
        bool inMotion = false;

        int currentOffset = 0;

        while ((line = reader.ReadLine()) != null)
        {
            line = line.Trim();
            if (string.IsNullOrEmpty(line)) continue;

            if (line == "MOTION")
            {
                inMotion = true;
                continue;
            }

            if (!inMotion)
            {
                if (line.StartsWith("ROOT") || line.StartsWith("JOINT"))
                {
                    string[] parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 2)
                    {
                        data.nodes.Add(new BvhNode { name = parts[1] });
                    }
                }
                else if (line.StartsWith("CHANNELS"))
                {
                    // "CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation"
                    string[] parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 2)
                    {
                        int chanCount = int.Parse(parts[1]);
                        if (data.nodes.Count > 0)
                        {
                            var node = data.nodes[data.nodes.Count - 1];
                            node.hasPosition = (chanCount == 6);
                            node.dataOffset = currentOffset;
                            currentOffset += chanCount;
                        }
                    }
                }
            }
            else
            {
                if (line.StartsWith("Frames:"))
                {
                    // pass
                }
                else if (line.StartsWith("Frame Time:"))
                {
                    string[] parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 3) data.frameTime = float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture);
                }
                else
                {
                    // Frame data
                    string[] parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    float[] frame = new float[parts.Length];
                    for (int i = 0; i < parts.Length; i++)
                    {
                        float.TryParse(parts[i], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out frame[i]);
                    }
                    data.frames.Add(frame);
                }
            }
        }

        return data;
    }
    #endregion
}
