using UnityEngine;
using UnityEngine.UI;
using TMPro;
using UnityEngine.Networking;
using UnityEngine.InputSystem;
using System;
using System.Collections;
using System.Text;
using System.IO;
using System.Text.RegularExpressions; 

/// <summary>
/// Unified ChatUIManager: combines text chat + motion generation.
/// </summary>
public class ChatUIManager : MonoBehaviour
{
    [Header("UI References")]
    [SerializeField] public TMP_InputField userInputUI;
    [SerializeField] public Button sendButton;
    [SerializeField] public TextMeshProUGUI responseText;
    [SerializeField] public TextMeshProUGUI chatHistoryText;
    [SerializeField] public TextMeshProUGUI statusText;

    [Header("Backend URLs")]
    [SerializeField] private string chatUrl = "http://localhost:8000/chat";
    [SerializeField] private string chatT2mUrl = "http://localhost:8000/chat_t2m";

    [Header("Motion Playback")]
    [SerializeField] private MotionManager motionManager;
    [SerializeField] private bool autoFindMotionManager = true;

    [Header("Motion Generation Context")]
    [SerializeField] [Range(1, 10)] private int contextUserMessageCount = 5;
    [SerializeField] [Range(1, 10)] private int contextAssistantMessageCount = 5;
    [SerializeField] private bool useContextForMotion = true;

    private StringBuilder chatHistory = new StringBuilder();

    // Static property to let other scripts check focus status
    public static bool IsInputFocused { get; private set; }

    private string CleanTextForTts(string rawText)
    {
        if (string.IsNullOrEmpty(rawText)) return "";

        // 1. Replace newlines with space
        string text = rawText.Replace("\n", " ").Replace("\r", " ");

        // 2. Remove Emojis
        // \p{Cs} matches Surrogate codes, which covers most emojis in UTF-16
        // \p{So} matches Symbol, Other
        // This regex removes surrogates and "Symbol, Other" characters
        text = Regex.Replace(text, @"\p{Cs}|\p{So}", "");

        return text.Trim();
    }
    private void Awake()
    {
        if (sendButton != null)
            sendButton.onClick.AddListener(OnSendClicked);

        InitializeMotionManager();
    }

    private void InitializeMotionManager()
    {
        if (motionManager == null && autoFindMotionManager)
        {
            motionManager = MotionManager.Instance ?? MotionManager.Ensure();
            if (motionManager != null)
            {
                Debug.Log("[ChatUIManager] Connected to MotionManager");
            }
        }

        if (motionManager == null)
        {
            Debug.LogWarning("[ChatUIManager] MotionManager not found. Motion playback will be unavailable.");
        }
    }

    private void Update()
    {
        if (userInputUI != null)
        {
            IsInputFocused = userInputUI.isFocused;
        }

        var keyboard = Keyboard.current;
        if (keyboard == null) return;

        // 1. "/" 鍵：自動聚焦到輸入框
        if (keyboard.slashKey.wasPressedThisFrame && !userInputUI.isFocused)
        {
            userInputUI.ActivateInputField();
            userInputUI.Select();
        }

        // 2. "Enter" 鍵：觸發按鈕邏輯
        // 檢查 Enter 是否被按下
        if (keyboard.enterKey.wasPressedThisFrame || keyboard.numpadEnterKey.wasPressedThisFrame)
        {
            // 條件：輸入框有焦點 且 內容不是空白
            if (userInputUI.isFocused && !string.IsNullOrWhiteSpace(userInputUI.text))
            {
                // 直接呼叫按鈕的 onClick 事件（這會讓 UI 按鈕有被點擊的反應）
                if (sendButton != null)
                {
                    sendButton.onClick.Invoke();
                }
                else
                {
                    // 如果沒掛載按鈕，則直接執行方法
                    OnSendClicked();
                }

                // 發送後讓輸入框失去焦點（或是保持聚焦，看你的操作習慣）
                userInputUI.DeactivateInputField();
            }
        }
    }

