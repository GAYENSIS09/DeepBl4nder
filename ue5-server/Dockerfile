# DeepBlender UE5 Server — REST API for Unreal Engine 5
#
# Ce serveur FastAPI communique avec l'éditeur UE5 via le Python API.
# Il doit tourner DANS un environnement où UE5 est installé.
#
# Usage:
#   docker build -t deepblender/ue5-server:latest .
#   docker run --rm -p 8080:8080 deepblender/ue5-server:latest

FROM ubuntu:22.04

# UE5 dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    libx11-6 \
    libxcursor1 \
    libxinerama1 \
    libxrandr2 \
    libxi6 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libasound2 \
    libpulse0 \
    libdbus-1-3 \
    libglib2.0-0 \
    libfontconfig1 \
    libfreetype6 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
WORKDIR /ue5-server
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy server code
COPY . .

EXPOSE 8080

ENV PYTHONUNBUFFERED=1 \
    UE5_EXE=/opt/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "server.py"]
