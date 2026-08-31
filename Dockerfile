# DeepBl4nder — Image de base
#
# Contient Python + Blender headless pour le rendu.
# Utilisez Dockerfile.worker pour l'exécution Blender.
# Utilisez Dockerfile.llm pour le serveur LLM local.

FROM python:3.12-slim AS base

ARG BLENDER_EXE=blender

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       libgl1 \
       libglu1-mesa \
       libxrender1 \
       libxext6 \
       libxi6 \
       libxfixes3 \
       libxcb1 \
       libx11-6 \
       libsm6 \
       libice6 \
       libxxf86vm1 \
       libfontconfig1 \
       libfreetype6 \
       libxrandr2 \
       libxcursor1 \
       libxinerama1 \
       git \
       curl \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-deps . || true

COPY DeepBl4nder ./DeepBl4nder
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir .

ENV BLENDER_EXE=${BLENDER_EXE} \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["DeepBl4nder"]