    public void OnSendClicked()
    {
        string text = userInputUI != null ? userInputUI.text : string.Empty;
        if (string.IsNullOrEmpty(text)) return;

        // Add to history manager
        if (ChatHistoryManager.Instance != null)
        {
            ChatHistoryManager.Instance.AddUserMessage(text);
        }

        AppendToHistory("----------------\nYou: " + text);
        userInputUI.text = string.Empty;

        Debug.Log("[ChatUIManager] Starting chat request and motion generation");
        StartCoroutine(SendChatRequestThenT2M(text));
    }

    // ====== Chained Flow: Chat Request -> Motion Generation ======
    private IEnumerator SendChatRequestThenT2M(string userInput)
    {
        string llmResponse = null;

        // Step 1: Send chat request and wait for LLM response
        yield return StartCoroutine(SendChatRequest(userInput, (response) => { llmResponse = response; }));

        // Step 2: If we got a valid response, use it for motion generation with context
        if (!string.IsNullOrEmpty(llmResponse))
        {
            Debug.Log($"[ChatUIManager] Using LLM response for motion generation: {llmResponse}");
            yield return StartCoroutine(SendChatT2MWithContext(llmResponse));
        }
        else
        {
            Debug.LogWarning("[ChatUIManager] No LLM response received, skipping motion generation.");
            statusTextSet("Motion generation skipped: no LLM response.");
        }
    }

