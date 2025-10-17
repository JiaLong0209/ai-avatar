http -d GET http://localhost:8000/tts text="你好，世界" lang=zh --download

http -d GET http://localhost:8000/tts text="這會直接把 MP3 檔案傳回來。 要存成檔案可以加 " lang=zh --download

curl -G 'http://localhost:8000/tts' --data-urlencode 'text=你好，世界' --data-urlencode 'lang=zh' -o out.wav