using UnityEngine;

public class TtsManager : MonoBehaviour
{
    public static TtsManager Instance { get; private set; }

    [SerializeField] private MonoBehaviour providerComponent; // Must implement ITtsProvider
    private ITtsProvider provider;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);

        if (providerComponent != null)
        {
            provider = providerComponent as ITtsProvider;
        }
        if (provider == null)
        {
            // Auto-add HTTP provider if none set
            var http = gameObject.AddComponent<TtsHttpProvider>();
            provider = http;
        }
    }

    public static TtsManager Ensure()
    {
        if (Instance != null) return Instance;
        var existing = FindFirstObjectByType<TtsManager>();
        if (existing != null)
        {
            Instance = existing;
            return Instance;
        }
        var go = new GameObject("TtsManager");
        var mgr = go.AddComponent<TtsManager>();
        return mgr;
    }

    public void Speak(string text)
    {
        if (string.IsNullOrEmpty(text)) return;
        if (provider == null) return;
        provider.Speak(text);
    }
}


