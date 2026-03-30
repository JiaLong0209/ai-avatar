using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using UnityEngine.Audio;

public class TtsHttpProvider : MonoBehaviour, ITtsProvider
{
    [SerializeField] private string ttsUrl = "http://localhost:8000/tts"; 
    [SerializeField] private AudioSource audioSource;
    [SerializeField] private bool useMp3 = true; 
    [SerializeField] private string language = "zh"; 
    
    // [ADD THIS] Variable to select provider
    [SerializeField] private string provider = "gtts"; // Options: "vits", "gtts"

    private bool isSpeaking;

    public void Speak(string text)
    {
        if (!gameObject.activeInHierarchy) return;
        StartCoroutine(SpeakCoroutine(text));
    }

    private IEnumerator SpeakCoroutine(string text)
    {
        if (string.IsNullOrEmpty(ttsUrl)) yield break;

        // [MODIFIED] Logic to handle both GET and POST with the new provider param
        if (useMp3)
        {
            // Build GET URL
            string url = ttsUrl + "?text=" + UnityWebRequest.EscapeURL(text);
            
            if (!string.IsNullOrEmpty(language))
                url += "&lang=" + UnityWebRequest.EscapeURL(language);
            
            // Append provider
            if (!string.IsNullOrEmpty(provider))
                url += "&provider=" + UnityWebRequest.EscapeURL(provider);

            Debug.Log("TTS Request URL: " + url);
            
            using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.MPEG))
            {
                yield return www.SendWebRequest();
                if (www.result == UnityWebRequest.Result.Success)
                {
                    AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                    PlayClip(clip);
                }
                else
                {
                    Debug.LogError($"TTS mp3 error: {www.error}");
                }
            }
        }
        else
        {
            // Build POST Form
            WWWForm form = new WWWForm();
            form.AddField("text", text);
            form.AddField("format", "wav");
            
            if (!string.IsNullOrEmpty(language)) form.AddField("lang", language);
            
            // Add provider field
            if (!string.IsNullOrEmpty(provider)) form.AddField("provider", provider);

            using (UnityWebRequest www = UnityWebRequest.Post(ttsUrl, form))
            {
                www.downloadHandler = new DownloadHandlerBuffer();
                yield return www.SendWebRequest();
                
                if (www.result == UnityWebRequest.Result.Success)
                {
                    byte[] wavBytes = www.downloadHandler.data;
                    AudioClip clip = WavUtility.ToAudioClip(wavBytes, "tts");
                    PlayClip(clip);
                }
                else
                {
                    Debug.LogError($"TTS wav error: {www.error}");
                }
            }
        }
    }

    private void PlayClip(AudioClip clip)
    {
        if (clip == null) return;
        
        if (audioSource == null)
        {
            audioSource = gameObject.GetComponent<AudioSource>();
            if (audioSource == null) audioSource = gameObject.AddComponent<AudioSource>();
        }
        audioSource.clip = clip;
        audioSource.Play();
    }
}
