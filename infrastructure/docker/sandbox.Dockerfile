# Imagem do backend "docker" do sandbox: Python + pytest e Node.js, sem código da plataforma.
FROM python:3.12-slim
RUN pip install --no-cache-dir "pytest>=9,<10" \
 && apt-get update && apt-get install -y --no-install-recommends nodejs npm \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
