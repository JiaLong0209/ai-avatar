using System;
using System.IO;
using UnityEngine;

public static class WavUtility
{
    const int HEADER_SIZE = 44;

    public static byte[] FromAudioClip(AudioClip clip)
    {
        using (MemoryStream stream = new MemoryStream())
        {
            int frequency = clip.frequency;
            int channels = clip.channels;
            float[] samples = new float[clip.samples * channels];
            clip.GetData(samples, 0);

            ushort bitDepth = 16;
            int byteRate = frequency * channels * (bitDepth / 8);

            // Write WAV header
            WriteHeader(stream, clip.samples, channels, frequency, bitDepth);

            // Convert float samples to PCM16
            short[] intData = new short[samples.Length];
            byte[] bytesData = new byte[samples.Length * 2];
            int rescaleFactor = 32767;

            for (int i = 0; i < samples.Length; i++)
            {
                intData[i] = (short)(samples[i] * rescaleFactor);
                byte[] byteArr = BitConverter.GetBytes(intData[i]);
                byteArr.CopyTo(bytesData, i * 2);
            }

            stream.Write(bytesData, 0, bytesData.Length);

            return stream.ToArray();
        }
    }

    public static AudioClip ToAudioClip(byte[] wavData, string clipName)
    {
        if (wavData == null || wavData.Length < HEADER_SIZE) return null;

        using (MemoryStream stream = new MemoryStream(wavData))
        using (BinaryReader reader = new BinaryReader(stream))
        {
            // RIFF header
            reader.ReadChars(4); // "RIFF"
            reader.ReadInt32();
            reader.ReadChars(4); // "WAVE"
            reader.ReadChars(4); // "fmt "
            int subchunk1Size = reader.ReadInt32();
            ushort audioFormat = reader.ReadUInt16();
            ushort channels = reader.ReadUInt16();
            int sampleRate = reader.ReadInt32();
            int byteRate = reader.ReadInt32();
            ushort blockAlign = reader.ReadUInt16();
            ushort bitsPerSample = reader.ReadUInt16();

            // Skip any extra fmt bytes
            if (subchunk1Size > 16)
            {
                reader.ReadBytes(subchunk1Size - 16);
            }

            // data header
            char[] dataHeader = reader.ReadChars(4); // may not be 'data' if there is a LIST chunk; simple parser assumes 'data'
            while (new string(dataHeader) != "data")
            {
                int chunkSize = reader.ReadInt32();
                reader.ReadBytes(chunkSize);
                dataHeader = reader.ReadChars(4);
            }
            int dataSize = reader.ReadInt32();

            byte[] pcm = reader.ReadBytes(dataSize);

            int totalSamples = dataSize / (bitsPerSample / 8);
            float[] floatData = new float[totalSamples];

            if (bitsPerSample == 16)
            {
                int index = 0;
                for (int i = 0; i < totalSamples; i++)
                {
                    short sample = System.BitConverter.ToInt16(pcm, index);
                    floatData[i] = sample / 32768.0f;
                    index += 2;
                }
            }
            else
            {
                // Only 16-bit PCM supported in this simple parser
                Debug.LogError("Unsupported WAV bit depth: " + bitsPerSample);
                return null;
            }

            int numSamples = totalSamples / channels;
            AudioClip clip = AudioClip.Create(clipName, numSamples, channels, sampleRate, false);
            clip.SetData(floatData, 0);
            return clip;
        }
    }

    private static void WriteHeader(Stream stream, int samples, int channels, int frequency, ushort bitDepth)
    {
        using (BinaryWriter writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true))
        {
            writer.Write(System.Text.Encoding.UTF8.GetBytes("RIFF"));
            writer.Write((int)(HEADER_SIZE - 8 + samples * channels * (bitDepth / 8)));
            writer.Write(System.Text.Encoding.UTF8.GetBytes("WAVE"));
            writer.Write(System.Text.Encoding.UTF8.GetBytes("fmt "));
            writer.Write(16);
            writer.Write((ushort)1);
            writer.Write((ushort)channels);
            writer.Write(frequency);
            writer.Write(frequency * channels * (bitDepth / 8));
            writer.Write((ushort)(channels * (bitDepth / 8)));
            writer.Write(bitDepth);
            writer.Write(System.Text.Encoding.UTF8.GetBytes("data"));
            writer.Write(samples * channels * (bitDepth / 8));
        }
    }
}



// using UnityEngine;
// using UnityEngine.UI;
// using TMPro;
// using System.Collections;
// using Vosk;  // Vosk C# binding
// using System.Text;

// public class SpeechToTextManager : MonoBehaviour
// {
//     [SerializeField] private Button toggleRecordButton;
//     [SerializeField] private TextMeshProUGUI statusText;

//     private AudioClip clip;
//     private bool recording;
//     private VoskRecognizer recognizer;
//     private const int sampleRate = 16000; // Vosk用に16kHzが推奨

//     private void Start()
//     {
//         // 中国語 (Mandarin)
//         string modelPath = System.IO.Path.Combine(Application.streamingAssetsPath, "models/vosk-model-small-cn-0.22");
//         // string modelPath = System.IO.Path.Combine(Application.streamingAssetsPath, "models/vosk-model-small-en-us");

//         Vosk.Vosk.SetLogLevel(0);
//         Model model = new Model(modelPath);
//         recognizer = new VoskRecognizer(model, sampleRate);

//         toggleRecordButton.onClick.AddListener(ToggleRecording);
//         statusText.text = "Ready";
//     }

//     private void ToggleRecording()
//     {
//         if (!recording)
//         {
//             StartRecording();
//         }
//         else
//         {
//             StopRecording();
//         }
//     }

//     private void StartRecording()
//     {
//         statusText.color = Color.green;
//         statusText.text = "Recording...";
//         clip = Microphone.Start(null, true, 10, sampleRate);
//         recording = true;
//         StartCoroutine(ProcessAudio());
//     }

//     private void StopRecording()
//     {
//         recording = false;
//         Microphone.End(null);
//         statusText.color = Color.yellow;
//         statusText.text = "Processing...";
//     }

//     private IEnumerator ProcessAudio()
//     {
//         int lastSample = 0;

//         while (recording)
//         {
//             int pos = Microphone.GetPosition(null);
//             if (pos > 0 && pos > lastSample)
//             {
//                 float[] samples = new float[pos - lastSample];
//                 clip.GetData(samples, lastSample);

//                 // float -> short に変換
//                 short[] intData = new short[samples.Length];
//                 for (int i = 0; i < samples.Length; i++)
//                     intData[i] = (short)(samples[i] * short.MaxValue);

//                 byte[] bytes = new byte[intData.Length * 2];
//                 System.Buffer.BlockCopy(intData, 0, bytes, 0, bytes.Length);

//                 if (recognizer.AcceptWaveform(bytes, bytes.Length))
//                 {
//                     string result = recognizer.Result();
//                     Debug.Log("Partial: " + result);
//                     statusText.text = "Listening...";
//                 }
//                 else
//                 {
//                     string partial = recognizer.PartialResult();
//                     Debug.Log("Partial Result: " + partial);
//                 }

//                 lastSample = pos;
//             }
//             yield return null;
//         }

//         // Final認識
//         string finalResult = recognizer.FinalResult();
//         Debug.Log("Final: " + finalResult);
//         statusText.color = Color.white;
//         statusText.text = finalResult;

//         // ChatUIManagerに送信
//         ChatUIManager uiManager = FindObjectOfType<ChatUIManager>();
//         if (uiManager != null)
//         {
//             uiManager.userInputUI.text = finalResult;
//             uiManager.SendButtonClick();
//         }
//     }
// }