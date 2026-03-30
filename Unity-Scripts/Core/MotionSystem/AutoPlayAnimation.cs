#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;

/// <summary>
/// Utility class for importing and playing FBX animation clips in the Unity Editor.
/// Handles asset import configuration and animator controller setup.
/// </summary>
public static class GeneratedFbxImporter
{
    private const string TEMP_CONTROLLER_PATH = "Assets/Animations/TempController.controller";

    /// <summary>
    /// Imports an FBX asset and plays its animation on the target animator.
    /// </summary>
    /// <param name="assetPath">Path to the FBX asset (e.g., "Assets/Animations/Generated/motion.fbx")</param>
    /// <param name="targetAnimator">Animator component to play the animation on</param>
    public static void ImportAndPlay(string assetPath, Animator targetAnimator)
    {
        if (string.IsNullOrEmpty(assetPath))
        {
            Debug.LogError("[GeneratedFbxImporter] Asset path is empty.");
            return;
        }

        // Configure model importer
        ConfigureModelImporter(assetPath);

        // Refresh asset database to ensure changes are recognized
        AssetDatabase.Refresh();
        AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);

        // Load animation clip
        var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
        if (clip == null)
        {
            Debug.LogError($"[GeneratedFbxImporter] No AnimationClip found at {assetPath}");
            return;
        }

        // Find animator if not provided
        if (targetAnimator == null)
        {
            targetAnimator = Object.FindFirstObjectByType<Animator>();
            if (targetAnimator == null)
            {
                Debug.LogWarning("[GeneratedFbxImporter] No Animator found to play the clip.");
                return;
            }
        }

        // Create or update animator controller
        var controller = GetOrCreateAnimatorController();
        if (controller == null)
        {
            Debug.LogError("[GeneratedFbxImporter] Failed to create animator controller.");
            return;
        }

        // Configure controller with the animation clip
        ConfigureAnimatorController(controller, clip);

        // Assign controller to animator and play
        targetAnimator.runtimeAnimatorController = controller;
        Debug.Log($"[GeneratedFbxImporter] Playing animation: {clip.name}");
    }

    /// <summary>
    /// Configures the ModelImporter for Humanoid animation.
    /// </summary>
    private static void ConfigureModelImporter(string assetPath)
    {
        var importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
        if (importer == null)
        {
            Debug.LogWarning($"[GeneratedFbxImporter] Could not get ModelImporter for: {assetPath}");
            return;
        }

        importer.animationType = ModelImporterAnimationType.Human;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        importer.SaveAndReimport();
    }

    /// <summary>
    /// Gets or creates the temporary animator controller.
    /// </summary>
    private static AnimatorController GetOrCreateAnimatorController()
    {
        var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(TEMP_CONTROLLER_PATH);
        
        if (controller == null)
        {
            // Ensure directory exists
            string directory = System.IO.Path.GetDirectoryName(TEMP_CONTROLLER_PATH);
            if (!AssetDatabase.IsValidFolder(directory))
            {
                AssetDatabase.CreateFolder("Assets", "Animations");
            }

            controller = AnimatorController.CreateAnimatorControllerAtPath(TEMP_CONTROLLER_PATH);
        }

        return controller;
    }

    /// <summary>
    /// Configures the animator controller with the animation clip.
    /// </summary>
    private static void ConfigureAnimatorController(AnimatorController controller, AnimationClip clip)
    {
        if (controller.layers.Length == 0)
        {
            Debug.LogError("[GeneratedFbxImporter] Animator controller has no layers.");
            return;
        }

        var stateMachine = controller.layers[0].stateMachine;

        // Clear existing states
        var states = stateMachine.states;
        foreach (var state in states)
        {
            stateMachine.RemoveState(state.state);
        }

        // Add new state with the clip
        var newState = stateMachine.AddState("Play");
        newState.motion = clip;

        // Set as default state
        stateMachine.defaultState = newState;
    }
}
#endif
