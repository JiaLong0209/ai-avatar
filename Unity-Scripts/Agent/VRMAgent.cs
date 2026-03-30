using UnityEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Sensors;
using System.Collections.Generic;
using UnityEngine.InputSystem; 

[RequireComponent(typeof(Animator))]
public class VRMAgent : Agent
{
    [Header("Targeting Settings")]
    public Animator targetAnimator; 
    
    [Header("Model Settings")]
    public float modelHeight = 1.6f; 
    public float rotationSpeed = 100f; // 降低旋轉速度以提高穩定性
    public float moveSpeed = 2f;      
    public float turnSpeed = 100f;    

    private Animator anim;
    private Transform hips;
    private Transform head;
    private Transform targetHead;

    private List<Transform> boneNodes = new List<Transform>();
    private List<Quaternion> idleRotations = new List<Quaternion>();
    
    // 用於記錄上一次動作以計算震盪懲罰
    private float[] previousActions = new float[36];

    public override void Initialize()
    {
        anim = GetComponent<Animator>();
        hips = anim.GetBoneTransform(HumanBodyBones.Hips);
        head = anim.GetBoneTransform(HumanBodyBones.Head);

        if (targetAnimator != null)
            targetHead = targetAnimator.GetBoneTransform(HumanBodyBones.Head);

        MapBones();
    }

    private void MapBones()
    {
        HumanBodyBones[] bonesToControl = {
            HumanBodyBones.Spine, HumanBodyBones.Chest, HumanBodyBones.UpperChest,
            HumanBodyBones.Neck, HumanBodyBones.Head,
            HumanBodyBones.LeftUpperArm, HumanBodyBones.LeftLowerArm,
            HumanBodyBones.RightUpperArm, HumanBodyBones.RightLowerArm,
            HumanBodyBones.LeftUpperLeg, HumanBodyBones.RightUpperLeg
        };

        boneNodes.Clear();
        idleRotations.Clear();
        foreach (var b in bonesToControl)
        {
            Transform t = anim.GetBoneTransform(b);
            if (t != null) {
                boneNodes.Add(t);
                idleRotations.Add(t.localRotation);
            }
        }
    }

    public override void OnEpisodeBegin()
    {
        anim.enabled = false;

        // 重置 Agent 位置
        float randomAngle = Random.Range(0f, Mathf.PI * 2f);
        Vector3 offset = new Vector3(Mathf.Cos(randomAngle), 0, Mathf.Sin(randomAngle)) * Random.Range(2.5f, 4.5f);
        transform.localPosition = offset;
        transform.localRotation = Quaternion.Euler(0, Random.Range(0, 360), 0);

        // 初始化骨骼：給予極小的隨機擾動，避免初始動作過大
        for (int i = 0; i < boneNodes.Count; i++)
        {
            boneNodes[i].localRotation = idleRotations[i] * Quaternion.Euler(Random.Range(-5f, 5f), Random.Range(-5f, 5f), Random.Range(-5f, 5f));
        }

        // 清空動作歷史
        System.Array.Clear(previousActions, 0, previousActions.Length);
    }

    public override void CollectObservations(VectorSensor sensor)
    {
        // 基礎狀態 (1 + 44)
        sensor.AddObservation(hips.localPosition.y / modelHeight);
        foreach (var bone in boneNodes)
            sensor.AddObservation(bone.localRotation);

        // 目標相關 (3 + 1)
        if (targetHead != null)
        {
            Vector3 toTargetHead = (targetHead.position - head.position).normalized;
            sensor.AddObservation(head.InverseTransformDirection(toTargetHead));
            float dist = Vector3.Distance(transform.position, targetAnimator.transform.position);
            sensor.AddObservation(Mathf.Clamp01(dist / 10f));
        }
        else
        {
            sensor.AddObservation(Vector3.zero);
            sensor.AddObservation(0f);
        }

        // 動作歷史 (36)：讓 Agent 學習如何平滑化動作
        foreach (var act in previousActions)
            sensor.AddObservation(act);
    }

