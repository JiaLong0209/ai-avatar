# vits 使用說明（完整範例與參數說明）

下面示範如何將一句英文翻譯成日文，並讓角色 "MyNewCharacter" 以稍慢的語速合成語音，最後將音訊儲存為指定檔名。請在您的 vits 資料夾中執行下列程式碼。

程式碼（Bash）
```bash
python tts_cli.py --text "Hello, this is a complete test using all available parameters." --speaker "MyNewCharacter" --language "JA" --source_language "EN" --output "full_example_output_ja.wav" --speed 1.2 --model_dir "G_latest.pth" --config_dir "config.json"
```

## 參數逐一詳解

### 核心參數（最常用）
- --text (-t)  
  說明: （必需）要合成的原始文字內容。  
  範例: `--text "你好世界"`

- --speaker (-s)  
  說明: （必需）要使用的角色名稱，必須與 `config.json` 中 `speakers` 列表的名稱相符。  
  範例: `--speaker "MyNewCharacter"`

- --language (-l)  
  說明: （可選）指定最終生成的目標語言。  
  可選值: `JA`, `ZH`, `EN`。  
  預設值: `ZH`（簡體中文）。  
  範例: `--language "JA"`（輸出日語語音）。

- --output (-o)  
  說明: （可選）輸出音訊檔的路徑與檔名。  
  預設值: `output.wav`。  
  範例: `--output "dialogue/scene1_audio.wav"`

### 翻譯與進階參數
- --source_language  
  說明: （可選）輸入文字的來源語言，用於觸發自動翻譯。  
  可選值: `auto`, `JA`, `ZH`, `EN`。  
  預設值: `auto`（會嘗試自動偵測輸入語言）。  
  範例: `--source_language "EN"`

- --speed  
  說明: （可選）控制語音速度。數值越小語速越快；數值越大語速越慢。1.0 為基準速度。  
  預設值: `1.0`。  
  範例: `--speed 0.8`（語速加快 20%），`--speed 1.2`（語速減慢 20%）。

### 模型與設定檔參數（通常保持預設）
- --model_dir  
  說明: （可選）指定模型檔案（`.pth`）的路徑。  
  預設值: `G_latest.pth`。  
  範例: `--model_dir "MyAwesomeModel_2000.pth"`

- --config_dir  
  說明: （可選）指定設定檔（`.json`）的路徑。  
  預設值: `config.json`。  
  範例: `--config_dir "my_config.json"`

---

如需進一步範例或排版調整，請說明要加強的部份（例如：更多範例、參數表格、或簡短教學）。