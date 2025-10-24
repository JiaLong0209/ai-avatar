# Poetry package

poetry add fastapi uvicorn transformers torch
poetry self add poetry-plugin-shell

poetry add fastapi pydantic requests uvicorn

## STT
poetry add openai-whisper 
poetry add python-multipart

## TTS
poetry add gtts

## T2M

poetry add torch==2.8.0+cu121 --source pytorch-cu121
poetry add torchvision==0.23.0+cu121 --source pytorch-cu121


poetry add numpy openai-clip tqdm scipy

poetry add pillow
poetry add bpy



## Use python 3.11.9
pyenv install 3.11.9
pyenv versions

pyenv local 3.11.9

poetry env use ~/.pyenv/versions/3.11.9/bin/python