    public override void OnActionReceived(ActionBuffers actions)
    {
        var continuousActions = actions.ContinuousActions;
        float actionMagnitudePenalty = 0f;
        float jitterPenalty = 0f;

        // 1. 骨骼旋轉控制 (Index 0 - 32)
        float poseAlignmentScore = 0f;
        for (int i = 0; i < boneNodes.Count; i++)
        {
            int idx = i * 3;
            // 將輸出縮放至更穩定的範圍 (-30~30度)
            float x = continuousActions[idx] * 30f;
            float y = continuousActions[idx + 1] * 30f;
            float z = continuousActions[idx + 2] * 30f;

            // 累積動作大小懲罰
            actionMagnitudePenalty += Mathf.Abs(continuousActions[idx]) + Mathf.Abs(continuousActions[idx+1]) + Mathf.Abs(continuousActions[idx+2]);

            // 累積震盪懲罰 (與前一次動作的差異)
            jitterPenalty += Mathf.Abs((continuousActions[idx] - previousActions[idx]) * 0.1f);

            Quaternion targetRotation = idleRotations[i] * Quaternion.Euler(x, y, z);
            boneNodes[i].localRotation = Quaternion.RotateTowards(boneNodes[i].localRotation, targetRotation, rotationSpeed * Time.fixedDeltaTime);

            float angleDiff = Quaternion.Angle(boneNodes[i].localRotation, idleRotations[i]);
            poseAlignmentScore += (1.0f - (angleDiff / 180f));
        }

        // 2. 位移與旋轉控制 (Index 33 - 35)
        float moveForward = continuousActions[33]; 
        float moveSide = continuousActions[34];    
        float rotateYaw = continuousActions[35];   

        transform.Rotate(Vector3.up * rotateYaw * turnSpeed * Time.fixedDeltaTime);
        Vector3 moveDir = new Vector3(moveSide, 0, moveForward) * moveSpeed * Time.fixedDeltaTime;
        transform.Translate(moveDir);

        // 3. 複合獎勵函數
        float stepReward = 0f;

        // 姿態維持獎勵 (基礎)
        stepReward += (poseAlignmentScore / boneNodes.Count) * 0.05f;

        // 目標引導獎勵
        if (targetAnimator != null)
        {
            float distance = Vector3.Distance(transform.position, targetAnimator.transform.position);
            // 鼓勵保持在 1.5m - 2.0m 的舒適社交距離
            if (distance >= 1.5f && distance <= 2.2f) stepReward += 0.1f;
            else if (distance < 1.0f) stepReward -= 0.05f; // 太近給予壓力

            Vector3 dirToTarget = (targetHead.position - head.position).normalized;
            float lookAtDot = Vector3.Dot(head.forward, dirToTarget);
            if (lookAtDot > 0.8f) stepReward += 0.02f * lookAtDot;
        }

        // --- 強制動作限制懲罰 ---
        // 懲罰動作幅度 (Energy Cost)
        stepReward -= 0.01f * actionMagnitudePenalty; 
        // 懲罰動作不連續性 (Smoothness Cost)
        stepReward -= 0.05f * jitterPenalty; 

        AddReward(stepReward);

        // 更新動作歷史
        for (int i = 0; i < 36; i++) previousActions[i] = continuousActions[i];

        // 失敗判定
        if (hips.position.y < modelHeight * 0.5f) {
            SetReward(-1f);
            EndEpisode();
        }
    }

    public override void Heuristic(in ActionBuffers actionsOut)
    {
        var continuousActions = actionsOut.ContinuousActions;
        for (int i = 0; i < 36; i++) continuousActions[i] = 0f;

        if (Keyboard.current != null)
        {
            if (Keyboard.current.wKey.isPressed) continuousActions[33] = 1f;
            if (Keyboard.current.sKey.isPressed) continuousActions[33] = -1f;
            if (Keyboard.current.aKey.isPressed) continuousActions[35] = -1f;
            if (Keyboard.current.dKey.isPressed) continuousActions[35] = 1f;
        }
    }
}

// Version 1

// using UnityEngine;
// using Unity.MLAgents;
// using Unity.MLAgents.Actuators;
// using Unity.MLAgents.Sensors;
// using System.Collections.Generic;

// public class VRMAgent : Agent
// {
//     [Header("(Target)")]
//     public Transform targetVRM;

//     private Animator anim;
    
//     // 儲存所有需要觀察與控制的骨骼節點 (對應 .bvh 結構)
//     private List<Transform> boneNodes = new List<Transform>();

//     // 核心根節點定義
//     private Transform hips;
//     private Transform head;
//     private float height = 700f;

//         // 在 OnActionReceived 或 Update 中打印
//     void Update() {
//         if (StepCount % 100 == 0) { // 每 100 步打印一次，避免洗版
//             Debug.Log($"Episode: {CompletedEpisodes} | Reward: {GetCumulativeReward():F2}");
//         }
//     }

//     private Vector3 initialPosition;

//     public override void Initialize()
//     {
//         anim = GetComponent<Animator>();
//         if (anim == null || !anim.isHuman)
//         {
//             Debug.LogError("物件必須包含 Animator 且設定為 Humanoid！");
//             return;
//         }

//         // --- 1. 根據 .bvh 結構自動抓取骨骼 ---
//         // 根節點 (Root)
//         hips = anim.GetBoneTransform(HumanBodyBones.Hips);
        
