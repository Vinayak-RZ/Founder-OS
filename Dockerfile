FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

# Build tools needed by a few wheels (e.g. onnxruntime/fastembed). Removed after install
# stays small because we only keep the slim base.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data/ holds the SQLite DB + backups; mount it as a volume so the
# brain survives container rebuilds.
RUN mkdir -p data
VOLUME ["/app/data"]

CMD ["python", "main.py"]
