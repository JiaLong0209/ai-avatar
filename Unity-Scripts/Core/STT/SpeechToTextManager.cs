using UnityEngine;
using UnityEngine.UI;
using TMPro;
using UnityEngine.Networking;
using System.Collections;
using System.IO;

public class SpeechToTextManager : MonoBehaviour
{
    [SerializeField] private Button toggleRecordButton;
    [SerializeField] private TextMeshProUGUI statusText;
    [SerializeField] private TextMeshProUGUI userInput;
    [SerializeField] private string sttUrl = "http://localhost:8000/stt";

    private AudioClip clip;
    private bool recording;
    private const int sampleRate = 16000;

    private void Start()
    {
        toggleRecordButton.onClick.AddListener(ToggleRecording);
        statusText.text = "語音輸入";
    }

    private void ToggleRecording()
    {
        if (!recording) StartRecording();
        else StopRecording();
    }

    private void StartRecording()
    {
        statusText.text = " Recording...";
        statusText.color = Color.green;
        clip = Microphone.Start(null, false, 10, sampleRate);
        recording = true;
    }

    private void StopRecording()
    {
        recording = false;
        Microphone.End(null);

        statusText.text = "處理中...";
        statusText.color = Color.yellow;

        SaveAndSend();
    }

    private void SaveAndSend()
    {
        float[] samples = new float[clip.samples];
        clip.GetData(samples, 0);

        byte[] wavData = WavUtility.FromAudioClip(clip); // UtilityでWAVに変換

        StartCoroutine(SendToWhisper(wavData));
    }

    private IEnumerator SendToWhisper(byte[] wavData)
    {
        WWWForm form = new WWWForm();
        form.AddBinaryData("file", wavData, "speech.wav", "audio/wav");

        using (UnityWebRequest www = UnityWebRequest.Post(sttUrl, form))
        {
            www.timeout = 30;
            Debug.Log("STT URL: " + sttUrl + ", bytes: " + (wavData != null ? wavData.Length : 0));
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                string resultJson = www.downloadHandler.text;
                WhisperResponse result = null;
                try
                {
                    result = JsonUtility.FromJson<WhisperResponse>(resultJson);
                }
                catch (System.Exception ex)
                {
                    Debug.LogError("STT JSON parse error: " + ex.Message + ", body: " + resultJson);
                }
                if (result != null && !string.IsNullOrEmpty(result.text))
                {
                    userInput.text = result.text;
                    Debug.Log("SpeechToTextManager: " + result.text);
                }
                else
                {
                    Debug.LogError("STT empty text. Body: " + resultJson);
                }

                // Chatへ送信
                // ChatUIManager uiManager = FindObjectOfType<ChatUIManager>();
                ChatUIManager uiManager = FindFirstObjectByType<ChatUIManager>();
                if (uiManager != null)
                {
                    uiManager.userInputUI.text = result.text;
                    uiManager.OnSendClicked();
                }
                statusText.text = "語音輸入";
            }
            else
            {
                statusText.text = "Error: " + www.error + " (" + www.responseCode + ")";
                Debug.LogError("STT request failed. URL: " + sttUrl + ", status: " + www.responseCode + ", error: " + www.error + ", body: " + www.downloadHandler.text);
            }
        }
    }

    [System.Serializable]
    public class WhisperResponse
    {
        public string text;
    }
}
