using UnityEngine;
using UnityEngine.InputSystem;

public class TPSCameraController : MonoBehaviour
{
    [Header("Target Settings")]
    public Transform target;            // 要跟隨的 Agent
    public bool followAgent = true;    // 是否開啟跟隨模式
    public Vector3 offset = new Vector3(0, 1.5f, -3.0f); // 初始偏移量

    [Header("Movement Settings")]
    public float smoothSpeed = 10f;    // 跟隨平滑度
    public float rotateSpeed = 0.2f;   // 旋轉靈敏度
    public float zoomSpeed = 0.5f;     // 縮放靈敏度
    public float minDistance = 1.0f;   // 最近縮放距離
    public float maxDistance = 10.0f;  // 最遠縮放距離

    [Header("Rotation Constraints")]
    public float minPitch = -20f;      // 俯角限制
    public float maxPitch = 80f;       // 仰角限制

    private float currentYaw = 0f;
    private float currentPitch = 0f;
    private float currentDistance;

    private void Start()
    {
        if (target == null)
        {
            Debug.LogWarning("[TPSCamera] 未指定 Target，請在 Inspector 拖入 Agent。");
            return;
        }

        // 初始化角度與距離
        currentDistance = offset.magnitude;
        Vector3 angles = transform.eulerAngles;
        currentYaw = angles.y;
        currentPitch = angles.x;
    }

    private void Update()
    {
        HandleInput();
    }

    private void LateUpdate()
    {
        if (!followAgent || target == null) return;

        UpdateCameraPosition();
    }

    private void HandleInput()
    {
        // 1. 切換跟隨模式 (G 鍵)
        if (Keyboard.current.gKey.wasPressedThisFrame)
        {
            followAgent = !followAgent;
            Debug.Log($"[TPSCamera] Follow Mode: {followAgent}");
        }

        // 2. 處理旋轉 (右鍵長按)
        if (Mouse.current.rightButton.isPressed)
        {
            Vector2 mouseDelta = Mouse.current.delta.ReadValue();
            currentYaw += mouseDelta.x * rotateSpeed;
            currentPitch -= mouseDelta.y * rotateSpeed;
            currentPitch = Mathf.Clamp(currentPitch, minPitch, maxPitch);
        }

        // 3. 處理縮放 (滑鼠滾輪)
        float scroll = Mouse.current.scroll.ReadValue().y;
        if (scroll != 0)
        {
            currentDistance -= scroll * zoomSpeed * 0.01f;
            currentDistance = Mathf.Clamp(currentDistance, minDistance, maxDistance);
        }
    }

    private void UpdateCameraPosition()
    {
        // 計算旋轉矩陣
        Quaternion rotation = Quaternion.Euler(currentPitch, currentYaw, 0);

        // 計算目標位置：Target 位置 + 旋轉後的偏移方向 * 當前距離
        // 注意：這裡不跟隨 Agent 的旋轉 (target.rotation)，只跟隨位置
        Vector3 negDistance = new Vector3(0.0f, 0.0f, -currentDistance);
        Vector3 position = rotation * negDistance + target.position + (Vector3.up * offset.y);

        // 平滑移動與應用旋轉
        transform.position = Vector3.Lerp(transform.position, position, smoothSpeed * Time.deltaTime);
        transform.rotation = rotation;
    }
}