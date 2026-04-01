using UnityEngine;
using UnityEngine.InputSystem; // 必須引入新版輸入系統命名空間
using VRM;
using System.Collections;

public class VRMExpressionTest : MonoBehaviour
{
    private VRMBlendShapeProxy proxy;

    [Header("測試設定")]
    public BlendShapePreset testPreset = BlendShapePreset.Joy; 
    [Range(0, 1)] public float targetValue = 1.0f;           
    public float duration = 0.5f;                            

    void Start()
    {
        proxy = GetComponent<VRMBlendShapeProxy>();

        if (proxy == null)
        {
            Debug.LogError("找不到 VRMBlendShapeProxy！請掛載於 VRM 根物件。");
            return;
        }

        Debug.Log("新版 Input System 測試就緒：\n按下 [T] 鍵觸發表情\n按下 [R] 鍵重置表情");
    }

    void Update()
    {
        // 使用新版 Input System 的語法檢查按鍵
        if (Keyboard.current != null)
        {
            // 按下 T 鍵
            if (Keyboard.current.tKey.wasPressedThisFrame)
            {
                StopAllCoroutines();
                StartCoroutine(FadeExpression(testPreset, targetValue));
            }

            // 按下 R 鍵
            if (Keyboard.current.rKey.wasPressedThisFrame)
            {
                StopAllCoroutines();
                ResetAllExpressions();
            }
        }
    }

    IEnumerator FadeExpression(BlendShapePreset preset, float target)
    {
        float startValue = proxy.GetValue(preset);
        float elapsed = 0;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float currentValue = Mathf.Lerp(startValue, target, elapsed / duration);
            
            // 核心更新指令
            proxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(preset), currentValue);
            yield return null;
        }
        
        proxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset(preset), target);
        Debug.Log($"[VRM] 表情 {preset} 已變更為 {target}");
    }

    public void ResetAllExpressions()
    {
        // 取得所有 Clip 並歸零
        foreach (var clip in proxy.BlendShapeAvatar.Clips)
        {
            proxy.ImmediatelySetValue(clip.Key, 0);
        }
        Debug.Log("[VRM] 已重置所有表情數值。");
    }
}
