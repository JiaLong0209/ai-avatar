using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

/// <summary>
/// Helper script to automatically set up MotionPlayback in the scene.
/// Can be used via menu item or attached to any GameObject.
/// </summary>
public class MotionPlaybackSetup : MonoBehaviour
{
#if UNITY_EDITOR
    [MenuItem("Tools/Motion System/Setup MotionPlayback")]
    public static void SetupMotionPlaybackFromMenu()
    {
        SetupMotionPlayback();
    }

    [MenuItem("Tools/Motion System/Setup MotionPlayback on Selected GameObject")]
    public static void SetupMotionPlaybackOnSelected()
    {
        GameObject selected = Selection.activeGameObject;
        if (selected == null)
        {
            EditorUtility.DisplayDialog("No Selection", 
                "Please select a GameObject first.", "OK");
            return;
        }

        SetupMotionPlaybackOnGameObject(selected);
    }

    /// <summary>
    /// Sets up MotionPlayback in the scene. Creates MotionManager if needed.
    /// </summary>
    public static void SetupMotionPlayback()
    {
        // First, ensure MotionManager exists
        MotionManager manager = FindFirstObjectByType<MotionManager>();
        if (manager == null)
        {
            GameObject managerObj = new GameObject("MotionManager");
            manager = managerObj.AddComponent<MotionManager>();
            Debug.Log("[MotionPlaybackSetup] Created MotionManager");
        }

        // Find existing MotionPlayback
        MotionPlayback existing = FindFirstObjectByType<MotionPlayback>();
        if (existing != null)
        {
            Debug.Log("[MotionPlaybackSetup] MotionPlayback already exists in scene.");
            Selection.activeGameObject = existing.gameObject;
            return;
        }

        // Find a GameObject with Animator (preferably the avatar/character)
        Animator animator = FindFirstObjectByType<Animator>();
        GameObject targetObject;

        if (animator != null)
        {
            targetObject = animator.gameObject;
            Debug.Log($"[MotionPlaybackSetup] Found Animator on: {targetObject.name}");
        }
        else
        {
            // Create a new GameObject for MotionPlayback
            targetObject = new GameObject("MotionPlayback");
            Debug.Log("[MotionPlaybackSetup] Created new GameObject for MotionPlayback");
            Debug.LogWarning("[MotionPlaybackSetup] No Animator found. Please add an Animator component to play animations.");
        }

        // Add MotionPlayback component
        MotionPlayback playback = targetObject.AddComponent<MotionPlayback>();
        
        // If we found an animator, assign it
        if (animator != null)
        {
            playback.SetTargetAnimator(animator);
        }

        // Mark as primary
        playback.RegisterWithManager();
        if (manager != null)
        {
            manager.SetPrimaryPlayback(playback);
        }

        // Select the object in hierarchy
        Selection.activeGameObject = targetObject;
        
        Debug.Log($"[MotionPlaybackSetup] ✅ MotionPlayback setup complete on: {targetObject.name}");
        EditorUtility.DisplayDialog("Setup Complete", 
            $"MotionPlayback has been added to {targetObject.name}.\n\n" +
            "If no Animator was found, please add one to play animations.", "OK");
    }

    /// <summary>
    /// Sets up MotionPlayback on a specific GameObject.
    /// </summary>
    public static void SetupMotionPlaybackOnGameObject(GameObject target)
    {
        if (target == null) return;

        // Check if MotionPlayback already exists
        MotionPlayback existing = target.GetComponent<MotionPlayback>();
        if (existing != null)
        {
            Debug.Log($"[MotionPlaybackSetup] MotionPlayback already exists on {target.name}");
            Selection.activeGameObject = target;
            return;
        }

        // Ensure MotionManager exists
        MotionManager manager = FindFirstObjectByType<MotionManager>();
        if (manager == null)
        {
            GameObject managerObj = new GameObject("MotionManager");
            manager = managerObj.AddComponent<MotionManager>();
        }

        // Add MotionPlayback component
        MotionPlayback playback = target.AddComponent<MotionPlayback>();

        // Try to find Animator on this GameObject or its children
        Animator animator = target.GetComponent<Animator>();
        if (animator == null)
        {
            animator = target.GetComponentInChildren<Animator>();
        }

        if (animator != null)
        {
            playback.SetTargetAnimator(animator);
            Debug.Log($"[MotionPlaybackSetup] Found Animator on {target.name}");
        }
        else
        {
            Debug.LogWarning($"[MotionPlaybackSetup] No Animator found on {target.name}. Please add one to play animations.");
        }

        // Register with manager
        playback.RegisterWithManager();
        if (manager != null)
        {
            manager.SetPrimaryPlayback(playback);
        }

        Selection.activeGameObject = target;
        Debug.Log($"[MotionPlaybackSetup] ✅ MotionPlayback added to: {target.name}");
    }

    /// <summary>
    /// Context menu item: Right-click on GameObject in hierarchy to add MotionPlayback
    /// </summary>
    [MenuItem("GameObject/Motion System/Add MotionPlayback", false, 10)]
    public static void AddMotionPlaybackContextMenu()
    {
        GameObject selected = Selection.activeGameObject;
        if (selected == null)
        {
            EditorUtility.DisplayDialog("No Selection", 
                "Please right-click on a GameObject in the hierarchy.", "OK");
            return;
        }

        SetupMotionPlaybackOnGameObject(selected);
    }

    [MenuItem("GameObject/Motion System/Add MotionPlayback", true)]
    public static bool ValidateAddMotionPlaybackContextMenu()
    {
        return Selection.activeGameObject != null;
    }
#endif

    /// <summary>
    /// Runtime method to set up MotionPlayback programmatically.
    /// Can be called from code at runtime.
    /// </summary>
    public static MotionPlayback SetupMotionPlaybackRuntime(GameObject target = null)
    {
        if (target == null)
        {
            // Try to find a GameObject with Animator
            Animator animator_temp = Object.FindFirstObjectByType<Animator>();
            if (animator_temp != null)
            {
                target = animator_temp.gameObject;
            }
            else
            {
                target = new GameObject("MotionPlayback");
            }
        }

        // Check if already has MotionPlayback
        MotionPlayback existing = target.GetComponent<MotionPlayback>();
        if (existing != null)
        {
            return existing;
        }

        // Add component
        MotionPlayback playback = target.AddComponent<MotionPlayback>();

        // Find Animator
        Animator animator = target.GetComponent<Animator>();
        if (animator == null)
        {
            animator = target.GetComponentInChildren<Animator>();
        }

        if (animator != null)
        {
            playback.SetTargetAnimator(animator);
        }

        // Register with manager
        playback.RegisterWithManager();

        Debug.Log($"[MotionPlaybackSetup] ✅ MotionPlayback setup at runtime on: {target.name}");
        return playback;
    }
}

