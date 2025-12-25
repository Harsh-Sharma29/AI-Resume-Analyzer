FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "setuptools<74" wheel && \
    pip install --no-cache-dir -r requirements.txt


CMD ["sh", "-c", "streamlit run App.py --server.address=0.0.0.0 --server.port=${PORT:-10000}"]
