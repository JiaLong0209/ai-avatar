using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Singleton manager for motion playback operations.
/// Provides centralized access to MotionPlayback components and coordinates motion operations.
/// </summary>
public class MotionManager : MonoBehaviour
{
    public static MotionManager Instance { get; private set; }

    [Header("Settings")]
    [SerializeField] private bool autoCreateIfMissing = true;

    private readonly List<MotionPlayback> registeredPlaybacks = new List<MotionPlayback>();
    private MotionPlayback primaryPlayback;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    /// <summary>
    /// Ensures MotionManager exists in the scene, creates one if missing.
    /// </summary>
    public static MotionManager Ensure()
    {
        if (Instance != null) return Instance;
        
        var existing = FindFirstObjectByType<MotionManager>();
        if (existing != null)
        {
            Instance = existing;
            return Instance;
        }
        
        var go = new GameObject("MotionManager");
        var mgr = go.AddComponent<MotionManager>();
        return mgr;
    }

    /// <summary>
    /// Registers a MotionPlayback component with the manager.
    /// </summary>
    public void RegisterPlayback(MotionPlayback playback)
    {
        if (playback == null) return;
        
        if (!registeredPlaybacks.Contains(playback))
        {
            registeredPlaybacks.Add(playback);
            
            // Set as primary if it's the first one or explicitly marked
            if (primaryPlayback == null)
            {
                primaryPlayback = playback;
            }
            
            Debug.Log($"[MotionManager] Registered MotionPlayback: {playback.name}");
        }
    }

    /// <summary>
    /// Unregisters a MotionPlayback component from the manager.
    /// </summary>
    public void UnregisterPlayback(MotionPlayback playback)
    {
        if (playback == null) return;
        
        registeredPlaybacks.Remove(playback);
        
        if (primaryPlayback == playback)
        {
            primaryPlayback = registeredPlaybacks.Count > 0 ? registeredPlaybacks[0] : null;
        }
        
        Debug.Log($"[MotionManager] Unregistered MotionPlayback: {playback.name}");
    }

    /// <summary>
    /// Gets the primary MotionPlayback instance.
    /// </summary>
    public MotionPlayback GetPrimaryPlayback()
    {
        if (primaryPlayback != null) return primaryPlayback;
        
        // Try to find one in the scene
        primaryPlayback = FindFirstObjectByType<MotionPlayback>();
        
        if (primaryPlayback == null && autoCreateIfMissing)
        {
            Debug.LogWarning("[MotionManager] No MotionPlayback found. Consider adding one to the scene.");
        }
        
        return primaryPlayback;
    }

    /// <summary>
    /// Gets all registered MotionPlayback instances.
    /// </summary>
    public IReadOnlyList<MotionPlayback> GetAllPlaybacks()
    {
        return registeredPlaybacks.AsReadOnly();
    }

    /// <summary>
    /// Sets the primary MotionPlayback instance.
    /// </summary>
    public void SetPrimaryPlayback(MotionPlayback playback)
    {
        if (playback != null && registeredPlaybacks.Contains(playback))
        {
            primaryPlayback = playback;
            Debug.Log($"[MotionManager] Set primary MotionPlayback: {playback.name}");
        }
    }

    /// <summary>
    /// Plays an FBX motion file using the primary playback instance.
    /// </summary>
    public bool PlayMotion(string filePath)
    {
        var playback = GetPrimaryPlayback();
        if (playback == null)
        {
            Debug.LogError("[MotionManager] No MotionPlayback available to play motion.");
            return false;
        }

        playback.PlayFBX(filePath);
        return true;
    }
}

