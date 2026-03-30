using UnityEngine;
using UnityEngine.InputSystem; // new Input System

public class CameraController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 50f;
    [SerializeField] private float lookSensitivity = 3f;
    [SerializeField] private float scrollSpeed = 50f;

    private float xRot;
    private float yRot;

    void Start()
    {
        // Cursor.lockState = CursorLockMode.Locked;
    }

    void Update()
    {
        HandleLook();
        // HandleScroll();

        // Stop camera movement if user is typing in chat
        if (ChatUIManager.IsInputFocused) return;
        HandleMovement();
    }
    private void HandleLook()
    {
        if (Mouse.current.rightButton.isPressed)
        {
            // Lock and hide cursor while dragging
            if (Cursor.lockState != CursorLockMode.Locked)
            {
                Cursor.lockState = CursorLockMode.Locked;
                Cursor.visible = false;
            }

            Vector2 mouseDelta = Mouse.current.delta.ReadValue() * lookSensitivity * Time.deltaTime;
            yRot += mouseDelta.x;
            xRot -= mouseDelta.y;
            xRot = Mathf.Clamp(xRot, -90f, 90f);
            transform.rotation = Quaternion.Euler(xRot, yRot, 0f);
        }
        else
        {
            // Unlock and show cursor when released
            if (Cursor.lockState != CursorLockMode.None)
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
        }
    }

    private void HandleMovement()
    {
        Vector3 move = Vector3.zero;

        if (Keyboard.current.wKey.isPressed) move += transform.forward;
        if (Keyboard.current.sKey.isPressed) move -= transform.forward;
        if (Keyboard.current.aKey.isPressed) move -= transform.right;
        if (Keyboard.current.dKey.isPressed) move += transform.right;

        transform.position += move * moveSpeed * Time.deltaTime;
    }

    private void HandleScroll()
    {
        float scroll = Mouse.current.scroll.ReadValue().y; // scroll up/down
        if (Mathf.Abs(scroll) > 0.01f)
        {
            transform.position += transform.forward * scroll * scrollSpeed * Time.deltaTime;
        }
    }
}
