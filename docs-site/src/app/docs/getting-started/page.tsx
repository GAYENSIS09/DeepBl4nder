import { MDXRenderer } from '@/components/MDXRenderer'

export const metadata = {
  title: 'Getting Started - DeepBl4nder',
  description: 'How to install and run DeepBl4nder on your machine.',
}

const mdxContent = `
# Getting Started

## The Promise of Local-First AI

DeepBl4nder was born from a conviction that creative AI should not depend on cloud services, API keys, or monthly subscriptions. When you write a story prompt, that prompt should stay on your machine. When your GPU renders a frame, no telemetry should leave your workstation. The entire pipeline — from natural language understanding to 3D scene generation — runs locally, using open-weight models that you download once and use forever.

This is not just a philosophical stance. It has practical consequences. Without network latency, your agents respond in milliseconds instead of seconds. Without API rate limits, you can run full productions without worrying about costs. Without cloud dependencies, your workflow continues even when your internet connection drops. The local-first approach means that the system is as fast as your GPU allows, as private as your hard drive, and as reliable as your own hardware.

## What You Need

Before installing DeepBl4nder, your system needs three fundamental capabilities: a modern Python runtime, an NVIDIA GPU for local inference, and Docker for isolating heavy workloads. Let me explain why each of these matters.

**Python 3.12 or newer** is required because DeepBl4nder makes heavy use of async/await patterns, modern type hints, and recent improvements to the asyncio event loop. The agent runtime, the pipeline orchestrator, and the TUI all run as async coroutines, coordinating through Python's native concurrency primitives. Older Python versions lack the performance improvements and syntax features that make this coordination practical.

**An NVIDIA GPU with at least 8GB of VRAM** is the heart of the system. The local LLM server runs Qwen3 models through llama-cpp-python, which needs to load the entire model weights into GPU memory. The smallest model (1.5B parameters) requires about 1.5GB, while the largest (8B) needs roughly 5.5GB. Blender's Cycles renderer also benefits from GPU acceleration, so having a capable NVIDIA card serves double duty. AMD GPUs are supported through HIP, and Apple Silicon through Metal, but NVIDIA with CUDA remains the primary target.

**Docker with NVIDIA Container Toolkit** provides the isolation layer that keeps the LLM server and the Blender worker separate from your main system. The LLM server runs in its own container with direct GPU access, and the Blender worker runs in another container with Blender headless and FFmpeg pre-installed. This separation means you can update one component without affecting the other, and it ensures that the heavy GPU work does not interfere with your desktop environment.

## Installation in Five Steps

The installation process is designed to be as straightforward as possible, though the first run will take some time due to model downloads. Here is what each step accomplishes and why it matters.

**Cloning the repository** gives you the full source code, including all 14 agents, the production pipeline, the LLM system, the TUI, and the 36+ embedded skills. The repository is structured as a single Python package with optional extras for the TUI and development tools.

\`\`\`bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder
\`\`\`

**Installing with pip** in editable mode means that any changes you make to the source code take effect immediately without reinstalling. The \`.[tui]\` extra pulls in Textual and its dependencies for the terminal interface. If you plan to contribute to the project, this editable installation is essential.

\`\`\`bash
pip install -e ".[tui]"
\`\`\`

**Downloading the models** is the most time-consuming step, as you are fetching approximately 10GB of quantized model weights from HuggingFace. These are GGUF-format files optimized for llama-cpp-python. You can download all three models at once, or start with just the 1.5B model for quick testing and add the larger ones later. The download is resumable, so interrupted downloads will continue from where they left off.

\`\`\`bash
python -m DeepBl4nder.llm.download --all
\`\`\`

**Starting Docker services** brings up two containers: the LLM server on port 8080 and the Blender worker. The LLM server loads the default model (typically the 8B for best quality) and exposes an OpenAI-compatible API. The Blender worker provides a headless Blender 4.1 environment with FFmpeg for video processing. Both containers have direct GPU access through the NVIDIA Container Toolkit.

\`\`\`bash
docker compose up -d
\`\`\`

**Launching the TUI** starts the Textual terminal interface where you type creative briefs and watch agents work. The TUI connects to the Docker services through an in-process API, so there is no HTTP overhead between the interface and the agents.

\`\`\`bash
DeepBl4nder tui
\`\`\`

## Your First Production

Once the TUI is running, you are greeted by the Console screen — a dark, minimal interface with a text input at the bottom and a large output area above. This is where the magic begins.

Type a creative brief describing the scene you want to create. Be as specific or as vague as you like. The agents will interpret your words, build a narrative structure, plan the visual composition, generate Blender scripts, and produce rendered output — all from a single paragraph of text.

As the pipeline runs, you see each agent's reasoning unfold in real-time. The StoryAgent appears first, analyzing your brief for characters, setting, and emotional tone. Then the StoryboardAgent takes over, planning camera angles and shot transitions. The DirectorAgent synthesizes everything into a detailed scene specification. The BlenderAgent writes Python code that constructs the 3D scene. And the QAAgent evaluates the output, requesting revisions if the quality falls below the threshold.

The entire process typically takes between two and five minutes, depending on the complexity of your brief and the speed of your GPU. When it completes, you find rendered video files, Blender scripts, and QA reports in the production output directory.

## Understanding the GPU Backend

DeepBl4nder automatically detects your GPU backend at startup. For NVIDIA cards, it prefers OptiX (the hardware-accelerated ray tracing API) over CUDA. For AMD GPUs, it uses HIP. For Apple Silicon, it uses Metal. This detection happens transparently — you do not need to configure anything. The system simply uses the fastest available backend for your hardware.

If you have multiple GPUs, you can control which ones are used through the \`CUDA_VISIBLE_DEVICES\` environment variable. This is particularly useful if you want to dedicate one GPU to the LLM server and another to Blender rendering, preventing memory contention between the two workloads.

## What Happens Next

With DeepBl4nder running, you have several paths forward. The **Architecture** section explains how the 4-layer system is organized and why each design decision was made. The **Agents** section introduces you to the 14 specialized agents and their roles in the production pipeline. The **Pipeline** section walks through the complete flow from brief to final output, including the checkpoint system that protects against crashes and the budget tracking that prevents runaway costs.
`

export default function GettingStartedPage() {
  return <MDXRenderer source={mdxContent} />
}
