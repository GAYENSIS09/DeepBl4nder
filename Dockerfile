# DeepBl4nder : image runtime (Spec §5).
#
# La topologie §5 prévoit des services internes (planner, workflow engine,
# scheduler, harness) et des workers typés par domaine. Cette image de base
# contient le paquet Python + Blender (worker) et expose la commande `DeepBl4nder`.
#
# Pour utiliser un Blender plus récent, surcharger BLENDER_EXE (ADR-009):
#   docker build --build-arg BLENDER_EXE=/opt/blender/blender .
FROM python:3.12-slim

ARG BLENDER_EXE=blender

RUN apt-get update \
    && apt-get install -y --no-install-recommends blender ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY DeepBl4nder ./DeepBl4nder
RUN pip install --no-cache-dir .

ENV BLENDER_EXE=${BLENDER_EXE} \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["DeepBl4nder"]
