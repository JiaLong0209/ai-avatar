using UnityEngine;
using UnityEngine.InputSystem;

public enum CameraMode
{
    Free,
    Follow
}

public class CameraController : MonoBehaviour
{
    [Header("General Settings")]
    public CameraMode currentMode = CameraMode.Free;
    
    [Header("Target Settings (Follow Mode)")]
    public Transform target;
    public Vector3 targetOffset = new Vector3(0, 1.5f, 0);
    public float startingDistance = 3.0f;
    
    [Header("Movement Settings")]
    public float freeMoveSpeed = 6f;
    public float followSmoothSpeed = 10f;
    
    [Header("Rotation Settings")]
    public float lookSensitivity = 12f; // Used for Free mode
    public float rotateSpeed = 0.2f;    // Used for Follow mode
    
    [Header("Zoom Settings (Follow Mode)")]
    public float zoomSpeed = 0.5f;
    public float minDistance = 1.0f;
    public float maxDistance = 10.0f;

    [Header("Rotation Constraints (Follow Mode)")]
    public float minPitch = -90f;
    public float maxPitch = 90;

    // Tracking variables
    private float currentYaw = 0f;
    private float currentPitch = 0f;
    private float currentDistance;

    void Start()
    {
        // Initialize rotation and viewing distance tracking
        currentDistance = startingDistance;
        Vector3 angles = transform.eulerAngles;
        currentYaw = angles.y;
        currentPitch = angles.x;

        if (target == null && currentMode == CameraMode.Follow)
        {
            Debug.LogWarning("[CameraController] Follow mode active but target is unassigned!");
        }
    }

    void Update()
    {
        // Stop camera movement/actions if user is typing in chat
        if (ChatUIManager.IsInputFocused) return;

        HandleModeToggle();

        if (currentMode == CameraMode.Free)
        {
            HandleFreeLook();
            HandleFreeMovement();
        }
        else if (currentMode == CameraMode.Follow)
        {
            HandleFollowInput();
        }
    }

    private void LateUpdate()
    {
        if (currentMode == CameraMode.Follow && target != null)
        {
            UpdateFollowCameraPosition();
        }
    }

    private void HandleModeToggle()
    {
        // Toggle camera mode with 'C' key
        if (Keyboard.current.cKey.wasPressedThisFrame)
        {
            currentMode = currentMode == CameraMode.Free ? CameraMode.Follow : CameraMode.Free;
            Debug.Log($"[CameraController] Camera Mode Switched to: {currentMode}");
            
            // Re-sync angles when switching modes to prevent snapping back
            if (currentMode == CameraMode.Follow) {
                Vector3 angles = transform.eulerAngles;
                currentYaw = angles.y;
                currentPitch = angles.x;
            }
        }
    }

    #region Free Mode Implementation

    private void HandleFreeLook()
    {
        if (Mouse.current.rightButton.isPressed)
        {
            if (Cursor.lockState != CursorLockMode.Locked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }

            Vector2 mouseDelta = Mouse.current.delta.ReadValue() * lookSensitivity * Time.deltaTime;
            currentYaw += mouseDelta.x;
            currentPitch -= mouseDelta.y;
            currentPitch = Mathf.Clamp(currentPitch, -90f, 90f);
            
            transform.rotation = Quaternion.Euler(currentPitch, currentYaw, 0f);
        }
        else
        {
            if (Cursor.lockState != CursorLockMode.None)
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
        }
    }

    private void HandleFreeMovement()
    {
        Vector3 move = Vector3.zero;

        if (Keyboard.current.wKey.isPressed) move += transform.forward;
        if (Keyboard.current.sKey.isPressed) move -= transform.forward;
        if (Keyboard.current.aKey.isPressed) move -= transform.right;
        if (Keyboard.current.dKey.isPressed) move += transform.right;

        transform.position += move * freeMoveSpeed * Time.deltaTime;
    }

    #endregion

    #region Follow Mode Implementation

    private void HandleFollowInput()
    {
        // Rotation via right click
        if (Mouse.current.rightButton.isPressed)
        {
            Vector2 mouseDelta = Mouse.current.delta.ReadValue();
            currentYaw += mouseDelta.x * rotateSpeed;
            currentPitch -= mouseDelta.y * rotateSpeed;
            currentPitch = Mathf.Clamp(currentPitch, minPitch, maxPitch);
        }

        // Zoom via scroll wheel
        float scroll = Mouse.current.scroll.ReadValue().y;
        if (scroll != 0)
        {
            currentDistance -= scroll * zoomSpeed * 0.01f;
            currentDistance = Mathf.Clamp(currentDistance, minDistance, maxDistance);
        }
    }

    private void UpdateFollowCameraPosition()
    {
        Quaternion rotation = Quaternion.Euler(currentPitch, currentYaw, 0);
        Vector3 negDistance = new Vector3(0.0f, 0.0f, -currentDistance);
        
        Vector3 targetPos = target.position + targetOffset;
        Vector3 position = rotation * negDistance + targetPos;

        transform.position = Vector3.Lerp(transform.position, position, followSmoothSpeed * Time.deltaTime);
        transform.rotation = rotation;
    }

    #endregion
}
