using UnityEngine;
using System.IO;
#if UNITY_EDITOR
using UnityEditor;
#endif

/// <summary>
/// Handles playback of FBX motion files. Automatically registers with MotionManager.
/// </summary>
public class MotionPlayback : MonoBehaviour
{
    [Header("Animation Target")]
    [SerializeField] private Animator targetAnimator;

    [Header("Settings")]
    [SerializeField] private bool registerWithManager = true;
    [SerializeField] private bool isPrimary = false;

    private void Awake()
    {
        if (targetAnimator == null)
        {
            targetAnimator = GetComponent<Animator>();
        }

        if (registerWithManager)
        {
            RegisterWithManager();
        }
    }

    private void OnDestroy()
    {
        if (MotionManager.Instance != null)
        {
            MotionManager.Instance.UnregisterPlayback(this);
        }
    }

    /// <summary>
    /// Registers this playback instance with MotionManager.
    /// </summary>
    public void RegisterWithManager()
    {
        var manager = MotionManager.Ensure();
        manager.RegisterPlayback(this);

        if (isPrimary)
        {
            manager.SetPrimaryPlayback(this);
        }
    }

    /// <summary>
    /// Plays an FBX motion file.
    /// </summary>
    /// <param name="sourcePath">Absolute path to the FBX file</param>
    public void PlayFBX(string sourcePath)
    {
        if (string.IsNullOrEmpty(sourcePath))
        {
            Debug.LogWarning("[MotionPlayback] Cannot play motion: source path is empty.");
            return;
        }

        if (!File.Exists(sourcePath))
        {
            Debug.LogError($"[MotionPlayback] Motion file not found: {sourcePath}");
            return;
        }

#if UNITY_EDITOR
        PlayFBXInEditor(sourcePath);
#else
        Debug.LogWarning("[MotionPlayback] Runtime FBX import is not supported outside the Unity Editor.");
#endif
    }

#if UNITY_EDITOR
    /// <summary>
    /// Handles FBX playback in Unity Editor.
    /// </summary>
    private void PlayFBXInEditor(string sourcePath)
    {
        string projectDir = Application.dataPath;
        string generatedDir = Path.Combine(projectDir, "Animations/Generated");
        Directory.CreateDirectory(generatedDir);

        string fileName = Path.GetFileName(sourcePath);
        string destAbs = Path.Combine(generatedDir, fileName);

        // Copy file to project directory if it's not already there
        if (sourcePath != destAbs)
        {
            File.Copy(sourcePath, destAbs, overwrite: true);
            Debug.Log($"[MotionPlayback] Copied FBX to project: {destAbs}");
        }

        // Convert absolute to AssetDatabase path
        string assetPath = "Assets/Animations/Generated/" + fileName;

        // Configure model importer
        ConfigureModelImporter(assetPath);

        // Play the animation
        GeneratedFbxImporter.ImportAndPlay(assetPath, targetAnimator);
    }

    /// <summary>
    /// Configures the ModelImporter for Humanoid animation.
    /// </summary>
    private void ConfigureModelImporter(string assetPath)
    {
        ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
        if (importer == null)
        {
            Debug.LogWarning($"[MotionPlayback] Could not get ModelImporter for: {assetPath}");
            return;
        }

        importer.animationType = ModelImporterAnimationType.Human;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        importer.SaveAndReimport();
        
        Debug.Log($"[MotionPlayback] Configured ModelImporter for: {assetPath}");
    }
#endif

    /// <summary>
    /// Gets the target animator, finding one if not assigned.
    /// </summary>
    public Animator GetTargetAnimator()
    {
        if (targetAnimator == null)
        {
            targetAnimator = GetComponent<Animator>();
        }
        return targetAnimator;
    }

    /// <summary>
    /// Sets the target animator.
    /// </summary>
    public void SetTargetAnimator(Animator animator)
    {
        targetAnimator = animator;
    }
}


