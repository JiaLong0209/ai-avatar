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

# Other

poetry add "setuptools==65.5.0"

## MDM
poetry add smplx
poetry add torch_dct 
poetry add joblib 
poetry add moviepy==1.0.3
poetry add spacy

# VITs
poetry add cython --group dev
poetry add unidecode
poetry add pyopenjtalk
poetry add jamo


poetry add pyopenjtalk-prebuilt jamo pypinyin jieba protobuf cn2an inflect eng_to_ipa ko_pron indic_transliteration==2.3.37 num_thai==0.0.5 opencc==1.1.1 demucs deep-translator

poetry add blis==0.7.8 chumpy==0.70 click==8.1.3 confection==0.0.2 ftfy==6.1.1 importlib-metadata==5.0.0 lxml==4.9.1 murmurhash==1.0.8 preshed==3.0.7 pycryptodomex==3.15.0 regex==2022.9.13 smplx==0.1.28 srsly==2.4.4 thinc==8.0.17 typing-extensions==4.1.1 urllib3==1.26.12 wasabi==0.10.1 wcwidth==0.2.5
# poetry add blis chumpy click confection ftfy importlib-metadata lxml murmurhash preshed pycryptodomex regex smplx srsly thinc typing-extensions urllib3 wasabi wcwidth

# poetry add ftfy==6.1.1 importlib-metadata lxml==4.9.1 pycryptodomex==3.15.0 regex smplx==0.1.28 wcwidth==0.2.5 chumpy==0.70
    
    # python 3.11
    # "bpy (>=4.5.3,<5.0.0)",
    # python 3.10
    # "bpy (>=3.4.1, <4.0.0)", # 


poetry add fastapi pydantic requests uvicorn ollama whisper openai-whisper python-multipart gtts torch numpy openai-clip tqdm pillow torchvision setuptools ipykernel matplotlib smplx torch-dct joblib moviepy spacy



# 安裝與 CUDA 12 相容的 nvcc 編譯器
poetry run pip install nvidia-cuda-nvcc-cu12

# # 1. 抓取 nvcc 的安裝路徑
# export NVCC_PATH=$(poetry run python -c "import os; import nvidia.cuda_nvcc_cu12 as nvcc; print(os.path.dirname(nvcc.__file__))")

# # 2. 顯示路徑確認一下 (應該會看到類似 .../site-packages/nvidia/cuda_nvcc_cu12)
# echo "Using NVCC from: $NVCC_PATH"

# # 3. 設定 CUDA_HOME 與 PATH，並強制編譯安裝 mamba-ssm
# # 我們加入 --no-build-isolation 讓它能直接看到我們剛裝好的 nvcc
# CUDA_HOME=$NVCC_PATH PATH=$NVCC_PATH/bin:$PATH poetry run pip install mamba-ssm causal-conv1d


# light-t2m
poetry run pip uninstall -y torch torchvision torchaudio

poetry run pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121

poetry run pip install "https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.4.0/causal_conv1d-1.4.0+cu121torch2.3cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"


poetry run pip install "https://github.com/state-spaces/mamba/releases/download/v2.2.2/mamba_ssm-2.2.2+cu121torch2.3cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"



