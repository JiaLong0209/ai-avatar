using UnityEngine;
using System.IO;
using System.Collections;
#if UNITY_EDITOR
using UnityEditor;
#endif

public enum MotionState
{
    Idle,
    PlayingFBX,
    AgentControlled
}

/// <summary>
/// Handles playback of FBX motion files and manages state transitions (Idle, Playing, AgentControlled).
/// Automatically registers with MotionManager.
/// </summary>
public class MotionPlayback : MonoBehaviour
{
    [Header("Animation Target")]
    [SerializeField] private Animator targetAnimator;

    [Header("Manager Settings")]
    [SerializeField] private bool registerWithManager = true;
    [SerializeField] private bool isPrimary = false;

    [Header("Idle Settings")]
    [Tooltip("Assign an Animator Controller that contains the default Idle state.")]
    public RuntimeAnimatorController defaultIdleController;
    
    [HideInInspector] // Hidden because we shouldn't use Editor importers at runtime
    public string defaultIdleFBXPath = "Assets/Animations/Default/Standard Idle.fbx";
    public bool useMLAgentForIdle = false;
    
    [Header("Runtime Player")]
    [SerializeField] private BvhRuntimePlayer bvhPlayer;

    [Header("ML-Agent Target (Future)")]
    // Reference to the VRMAgent script to enable/disable it
    // Using MonoBehaviour to avoid hard dependency compilation errors if script is moved
    [SerializeField] private MonoBehaviour vrmAgentScript; 

    // Current State
    public MotionState CurrentState { get; private set; } = MotionState.Idle;

    private Coroutine monitorCoroutine;

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

