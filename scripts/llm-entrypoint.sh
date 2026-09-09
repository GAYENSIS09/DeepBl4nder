#!/usr/bin/env bash
# DeepBl4nder LLM Server — Entrypoint
# Downloads missing models then starts the server.
set -euo pipefail

MODELS_DIR="${DeepBl4nder_MODELS_DIR:-/models}"
DEFAULT_MODEL="${DeepBl4nder_MODEL:-}"

# Use venv python if available, else system python3.12
PYTHON="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python3.12}"
PYTHON="${PYTHON:-python3.12}"

# ── Model configuration ────────────────────────────────────────────
declare -A MODEL_REPOS=(
    ["llama-3.2-1b"]="bartowski/Llama-3.2-1B-Instruct-GGUF"
    ["gemma-3-1b"]="ggml-org/gemma-3-1b-it-GGUF"
    ["qwen3.5-0.8b"]="bartowski/Qwen_Qwen3.5-0.8B-GGUF"
    ["smollm3-3b"]="jc-builds/SmolLM3-3B-Instruct-GGUF"
    ["granite-4.1-3b"]="ibm-granite/granite-4.1-3b-GGUF"
    ["ministral-3-3b"]="mistralai/Ministral-3-3B-Instruct-2512-GGUF"
    ["llama-3.2-3b"]="bartowski/Llama-3.2-3B-Instruct-GGUF"
    ["gemma-3-4b"]="ggml-org/gemma-3-4b-it-GGUF"
    ["qwen3.5-2b"]="Qwen/Qwen3.5-2B-GGUF"
    ["qwen3-vl-4b"]="Qwen/Qwen3-VL-4B-Instruct-GGUF"
    ["qwen3-4b"]="Qwen/Qwen3-4B-GGUF"
    ["qwen3-8b"]="Qwen/Qwen3-8B-GGUF"
    ["qwen2.5-coder-1.5b"]="Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF"
    ["qwen2.5-coder-7b"]="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"
    ["deepseek-r1-1.5b"]="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
    ["phi-4-mini-reasoning"]="bartowski/microsoft_Phi-4-mini-reasoning-GGUF"
    ["deepseek-r1-7b"]="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B-GGUF"
)

declare -A MODEL_FILES=(
    ["llama-3.2-1b"]="Llama-3.2-1B-Instruct-Q4_K_M.gguf"
    ["gemma-3-1b"]="gemma-3-1b-it-Q4_K_M.gguf"
    ["qwen3.5-0.8b"]="Qwen_Qwen3.5-0.8B-Q4_K_M.gguf"
    ["smollm3-3b"]="SmolLM3-3B-Q4_K_M.gguf"
    ["granite-4.1-3b"]="granite-4.1-3b-Q4_K_M.gguf"
    ["ministral-3-3b"]="Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
    ["llama-3.2-3b"]="Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    ["gemma-3-4b"]="gemma-3-4b-it-Q4_K_M.gguf"
    ["qwen3.5-2b"]="Qwen3.5-2B-Q4_K_M.gguf"
    ["qwen3-vl-4b"]="Qwen3-VL-4B-Instruct-Q4_K_M.gguf"
    ["qwen3-4b"]="Qwen3-4B-Q4_K_M.gguf"
    ["qwen3-8b"]="Qwen3-8B-Q4_K_M.gguf"
    ["qwen2.5-coder-1.5b"]="Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf"
    ["qwen2.5-coder-7b"]="Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"
    ["deepseek-r1-1.5b"]="DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
    ["phi-4-mini-reasoning"]="microsoft_Phi-4-mini-reasoning-Q4_K_M.gguf"
    ["deepseek-r1-7b"]="DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"
)

# Presence of the config file (written by the TUI) overrides the env-less default
DEFAULT_MODEL="${DEFAULT_MODEL:-$(if [ -f "${DeepBl4nder_CONFIG_FILE:-$HOME/.deepbl4nder/llm.json}" ]; then "$PYTHON" -c "
import json, os
try:
    d = json.load(open(os.environ.get('DeepBl4nder_CONFIG_FILE') or os.path.expanduser('~/.deepbl4nder/llm.json')))
    print(d.get('default_model', '') if isinstance(d, dict) else '')
except Exception:
    print('')
" 2>/dev/null || true; fi)}"
DEFAULT_MODEL="${DEFAULT_MODEL:-qwen3-8b}"

# Additional models to preload (comma-separated), e.g. DeepBl4nder_PRELOAD=qwen3-4b,llama-3.2-1b
PRELOAD_MODELS=()
if [ -n "${DeepBl4nder_PRELOAD:-}" ]; then
    IFS=',' read -r -a PRELOAD_MODELS <<< "$DeepBl4nder_PRELOAD"
fi

# ── GPU check ──────────────────────────────────────────────────────
echo "=== DeepBl4nder LLM Server ==="
if command -v nvidia-smi &>/dev/null; then
    echo "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true
else
    echo "WARNING: nvidia-smi not found — GPU acceleration may not work"
fi
echo ""

# ── Download missing models ────────────────────────────────────────
echo "Models dir: $MODELS_DIR"
echo "Default model: $DEFAULT_MODEL"
echo ""

if [ -z "${MODEL_REPOS[$DEFAULT_MODEL]:-}" ]; then
    echo "ERROR: unknown model '$DEFAULT_MODEL'."
    echo "Available: ${!MODEL_REPOS[*]}"
    exit 1
fi

download_if_missing() {
    local model_id="$1"
    local repo="${MODEL_REPOS[$model_id]}"
    local file="${MODEL_FILES[$model_id]}"
    local target="$MODELS_DIR/$file"

    if [ -f "$target" ]; then
        echo "[OK] $model_id present: $target"
    else
        echo "[DL] Downloading $model_id from $repo..."
        mkdir -p "$MODELS_DIR"
        "$PYTHON" -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='$repo',
    filename='$file',
    local_dir='$MODELS_DIR',
    local_dir_use_symlinks=False,
)
print(f'  -> {path}')
"
        echo "[OK] $model_id downloaded: $target"
    fi
}

download_if_missing "$DEFAULT_MODEL"
for preload in "${PRELOAD_MODELS[@]}"; do
    preload="${preload// /}"
    [ -n "$preload" ] && download_if_missing "$preload"
done

echo ""
echo "Starting server with model $DEFAULT_MODEL..."
echo ""

# ── Start llama-cpp-python ─────────────────────────────────────────
exec "$PYTHON" -m llama_cpp.server \
    --model "$MODELS_DIR/${MODEL_FILES[$DEFAULT_MODEL]}" \
    --host 0.0.0.0 \
    --port 8080 \
    --n_ctx 32768 \
    --n_gpu_layers -1 \
    --chat_format "${DeepBl4nder_CHAT_FORMAT:-chatml}"