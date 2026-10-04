FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 sox \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY deploy/tts/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from qwen_tts import Qwen3TTSModel; import torch, torchaudio; print(torch.__version__, torchaudio.__version__)"
COPY deploy/tts/server.py ./server.py
EXPOSE 1813
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "1813", "--workers", "1"]
