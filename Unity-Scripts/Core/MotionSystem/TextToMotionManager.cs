using UnityEngine;
using System.Collections;
using UnityEngine.Networking;
using System.IO;

/// <summary>
/// Manages text-to-motion generation and playback.
/// Handles communication with the backend T2M API and coordinates with MotionManager.
/// </summary>
public class TextToMotionManager : MonoBehaviour
{
    [Header("Backend Settings")]
    [SerializeField] private string serverUrl = "http://localhost:8000/t2m";
    
    [Header("Motion Management")]
    [SerializeField] private MotionManager motionManager;
    [SerializeField] private bool autoFindMotionManager = true;

    [Header("File Settings")]
    [SerializeField] private bool saveTempFiles = true;

    private void Start()
    {
        InitializeMotionManager();
    }

    private void InitializeMotionManager()
    {
        if (motionManager == null && autoFindMotionManager)
        {
            motionManager = MotionManager.Instance ?? MotionManager.Ensure();
        }
    }

    /// <summary>
    /// Generates and plays motion from text description.
    /// </summary>
    public void GenerateAndPlay(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            Debug.LogWarning("[TextToMotionManager] Cannot generate motion: text is empty.");
            return;
        }

        StartCoroutine(SendTextAndPlayMotion(text));
    }

    private IEnumerator SendTextAndPlayMotion(string text)
    {
        Debug.Log($"[TextToMotionManager] Generating motion from text: {text}");

        // Backend expects form field 'text' and optional format=fbx
        WWWForm form = new WWWForm();
        form.AddField("text", text);
        form.AddField("format", "fbx");
        form.AddField("save_temp_files", saveTempFiles.ToString().ToLower());

        using (var request = UnityWebRequest.Post(serverUrl, form))
        {
            request.downloadHandler = new DownloadHandlerBuffer();
            yield return request.SendWebRequest();

            if (request.result == UnityWebRequest.Result.Success)
            {
                string fileName = GenerateFileName(text);
                string absPath = SaveMotionFile(request.downloadHandler.data, fileName);
                
                if (!string.IsNullOrEmpty(absPath))
                {
                    Debug.Log($"[TextToMotionManager] Motion file saved: {absPath}");
                    PlayMotionFile(absPath);
                }
            }
            else
            {
                Debug.LogError($"[TextToMotionManager] Request failed: {request.error} " +
                              $"(status: {request.responseCode})\nBody: {request.downloadHandler.text}");
            }
        }
    }

    private string GenerateFileName(string text)
    {
        // Create a simple hash-based filename
        int hash = text.GetHashCode();
        return $"motion_{System.Math.Abs(hash) % 10000}.fbx";
    }

    private string SaveMotionFile(byte[] data, string fileName)
    {
        if (data == null || data.Length == 0)
        {
            Debug.LogError("[TextToMotionManager] Motion file data is empty.");
            return null;
        }

        string savePath;
#if UNITY_EDITOR
        savePath = Path.Combine(Application.dataPath, "Animations/Generated");
#else
        savePath = Application.persistentDataPath;
#endif
        Directory.CreateDirectory(savePath);
        
        string absPath = Path.Combine(savePath, fileName);
        File.WriteAllBytes(absPath, data);
        
        return absPath;
    }

    private void PlayMotionFile(string filePath)
    {
        if (motionManager == null)
        {
            motionManager = MotionManager.Instance;
        }

        if (motionManager == null)
        {
            Debug.LogWarning("[TextToMotionManager] MotionManager not available. Cannot play motion.");
            return;
        }

        bool success = motionManager.PlayMotion(filePath);
        if (!success)
        {
            Debug.LogError($"[TextToMotionManager] Failed to play motion file: {filePath}");
        }
    }
}
