FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUDIO_SEPARATOR_MODEL_DIR=/data/models

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# CPU Spaces cannot use CUDA. Install CPU-only PyTorch first to avoid pulling
# hundreds of MB of unused CUDA/NVIDIA wheels from the default PyPI index.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN mkdir -p /data/models /data/jobs
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