//         // 軀幹 (Spine Chain)
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.Spine));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.Chest));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.UpperChest));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.Neck));
//         head = anim.GetBoneTransform(HumanBodyBones.Head);
//         boneNodes.Add(head);

//         // 左臂 (Left Arm)
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftShoulder));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftUpperArm));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftLowerArm));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftHand));

//         // 右臂 (Right Arm)
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightShoulder));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightUpperArm));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightLowerArm));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightHand));

//         // 左腿 (Left Leg)
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftUpperLeg));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftLowerLeg));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.LeftFoot));

//         // 右腿 (Right Leg)
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightUpperLeg));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightLowerLeg));
//         boneNodes.Add(anim.GetBoneTransform(HumanBodyBones.RightFoot));

//         // 移除列表中可能存在的 null (部分 VRM 可能沒 UpperChest)
//         boneNodes.RemoveAll(item => item == null);
//     }

//     public override void OnEpisodeBegin()
//     {
//         anim.enabled = false;
        
//         // 讓 Agent 隨機出現在 Target 附近 3~5 公尺處
//         float randomAngle = Random.Range(0f, Mathf.PI * 2f);
//         Vector3 offset = new Vector3(Mathf.Cos(randomAngle), 0, Mathf.Sin(randomAngle)) * Random.Range(3f, 5f);
//         transform.localPosition = initialPosition + offset;

//         // 讓骨骼有更大的隨機性（模擬摔倒）
//         foreach (var bone in boneNodes)
//         {
//             bone.localRotation = Quaternion.Euler(Random.Range(-45, 45), Random.Range(-45, 45), Random.Range(-45, 45));
//         }
//     }


//     public override void CollectObservations(VectorSensor sensor)
//     {
//         // 1. Hips 高度正規化 (Height / 700)
//         // 這樣數值會落在 0.8~1.2 左右，對 AI 來說非常舒適
//         sensor.AddObservation(hips.localPosition.y / height); 
//         sensor.AddObservation(hips.localRotation); // Quaternion 永遠是 -1~1，不需處理

//         // 2. 骨骼旋轉 (不受模型大小影響，直接餵)
//         foreach (var bone in boneNodes)
//         {
//             sensor.AddObservation(bone.localRotation); 
//         }

//         // 3. 目標相對資訊
//         Vector3 relativePos = targetVRM.position - hips.position;
//         sensor.AddObservation(relativePos.normalized); // 方向向量已經是 -1~1
        
//         // 假設 3 倍身高外就不在意了 (3 * 700 = 2100)
//         float normalizedDist = Mathf.Clamp(relativePos.magnitude / (height * 3f), 0f, 1f);
//         sensor.AddObservation(normalizedDist); 
//     }


//     public override void OnActionReceived(ActionBuffers actions)
//     {
//         var contActions = actions.ContinuousActions;
//         int actionIndex = 0;

//         // 這裡我們讓 AI 控制每一根骨頭的旋轉
//         // 每個骨頭分配 3 個 Action (X, Y, Z 旋轉)
//         foreach (var bone in boneNodes)
//         {
//             if (actionIndex + 2 < contActions.Length)
//             {
//                 float x = contActions[actionIndex++] * 30f; // 限制旋轉幅度
//                 float y = contActions[actionIndex++] * 30f;
//                 float z = contActions[actionIndex++] * 30f;
                
//                 // 使用 Slerp 平滑過渡，避免模型爆炸
//                 bone.localRotation = Quaternion.Slerp(bone.localRotation, Quaternion.Euler(x, y, z), Time.fixedDeltaTime * 10f);
//             }
//         }

//         // --- 獎勵邏輯 (Rewards) ---
//         // 獎勵 1: Hips 保持在一定高度 (避免摔倒)
//         if (hips.position.y > 0.8f && hips.position.y < 1.2f) AddReward(0.01f);

//         // 獎勵 2: 頭部向上
//         AddReward(Vector3.Dot(head.up, Vector3.up) * 0.1f);


//         // 在 OnActionReceived 中加入
//         float distance = Vector3.Distance(hips.position, targetVRM.position);

//         // 理想社交距離：1.5 倍到 2.5 倍身高
//         if (distance > height * 1.5f && distance < height * 2.5f) {
//             AddReward(0.01f); 
//         } else if (distance <= height * 1.0f) {
//             AddReward(-0.01f); // 太近了（碰撞邊緣）
//         }
//         // B. 對視獎勵 (Look at Target)
//         Vector3 toTarget = (targetVRM.position - head.position).normalized;
//         float lookAtDot = Vector3.Dot(head.forward, toTarget); // 1 為正對, -1 為背對
//         if (lookAtDot > 0.8f) { // 大約正負 30 度內
//             AddReward(0.01f * lookAtDot); 
//         }
//     }
// }
