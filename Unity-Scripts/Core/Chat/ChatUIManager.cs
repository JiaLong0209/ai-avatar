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

    [Header("API Endpoints")]
    [SerializeField] private string chatUrl = "http://localhost:8000/chat";
    [SerializeField] private string chatT2mUrl = "http://localhost:8000/chat_t2m";
    [SerializeField] private string chatAndMotionUrl = "http://localhost:8000/chat_and_motion";

    [Header("API Flow Configuration")]
    [Tooltip("If true, chat and motion are requested in a single API call, allowing simultaneous audio/motion playback.")]
    public bool useCombinedFlow = true;

    [Header("Display Settings")]
    [Tooltip("If true, AI response text appears one character at a time.")]
    public bool useTypewriter = true;
    public float charDisplaySpeed = 0.1f;

    [Header("Motion Playback")]
    [SerializeField] private MotionManager motionManager;
    [SerializeField] private bool autoFindMotionManager = true;

    [Header("Motion Generation Context")]
    [SerializeField] [Range(1, 100)] private int contextUserMessageCount = 20;
    [SerializeField] [Range(1, 100)] private int contextAssistantMessageCount = 20;
    [SerializeField] private bool useContextForMotion = true;

    public enum MotionFormat { FBX, BVH }
    [Header("Motion Generation Format")]
    [SerializeField] private MotionFormat outputFormat = MotionFormat.BVH;

    private StringBuilder chatHistory = new StringBuilder();
    private Coroutine typingCoroutine;

    // Static property to let other scripts check focus status
    public static bool IsInputFocused { get; private set; }

    private string CleanTextForTts(string rawText)
    {
        if (string.IsNullOrEmpty(rawText)) return "";

        // 1. Replace newlines with space
        string text = rawText.Replace("\n", " ").Replace("\r", " ");

        // 2. Remove Emojis & Symbols
        text = Regex.Replace(text, @"\p{Cs}|\p{So}", "");

        // 3. Remove 顏文字 (Emoticons) patterns
        // Matches common strings like OuO, >w<, OwO, ^_^, etc.
        text = Regex.Replace(text, @"[O>o\^][w_]*[O<o\^]", "");
        
        // Remove complex ones like (｀・ω・´), (´・ω・`), etc.
        // This removes mostly brackets and unusual punctuation that 顏文字 use
        text = Regex.Replace(text, @"\([^\)]*[\u3000-\u303F\uFF00-\uFFEF][^\)]*\)", "");
        
        // Final cleanup of extra spaces
        text = Regex.Replace(text, @"\s+", " ");

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
        if (keyboard.enterKey.wasPressedThisFrame || keyboard.numpadEnterKey.wasPressedThisFrame)
        {
            if (userInputUI.isFocused && !string.IsNullOrWhiteSpace(userInputUI.text))
            {
                if (sendButton != null) sendButton.onClick.Invoke();
                else OnSendClicked();
                userInputUI.DeactivateInputField();
            }
        }

        // 3. "Ctrl + Backspace" 鍵：清除歷史紀錄與 UI
        if (keyboard.shiftKey.isPressed && keyboard.backspaceKey.wasPressedThisFrame)
        {
            ClearChatHistory();
        }
    }

    private void ClearChatHistory()
    {
        // 1. 清除 UI 顯示
        if (chatHistoryText != null) chatHistoryText.text = "";
        if (responseText != null) responseText.text = "";
        if (userInputUI != null) userInputUI.text = "";
        if (statusText != null) statusText.text = "History Cleared";

        // 2. 清除內部資料
        chatHistory.Clear();
        ChatHistoryManager.Instance.Clear();

        Debug.Log("[ChatUIManager] Chat history and UI cleared.");
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

        if (useCombinedFlow)
        {
            Debug.Log("[ChatUIManager] Starting combined chat & motion flow");
            StartCoroutine(SendCombinedChatAndMotion(text));
        }
        else
        {
            Debug.Log("[ChatUIManager] Starting chained chat request and motion generation");
            StartCoroutine(SendChatRequestThenT2M(text));
        }
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

    // ====== Combined Flow: Unified Chat & Motion ======
    private IEnumerator SendCombinedChatAndMotion(string userInput)
    {
        statusTextSet("Thinking and generating motion...");

        ChatPayload payload = ChatHistoryManager.Instance != null ? 
            ChatHistoryManager.Instance.CreatePayload() : 
            new ChatPayload { messages = new System.Collections.Generic.List<ChatMessage>() };

        var requestPayload = new ChatPayloadReq
        {
            payload = payload,
            t2m_text = userInput, 
            format = outputFormat.ToString().ToLower()
        };

        string jsonPayload = JsonUtility.ToJson(requestPayload);
        var request = new UnityWebRequest(chatAndMotionUrl, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonPayload);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        // Allow plenty of time for LLM JSON gen + Motion Gen
        request.timeout = 120; 

        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            string jsonResponse = request.downloadHandler.text;
            CombinedChatResponse response = JsonUtility.FromJson<CombinedChatResponse>(jsonResponse);

            if (response != null)
            {
                // 1. Process Text
                string reply = response.reply ?? string.Empty;
                
                if (useTypewriter)
                {
                    if (typingCoroutine != null) StopCoroutine(typingCoroutine);
                    typingCoroutine = StartCoroutine(TypeTextResponse(reply));
                }
                else
                {
                    if (responseText != null) responseText.text = reply;
                    AppendToHistory("AI: " + reply);
                }

                if (ChatHistoryManager.Instance != null)
                    ChatHistoryManager.Instance.AddAssistantMessage(reply);

                // 2. Process Audio (Text-to-Speech)
                if (TtsManager.Instance != null && !string.IsNullOrEmpty(reply))
                {
                    string ttsText = CleanTextForTts(reply);
                    Debug.Log($"[ChatUIManager] TTS Speaking: {ttsText}");
                    TtsManager.Instance.Speak(ttsText);
                }

                // 3. Process Motion
                if (!string.IsNullOrEmpty(response.file_base64) && !string.IsNullOrEmpty(response.file_name))
                {
                    try
                    {
                        byte[] fileData = System.Convert.FromBase64String(response.file_base64);
                        
                        string extension = response.format == "bvh" ? ".bvh" : ".fbx";
                        string fileName = response.file_name.EndsWith(extension) ? response.file_name : response.file_name + extension;
                        
                        string savePath = Path.Combine(Application.dataPath, "Animations", "Generated", fileName);
                        
                        string directory = Path.GetDirectoryName(savePath);
                        if (!Directory.Exists(directory))
                        {
                            Directory.CreateDirectory(directory);
                        }

                        File.WriteAllBytes(savePath, fileData);
                        Debug.Log($"[ChatUIManager] Saved combined motion file to {savePath}");

                        // Play the motion synchronously with TTS
                        if (MotionManager.Instance != null)
                        {
                            MotionManager.Instance.PlayMotion(savePath);
                        }
                    }
                    catch (System.Exception e)
                    {
                        Debug.LogError($"[ChatUIManager] Failed to save/play combined motion: {e.Message}");
                    }
                }
                else
                {
                    Debug.LogWarning("[ChatUIManager] No motion file returned in combined response.");
                }
                
                statusTextSet("Ready");
            }
        }
        else
        {
            Debug.LogError($"Combined API failed: {request.error}\n{request.downloadHandler.text}");
            statusTextSet("Error: " + request.error);
        }
    }


    // ====== UI Helper Methods ======
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

            if (useTypewriter)
            {
                if (typingCoroutine != null) StopCoroutine(typingCoroutine);
                typingCoroutine = StartCoroutine(TypeTextResponse(cleaned));
            }
            else
            {
                if (responseText != null) responseText.text = cleaned;
                AppendToHistory("AI: " + cleaned);
            }

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
            format = outputFormat.ToString().ToLower()
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
                string extension = outputFormat == MotionFormat.FBX ? ".fbx" : ".bvh";
                string baseName = string.IsNullOrEmpty(resp.file_name) ? "motion" : Path.GetFileNameWithoutExtension(resp.file_name);
                string fileName = $"{baseName}{extension}";

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

    [System.Serializable]
    public class CombinedChatResponse
    {
        public string reply;
        public string motion_text;
        public string format;
        public string file_name;
        public string file_base64;
    }
    private IEnumerator TypeTextResponse(string fullText)
    {
        Debug.Log($"[ChatUIManager] TypeTextResponse started. Speed: {charDisplaySpeed}");
        
        string baseHistory = chatHistory.ToString() + "AI: ";
        if (chatHistoryText != null) chatHistoryText.text = baseHistory;
        if (responseText != null) responseText.text = "";
        
        string currentTyping = "";
        foreach (char c in fullText)
        {
            currentTyping += c;
            
            if (responseText != null) responseText.text = currentTyping;
            if (chatHistoryText != null) chatHistoryText.text = baseHistory + currentTyping;
            
            yield return new WaitForSeconds(charDisplaySpeed);
        }
        
        // Finalize by committing to StringBuilder
        chatHistory.AppendLine("AI: " + fullText);
        
        Debug.Log("[ChatUIManager] TypeTextResponse finished.");
        typingCoroutine = null;
    }
}