        if (bvhPlayer == null)
        {
            bvhPlayer = gameObject.AddComponent<BvhRuntimePlayer>();
            bvhPlayer.Initialize(targetAnimator);
        }
        bvhPlayer.onPlaybackFinished = ReturnToIdle;
    }

    private void Start()
    {
        // Cache initial animator controller if user didn't assign one
        if (defaultIdleController == null && targetAnimator != null)
        {
            defaultIdleController = targetAnimator.runtimeAnimatorController;
        }

        // On start, enter idle state properly
        ReturnToIdle();
    }

    private void OnDestroy()
    {
        if (MotionManager.Instance != null)
        {
            MotionManager.Instance.UnregisterPlayback(this);
        }
    }

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
    /// Plays a motion file (FBX or BVH) and tracks its completion.
    /// </summary>
    public void PlayMotion(string sourcePath)
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

        // 1. Disable Agent if it was controlling
        SetAgentControl(false);

        // 2. State change
        CurrentState = MotionState.PlayingFBX;

        // 3. Play the motion based on extension
        string ext = Path.GetExtension(sourcePath).ToLower();
        
        if (ext == ".bvh")
        {
            // Fully runtime supported BVH playback
            if (monitorCoroutine != null) StopCoroutine(monitorCoroutine);
            targetAnimator.enabled = false; // Disable standard animator to allow manual bone manipulation
            bvhPlayer.LoadAndPlay(File.ReadAllText(sourcePath));
        }
        else
        {
            // Legacy / Editor FBX playback
            targetAnimator.enabled = true;

#if UNITY_EDITOR
            PlayFBXInEditor(sourcePath);
#else
            Debug.LogWarning("[MotionPlayback] Runtime FBX import is not supported outside the Unity Editor.");
#endif

            // 4. Start monitoring FBX completion
            if (monitorCoroutine != null) StopCoroutine(monitorCoroutine);
            monitorCoroutine = StartCoroutine(MonitorAnimationCompletion());
        }
    }

    private IEnumerator MonitorAnimationCompletion()
    {
        // Wait a tiny bit for the animator state to transition to the new clip
        yield return new WaitForSeconds(0.1f);

        if (targetAnimator != null)
        {
            // Wait until the current active animation finishes (normalized time >= 1)
            // Assumes it's playing on layer 0.
            while (targetAnimator.GetCurrentAnimatorStateInfo(0).normalizedTime < 1.0f)
            {
                // If another motion interrupted this one, state might change, abort coroutine
                if (CurrentState != MotionState.PlayingFBX) yield break;

                yield return null;
            }
        }

        // Animation finished, return to idle logic
        ReturnToIdle();
    }

    /// <summary>
    /// Logic to return the avatar to an idle state (either a default looping FBX or ML-Agent).
    /// </summary>
    private void ReturnToIdle()
    {
        // Ensure standard animator is re-enabled if returning from BVH runtime playback
        if (targetAnimator != null && !useMLAgentForIdle)
        {
            targetAnimator.enabled = true;
        }

        if (useMLAgentForIdle)
        {
            CurrentState = MotionState.AgentControlled;
            SetAgentControl(true);
            Debug.Log("[MotionPlayback] Returned to Idle: Agent Control Enabled.");
        }
        else
        {
            CurrentState = MotionState.Idle;
            SetAgentControl(false);
            
            // Re-play the default idle controller to avoid Editor Importer progress bars
            if (defaultIdleController != null && targetAnimator != null)
            {
                targetAnimator.runtimeAnimatorController = defaultIdleController;
                targetAnimator.Play(0, 0, 0f);
                Debug.Log($"[MotionPlayback] Returned to Idle: Assigned default controller.");
            }
            else if (!string.IsNullOrEmpty(defaultIdleFBXPath) && File.Exists(defaultIdleFBXPath))
            {
                Debug.Log($"[MotionPlayback] Returned to Idle: Playing fallback FBX: {defaultIdleFBXPath}");
#if UNITY_EDITOR
                PlayFBXInEditor(defaultIdleFBXPath, isLoopingIdle: true);
#endif
            }
            else
            {
                Debug.Log("[MotionPlayback] Returned to Idle: No valid Default Idle path found. Doing nothing.");
            }
        }
    }

    /// <summary>
    /// Helper to cleanly toggle the VRMAgent on/off.
    /// In the future, this turns the ML-Agent behavior loose on the bones.
    /// </summary>
    private void SetAgentControl(bool enable)
    {
        if (vrmAgentScript != null)
        {
            vrmAgentScript.enabled = enable;
        }
        
        // Disable the standard Animator if the agent takes over bone control
        if (targetAnimator != null)
        {
            targetAnimator.enabled = !enable;
        }
    }

#if UNITY_EDITOR
    /// <summary>
    /// Handles FBX playback in Unity Editor.
    /// </summary>
    private void PlayFBXInEditor(string sourcePath, bool isLoopingIdle = false)
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

        // Configure model importer with loop settings if it's the idle clip
        ConfigureModelImporter(assetPath, isLoopingIdle);

        // Play the animation
        GeneratedFbxImporter.ImportAndPlay(assetPath, targetAnimator);
    }

    /// <summary>
    /// Configures the ModelImporter for Humanoid animation.
    /// </summary>
    private void ConfigureModelImporter(string assetPath, bool forceLoopTime = false)
    {
        ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
        if (importer == null)
        {
            Debug.LogWarning($"[MotionPlayback] Could not get ModelImporter for: {assetPath}");
            return;
        }

        importer.animationType = ModelImporterAnimationType.Human;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;

        if (forceLoopTime)
        {
            var modelAnimArgs = importer.defaultClipAnimations;
            if (modelAnimArgs.Length > 0)
            {
                modelAnimArgs[0].loopTime = true;
                importer.clipAnimations = modelAnimArgs;
            }
        }

        importer.SaveAndReimport();
        
        Debug.Log($"[MotionPlayback] Configured ModelImporter for: {assetPath} (Loop: {forceLoopTime})");
    }
#endif

    public Animator GetTargetAnimator()
    {
        if (targetAnimator == null)
            targetAnimator = GetComponent<Animator>();
        return targetAnimator;
    }

    public void SetTargetAnimator(Animator animator)
    {
        targetAnimator = animator;
    }
}


