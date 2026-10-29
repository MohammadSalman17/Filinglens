FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ANONYMIZED_TELEMETRY=False \
    HF_HOME=/home/user/.cache/huggingface \
    PERSIST_CHATS=0 \
    API_URL=http://127.0.0.1:8000/ask_stream

# Non-root user (Hugging Face Spaces runs containers as user id 1000)
RUN useradd -m -u 1000 user
WORKDIR /app

# 1. CPU-only torch (much smaller than the default GPU build)
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
    || pip install torch==2.14.1

# 2. All other libraries, same versions as on your laptop
COPY requirements-deploy.txt .
RUN pip install -r requirements-deploy.txt

# 3. Download the two models during the build, so the first question is not slow
USER user
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# 4. Your code and the vector database
COPY --chown=user src ./src
COPY --chown=user vectorstore ./vectorstore
COPY --chown=user start.py .

EXPOSE 7860
CMD ["python", "start.py"]
