using System.Collections.Generic;
using System;
using System.Linq;

/// <summary>
/// Represents a single chat message with role and content.
/// </summary>
[Serializable]
public class ChatMessage
{
    public string role;
    public string content;

    public ChatMessage(string role, string content)
    {
        this.role = role;
        this.content = content;
    }
}

/// <summary>
/// Payload structure for chat API requests.
/// Contains a list of messages for conversation context.
/// </summary>
[Serializable]
public class ChatPayload
{
    public List<ChatMessage> messages = new List<ChatMessage>();
}

/// <summary>
/// Manages chat conversation history with support for context extraction.
/// Implements singleton pattern for global access.
/// </summary>
public class ChatHistoryManager
{
    private static ChatHistoryManager instance;
    
    public static ChatHistoryManager Instance
    {
        get
        {
            if (instance == null)
            {
                instance = new ChatHistoryManager();
            }
            return instance;
        }
    }

    private readonly List<ChatMessage> messages = new List<ChatMessage>();

    /// <summary>
    /// Gets read-only access to all messages.
    /// </summary>
    public IReadOnlyList<ChatMessage> Messages => messages.AsReadOnly();

    /// <summary>
    /// Gets the total number of messages.
    /// </summary>
    public int MessageCount => messages.Count;

    /// <summary>
    /// Clears all conversation history.
    /// </summary>
    public void Clear()
    {
        messages.Clear();
    }

    /// <summary>
    /// Adds a user message to the history.
    /// </summary>
    public void AddUserMessage(string content)
    {
        if (string.IsNullOrWhiteSpace(content)) return;
        messages.Add(new ChatMessage("user", content));
    }

    /// <summary>
    /// Adds an assistant message to the history.
    /// </summary>
    public void AddAssistantMessage(string content)
    {
        if (string.IsNullOrWhiteSpace(content)) return;
        messages.Add(new ChatMessage("assistant", content));
    }

    /// <summary>
    /// Creates a payload with full message history, including system memory.
    /// </summary>
    public ChatPayload CreatePayload()
    {
        var payload = new ChatPayload { messages = new List<ChatMessage>() };

        // Inject system memory if present
        string systemMemory = UserMemoryManager.Instance.BuildSystemMemoryMessage();
        if (!string.IsNullOrEmpty(systemMemory))
        {
            payload.messages.Add(new ChatMessage("system", systemMemory));
        }

        // Copy conversation messages
        payload.messages.AddRange(messages);
        return payload;
    }

    /// <summary>
    /// Gets the latest N user messages from history.
    /// </summary>
    /// <param name="count">Number of user messages to retrieve (default: 2)</param>
    /// <returns>List of user messages, most recent first</returns>
    public List<ChatMessage> GetLatestUserMessages(int count = 5)
    {
        return messages
            .Where(m => m.role == "user")
            .TakeLast(count)
            .ToList();
    }

    /// <summary>
    /// Gets the latest N assistant messages from history.
    /// </summary>
    /// <param name="count">Number of assistant messages to retrieve (default: 2)</param>
    /// <returns>List of assistant messages, most recent first</returns>
    public List<ChatMessage> GetLatestAssistantMessages(int count = 2)
    {
        return messages
            .Where(m => m.role == "assistant")
            .TakeLast(count)
            .ToList();
    }

    /// <summary>
    /// Creates a payload with only the latest N user and assistant messages for context.
    /// Useful for motion generation where we want recent context but not full history.
    /// </summary>
    /// <param name="userMessageCount">Number of recent user messages to include</param>
    /// <param name="assistantMessageCount">Number of recent assistant messages to include</param>
    /// <returns>ChatPayload with limited message history</returns>
    public ChatPayload CreateContextPayload(int userMessageCount = 5, int assistantMessageCount = 5)
    {
        var payload = new ChatPayload { messages = new List<ChatMessage>() };

        // Inject system memory if present
        string systemMemory = UserMemoryManager.Instance.BuildSystemMemoryMessage();
        if (!string.IsNullOrEmpty(systemMemory))
        {
            payload.messages.Add(new ChatMessage("system", systemMemory));
        }

        // Get latest messages (these are already in chronological order from TakeLast)
        var userMessages = GetLatestUserMessages(userMessageCount);
        var assistantMessages = GetLatestAssistantMessages(assistantMessageCount);

        // Create sets of message content+role for quick lookup
        var userMessageKeys = new HashSet<string>();
        foreach (var msg in userMessages)
        {
            userMessageKeys.Add($"{msg.role}:{msg.content}");
        }
        
        var assistantMessageKeys = new HashSet<string>();
        foreach (var msg in assistantMessages)
        {
            assistantMessageKeys.Add($"{msg.role}:{msg.content}");
        }

        // Add messages in original chronological order
        var contextMessages = new List<ChatMessage>();
        foreach (var msg in messages)
        {
            string key = $"{msg.role}:{msg.content}";
            if ((msg.role == "user" && userMessageKeys.Contains(key)) ||
                (msg.role == "assistant" && assistantMessageKeys.Contains(key)))
            {
                contextMessages.Add(msg);
            }
        }

        payload.messages.AddRange(contextMessages);
        return payload;
    }

    /// <summary>
    /// Gets the last message in the conversation.
    /// </summary>
    public ChatMessage GetLastMessage()
    {
        return messages.Count > 0 ? messages[messages.Count - 1] : null;
    }

    /// <summary>
    /// Gets the last user message.
    /// </summary>
    public ChatMessage GetLastUserMessage()
    {
        for (int i = messages.Count - 1; i >= 0; i--)
        {
            if (messages[i].role == "user")
            {
                return messages[i];
            }
        }
        return null;
    }

    /// <summary>
    /// Gets the last assistant message.
    /// </summary>
    public ChatMessage GetLastAssistantMessage()
    {
        for (int i = messages.Count - 1; i >= 0; i--)
        {
            if (messages[i].role == "assistant")
            {
                return messages[i];
            }
        }
        return null;
    }
}
