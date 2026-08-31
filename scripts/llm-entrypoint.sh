#!/usr/bin/env bash
# DeepBl4nder LLM Server — Entrypoint
# Telecharge les modeles manquants puis demarre le serveur.
set -euo pipefail

MODELS_DIR="${DeepBl4nder_MODELS_DIR:-/models}"
DEFAULT_MODEL="${DeepBl4nder_MODEL:-qwen3-8b}"

# ── Configuration des modeles ──────────────────────────────────────
declare -A MODEL_REPOS=(
    ["qwen3-4b"]="Qwen/Qwen3-4B-GGUF"
    ["qwen3-8b"]="Qwen/Qwen3-8B-GGUF"
)

declare -A MODEL_FILES=(
    ["qwen3-4b"]="Qwen3-4B-Q4_K_M.gguf"
    ["qwen3-8b"]="Qwen3-8B-Q4_K_M.gguf"
)

# ── Telechargement des modeles manquants ───────────────────────────
echo "=== DeepBl4nder LLM Server ==="
echo "Modeles dir: $MODELS_DIR"
echo "Modele par defaut: $DEFAULT_MODEL"
echo ""

for model_id in "${!MODEL_REPOS[@]}"; do
    repo="${MODEL_REPOS[$model_id]}"
    file="${MODEL_FILES[$model_id]}"
    target="$MODELS_DIR/$file"

    if [ -f "$target" ]; then
        echo "[OK] $model_id deja present : $target"
    else
        echo "[DL] Telechargement de $model_id depuis $repo..."
        mkdir -p "$MODELS_DIR"
        python3.12 -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='$repo',
    filename='$file',
    local_dir='$MODELS_DIR',
    local_dir_use_symlinks=False,
)
print(f'  -> {path}')
"
        echo "[OK] $model_id telecharge : $target"
    fi
done

echo ""
echo "Demarrage du serveur avec le modele $DEFAULT_MODEL..."
echo ""

# ── Demarrer llama-cpp-python ──────────────────────────────────────
exec python3.12 -m llama_cpp.server \
    --model "$MODELS_DIR/${MODEL_FILES[$DEFAULT_MODEL]}" \
    --host 0.0.0.0 \
    --port 8080 \
    --n_ctx 32768 \
    --n_gpu_layers -1 \
    --chat_format chatml