    // ====== Chat Text API ======
    private IEnumerator SendChatRequest(string userInput, System.Action<string> onResponse = null)
    {
        ChatPayload payload = ChatHistoryManager.Instance.CreatePayload();
        

        string jsonPayload = JsonUtility.ToJson(payload);
        var request = new UnityWebRequest(chatUrl, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonPayload);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string fullJson = request.downloadHandler.text;
            string cleaned = ParseAIResponse(fullJson);

            if (responseText != null)
                responseText.text = cleaned;

            AppendToHistory("AI: " + cleaned);

            if (ChatHistoryManager.Instance != null)
                ChatHistoryManager.Instance.AddAssistantMessage(cleaned);

            if (TtsManager.Instance != null)
            {
                // Clean text before sending to TTS
                string ttsText = CleanTextForTts(cleaned);
                Debug.Log($"[ChatUIManager] TTS Speaking: {ttsText}"); // Debug log to verify
                TtsManager.Instance.Speak(ttsText);
            }
            statusTextSet("AI Response received.");

            // Call the callback with the response
            onResponse?.Invoke(cleaned);
        }
        else
        {
            Debug.LogError($"Chat request failed: {request.error}");
            statusTextSet("Error: " + request.error);
            onResponse?.Invoke(null);
        }
    }

    /// <summary>
    /// Sends motion generation request with context from chat history.
    /// </summary>
    private IEnumerator SendChatT2MWithContext(string llmResponse, bool saveInProject = true)
    {
        statusTextSet("Generating motion...");

        // Build context payload with recent messages
        ChatPayload contextPayload = null;
        
        if (useContextForMotion && ChatHistoryManager.Instance != null)
        {
            contextPayload = ChatHistoryManager.Instance.CreateContextPayload(
                contextUserMessageCount,
                contextAssistantMessageCount
            );
            Debug.Log($"[ChatUIManager] Using context: {contextUserMessageCount} user messages, " +
                     $"{contextAssistantMessageCount} assistant messages");
        }
        else
        {
            // Fallback to simple payload
            contextPayload = new ChatPayload
            {
                messages = new System.Collections.Generic.List<ChatMessage>
                {
                    new ChatMessage("assistant", llmResponse)
                }
            };
        }

        var payload = new ChatPayloadReq
        {
            payload = contextPayload,
            t2m_text = llmResponse, // Pass LLM response, backend will generate motion description from it
            format = "fbx"
        };

        string json = JsonUtility.ToJson(payload);
        var req = new UnityWebRequest(chatT2mUrl, "POST");
        req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");

        yield return req.SendWebRequest();

        if (req.result == UnityWebRequest.Result.Success)
        {
            var jsonResp = req.downloadHandler.text;
            ChatT2MResponse resp = null;
            try
            {
                resp = JsonUtility.FromJson<ChatT2MResponse>(jsonResp);
            }
            catch (Exception ex)
            {
                Debug.LogError("chat_t2m JSON parse error: " + ex.Message + ", body: " + jsonResp);
            }

            if (resp != null && !string.IsNullOrEmpty(resp.file_base64))
            {
                string fileName = string.IsNullOrEmpty(resp.file_name) ? "motion.fbx" : resp.file_name;

                string path;
#if UNITY_EDITOR
                if (saveInProject)
                {
                    // Save inside Assets/Animations/Generated
                    string projectPath = Application.dataPath;
                    string dir = Path.Combine(projectPath, "Animations/Generated");
                    Directory.CreateDirectory(dir);
                    path = Path.Combine(dir, fileName);
                }
                else
#endif
                {
                    //  Save in persistent data path (temp/runtime)
                    string dir = Application.persistentDataPath;
                    Directory.CreateDirectory(dir);
                    path = Path.Combine(dir, fileName);
                }

                File.WriteAllBytes(path, Convert.FromBase64String(resp.file_base64));
                statusTextSet($"Motion saved: {path}");
                Debug.Log($"[ChatUIManager] Motion file saved at: {path}");

                // Automatically play animation
                PlayMotionFile(path);
            }
            else
            {
                Debug.LogError("chat_t2m missing file data: " + jsonResp);
                statusTextSet("Motion generation failed.");
            }
        }
        else
        {
            Debug.LogError($"chat_t2m error: {req.error}, code: {req.responseCode}, body: {req.downloadHandler.text}");
            statusTextSet("Motion API error.");
        }
    }


    /// <summary>
    /// Plays a motion file using MotionManager.
    /// </summary>
    private void PlayMotionFile(string filePath)
    {
        if (string.IsNullOrEmpty(filePath))
        {
            Debug.LogWarning("[ChatUIManager] Cannot play motion: file path is empty.");
            return;
        }

        if (motionManager == null)
        {
            motionManager = MotionManager.Instance;
        }

        if (motionManager == null)
        {
            Debug.LogError("[ChatUIManager] MotionManager not available. Cannot play motion.");
            statusTextSet("Motion playback unavailable: MotionManager not found.");
            return;
        }

        bool success = motionManager.PlayMotion(filePath);
        if (success)
        {
            Debug.Log($"[ChatUIManager] Playing motion from: {filePath}");
            statusTextSet("Motion playing...");
        }
        else
        {
            Debug.LogError("[ChatUIManager] Failed to play motion.");
            statusTextSet("Failed to play motion.");
        }
    }

    private void statusTextSet(string s)
    {
        Debug.Log($"[ChatUIManager] Status: {s}");
        if (statusText != null)
            statusText.text = s;
    }

    private void AppendToHistory(string message)
    {
        chatHistory.AppendLine(message);
        if (chatHistoryText != null)
            chatHistoryText.text = chatHistory.ToString();
        Debug.Log("Chat history: " + message);
    }

    private string ParseAIResponse(string json)
    {
        int start = json.IndexOf(":\"") + 2;
        int end = json.LastIndexOf("\"");
        if (start >= 0 && end > start)
            return json.Substring(start, end - start);
        return "Invalid JSON response";
    }

    // ====== Internal Payload Types ======
    [Serializable] private class ChatPayloadReq
    {
        public ChatPayload payload;
        public string t2m_text;
        public string format;
    }
    [Serializable] private class ChatT2MResponse
    {
        public string motion_text;
        public string format;
        public string file_name;
        public string file_base64;
    }
}
