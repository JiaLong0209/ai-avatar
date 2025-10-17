
#

## ollama

```bash

yay -S ollama

sudo systemctl enable ollama
sudo systemctl start ollama

ollama pull gemma:4b
ollama run gemma:4b

 
```


```bash
ollama serve &

ollama run gemma:7b

（第一次會自動下載）

啟動 FastAPI：

poetry run uvicorn app:app --reload --port 8000


測試：

curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, how are you?"}'
```

## Poetry  commands


```bash
poetry shell
uvicorn app:app --host 0.0.0.0 --port 8000

poetry run uvicorn app:app --reload


```



<!-- poetry run uvicorn app:app --host 0.0.0.0 --port 8000

poetry run flask run --host=0.0.0.0 --port=5000 -->

## Just delete the virtual environment
```bash

poetry env info --path
poetry env remove python

poetry env list --full-path
poetry env remove <env_path>

# or manually
rm -rf $(poetry env info --path)


```


## Structure
[User Input (Text / Voice)]
        │
        ▼
┌────────────────────┐
│     Unity Frontend │
└────────────────────┘
        │ Socket / REST
        ▼
┌────────────────────┐
│    Python Backend  │
└────────────────────┘
        │
        ▼
┌────────┬────────┬────────────┬─────────────┐
│  LLM   │  T2M   │ Emotion AI │  TTS (VITS) │
└────────┴────────┴────────────┴─────────────┘

## Unity Asset file structure

Assets/
│
├── 📁 Scenes/                          ← Unity 場景
│   └── MainScene.unity
│
├── 📁 Scripts/                         ← C# 腳本
│   ├── Chat/
│   │   ├── ChatUIManager.cs           ← 控制聊天輸入與輸出
│   │   └── STTListener.cs             ← 聲控觸發語音辨識（Whisper / Google）
│   │
│   ├── AICommunication/
│   │   ├── SocketClient.cs            ← Unity <-> Python 通訊
│   │   └── AIResponseHandler.cs       ← 接收與分發 AI 回應 (Text, Emotion, Motion, Audio)
│   │
│   ├── Avatar/
│   │   ├── AvatarController.cs        ← 控制 VRM 角色動作 / 表情
│   │   ├── LipSyncController.cs       ← 音訊驅動口型
│   │   └── IdleMotionHandler.cs       ← 控制等待時動畫
│   │
│   └── Utils/
│       ├── AudioPlayer.cs             ← 播放 TTS 音訊
│       └── BVHLoader.cs               ← 將 BVH 資料應用到 Animator
│
├── 📁 Prefabs/
│   ├── UI/
│   │   └── ChatPanel.prefab           ← 聊天 UI 元件
│   └── Characters/
│       └── MyVRMCharacter.prefab      ← VRM 角色預設物件
│
├── 📁 Resources/
│   ├── Animations/
│   │   ├── Idle.anim                  ← 預設待機動作
│   │   └── BVH_Imported.anim          ← 動態轉換的 BVH 動作（可於運行時生成）
│   ├── Audio/
│   │   └── TTS/                       ← TTS 音訊輸出存放區（WAV / MP3）
│   └── BlendShapes/
│       └── EmotionMap.asset           ← 表情映射設定（Emotion→BlendShape）
│
├── 📁 StreamingAssets/
│   └── BVH/                           ← 存放從 Python 傳來的動作 BVH 檔
│
├── 📁 VRM/
│   ├── Runtime/                       ← UniVRM 執行環境
│   └── Models/
│       └── MyCharacter.vrm            ← VRM 角色模型
│
├── 📁 Plugins/
│   ├── LipSync/
│   └── WhisperUnity/                  ← 若有內嵌 STT 模組
│
└── 📁 Materials/                      ← 材質與角色渲染用資源

## Unity 模組命名與功能規劃

模組名稱	功能說明

