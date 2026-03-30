using UnityEngine;
using System;

[Serializable]
public class UserMemoryManager
{
    private const string PlayerPrefsUserNameKey = "UserMemoryManager.UserName";
    private static UserMemoryManager instance;

    public static UserMemoryManager Instance
    {
        get
        {
            if (instance == null)
            {
                instance = new UserMemoryManager();
            }
            return instance;
        }
    }

    private string cachedUserName;

    private UserMemoryManager()
    {
        cachedUserName = PlayerPrefs.GetString(PlayerPrefsUserNameKey, string.Empty);
    }

    public bool HasUserName()
    {
        return !string.IsNullOrEmpty(cachedUserName);
    }

    public string GetUserName()
    {
        return cachedUserName;
    }

    public void SetUserName(string name)
    {
        if (string.IsNullOrEmpty(name))
        {
            cachedUserName = string.Empty;
            PlayerPrefs.DeleteKey(PlayerPrefsUserNameKey);
            PlayerPrefs.Save();
            return;
        }

        cachedUserName = name;
        PlayerPrefs.SetString(PlayerPrefsUserNameKey, cachedUserName);
        PlayerPrefs.Save();
    }

    public string BuildSystemMemoryMessage()
    {
        if (!HasUserName())
        {
            return string.Empty;
        }
        // Traditional Chinese instruction for the model to remember and use the user's name.
        return "使用者名稱是 " + cachedUserName + "。在對話中以名字稱呼使用者，並在需要時記住此資訊。";
    }
}


