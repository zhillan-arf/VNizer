FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 sox \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY deploy/tts/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY deploy/tts/server.py ./server.py
EXPOSE 1813
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "1813", "--workers", "1"]