ChatUIManager	提供文字輸入與語音輸入的介面（文字框、語音錄製按鈕）
SpeechToTextModule	使用 Whisper 或 Google API 進行語音轉文字（可長期監聽）
SocketClient / APIClient	與 Python 後端進行 Socket 或 HTTP 通訊
AvatarController	控制 VRM 角色的表情（BlendShape）、動畫、Lip Sync 等
MotionPlayer	將 AI 回傳的 BVH 或 Unity 動作套用到 Animator 上
LipSyncController	根據 VITS 語音輸出進行口型同步（可使用 OVR Lip Sync）
IdleMotionHandler	在等待時顯示隨機 Idle 動作或表情

## Python 模組命名與功能規劃
app.py	Flask / FastAPI 主入口，接收 Unity 請求並回傳 JSON 結果
llm_module.py	使用 HuggingFace Transformers (如 Llama 3 / GPT2) 處理對話輸出
motion_gen.py	將 LLM 的輸出文字送進 MotionCLIP / T2M-GPT 生成 BVH
emotion_classifier.py	使用文字情緒分類模型（BERT 或 finetune 模型）回傳情緒類別
tts_module.py	使用 VITS / Edge-TTS 等 TTS 引擎生成語音並存為 WAV
socket_server.py	Socket Server，用於與 Unity 實時通訊
utils/logger.py	日誌與錯誤處理模組
config.yaml/json	設定檔（模型路徑、情緒對應表、動作對應表）

 ## AI 模型與資料流

使用者輸入語音 → Unity STT → 傳給 Python（文字）

LLM（如 Llama 3）根據文字回應句子

將句子同時丟入：

MotionCLIP / T2M-GPT → 產生 BVH

EmotionClassifier → 回傳「開心、悲傷…」等情緒

VITS → 輸出語音（WAV 檔案）

Python 統整結果 → 傳回 Unity

Unity 控制角色進行表演（動作、表情、口型、語音播放）


## 建議通訊方式（Unity ↔ Python）

使用 Socket（TCP/WebSocket）可以同時傳送多筆資料（語音、文字、動作路徑）

或使用 HTTP API 分段請求（例如先傳送文字請求，再用 GET 拿語音與動作）

## 優化建議
若 VRChat 要用，請轉換動作為 Unity Animator Clip 或 .anim（可轉換 BVH）

使用 VRM SDK（UniVRM）以正確控制 BlendShape、表情與口型

可加入記憶模組（RAG / Conversation History）

## Project Names
🔖 風格一：專業實驗型（適合畢專或研究項目）
名稱	說明
AIDeskAvatar	AI 桌面虛擬角色的總稱，簡潔專業
TalkMotionAI	強調「對話 + 動作生成」
VirtualAgent3D	虛擬角色代理人，較中性
AICharacterCore	虛擬角色核心系統
MultimodalPetAI	多模態虛擬寵物 AI（語音+表情+動作）

🎨 風格二：創意應用型（強調角色互動）
名稱	說明
SoulPet	角色像有靈魂一樣與你互動 ✨
LivePetGPT	Live2D/3D + GPT 整合式桌寵
EmotiMate	Emotion + Mate（感情 + 夥伴）
ChatToMotion	從聊天控制角色動作
FeelMotionAI	會「感覺」的角色動作系統

💡 如果是針對技術核心（模組化）
模組	建議命名
Python 後端	LLMBridge, ChatMotionServer, UnityAI-Bridge
Unity 專案	PetClient, AvatarCore, UnityMotionAgent
整體倉庫	AICharacterEngine, ChatDrivenAvatar, GPT3DActor

## 額外建議工具與資源
功能	建議工具資源
VRM 載入與控制	UniVRM SDK
表情控制（BlendShape）	VRMBlendShapeProxy / ExpressionPreset
動作載入（BVH）	自寫 BVHLoader + Avatar IK 或 Human Rig Mapping
音訊播放（TTS 語音）	AudioSource + 動態載入音訊
口型同步	OVR LipSync / Rhubarb Lip Sync + viseme map
UI 互動面板	TextMeshPro + Unity UI 元件
Python 通訊	System.Net.Sockets + async task handling

## 測試建議
建議建立一個 Test/ 資料夾並使用 Unity Test Framework 撰寫以下單元測試：

是否正確接收到 Python 回傳的 JSON 並處理

Emotion → 表情映射是否正常

BVH 是否成功應用在角色上
