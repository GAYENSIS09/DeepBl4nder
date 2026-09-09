import { MDXRenderer } from '@/components/MDXRenderer'

export const metadata = {
  title: 'Getting Started - DeepBl4nder',
  description: 'How to install and run DeepBl4nder on your machine.',
}

const mdxContent = `
# Getting Started

## What DeepBl4nder Is

DeepBl4nder is a multi-agent AI pipeline that transforms creative briefs into 3D scenes using Blender. Fourteen specialized agents collaborate through a cloud-based LLM router — generating narrative, storyboarding shots, directing scenes, writing Blender Python scripts, and evaluating quality — to produce rendered video from a single paragraph of text.

The system uses cloud LLM providers (Gemini, Groq, NVIDIA, OpenRouter, Cloudflare) rather than local models, so you do not need a specific GPU for language model inference. GPU hardware is only relevant if you want hardware-accelerated Blender rendering; the LLM layer runs entirely through cloud APIs.

## What You Need

Before installing DeepBl4nder, your system needs two fundamental capabilities: a modern Python runtime and at least one cloud LLM API key. Docker is optional but recommended for isolated Blender rendering.

**Python 3.12 or newer** is required because DeepBl4nder makes heavy use of async/await patterns, modern type hints, and recent improvements to the asyncio event loop. The agent runtime, the pipeline orchestrator, and the TUI all run as async coroutines, coordinating through Python's native concurrency primitives. Older Python versions lack the performance improvements and syntax features that make this coordination practical.

**At least one cloud LLM API key** is required. DeepBl4nder routes requests through a multi-provider LLM router built on \`litellm\`. You need at least one of the following keys configured in your environment:

- \`GEMINI_API_KEY\` — Google Gemini
- \`GROQ_API_KEY\` — Groq
- \`NVIDIA_API_KEY\` — NVIDIA NIM
- \`OPENROUTER_API_KEY\` — OpenRouter
- \`CLOUDFLARE_API_KEY\` + \`CLOUDFLARE_ACCOUNT_ID\` — Cloudflare Workers AI

The more providers you configure, the more resilient the system is — the router automatically falls back to the next provider if one fails.

**Docker** (optional) is recommended for running Blender in an isolated container with GPU access. This keeps generated scripts contained and prevents any issues from affecting your main system.

## Installation in Four Steps

The installation process is designed to be as straightforward as possible.

**Cloning the repository** gives you the full source code, including all 14 agents, the production pipeline, the LLM system, the TUI, and the 32 embedded skills. The repository is structured as a single Python package with optional extras for the TUI and development tools.

\`\`\`bash
git clone https://github.com/GAYENSIS09/DeepBl4nder.git
cd DeepBl4nder
\`\`\`

**Installing with pip** in editable mode means that any changes you make to the source code take effect immediately without reinstalling. The \`.[tui]\` extra pulls in Textual and its dependencies for the terminal interface. If you plan to contribute to the project, this editable installation is essential.

\`\`\`bash
pip install -e ".[tui]"
\`\`\`

**Configuring at least one API key** is the critical step that connects DeepBl4nder to the cloud LLM providers. Create a \`.env\` file in the project root (or export the variables in your shell) with at least one key:

\`\`\`bash
# At least one of these is required:
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
NVIDIA_API_KEY=your-nvidia-key
OPENROUTER_API_KEY=your-openrouter-key
CLOUDFLARE_API_KEY=your-cloudflare-key
CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
\`\`\`

You can also configure the router via \`~/.deepbl4nder/llm.json\` for advanced settings like provider priority, model selection rules, cooldown durations, and budget caps. See the LLM System documentation for details.

**Launching the TUI** starts the Textual terminal interface where you type creative briefs and watch agents work. The TUI connects to the agents through an in-process API, so there is no HTTP overhead between the interface and the agents.

\`\`\`bash
DeepBl4nder tui
\`\`\`

**Starting the Blender worker** (optional) brings up a Docker container with Blender 4.1 and FFmpeg pre-installed. This is needed for hardware-accelerated rendering. If you skip this step, the pipeline can still generate scripts and QA reports, but will not produce final rendered video.

\`\`\`bash
docker compose up -d blender-worker
\`\`\`

## Your First Production

Once the TUI is running, you are greeted by the Console screen — a dark, minimal interface with a text input at the bottom and a large output area above. This is where the magic begins.

Type a creative brief describing the scene you want to create. Be as specific or as vague as you like. The agents will interpret your words, build a narrative structure, plan the visual composition, generate Blender scripts, and produce rendered output — all from a single paragraph of text.

As the pipeline runs, you see each agent's reasoning unfold in real-time. The StoryAgent appears first, analyzing your brief for characters, setting, and emotional tone. Then the StoryboardAgent takes over, planning camera angles and shot transitions. The DirectorAgent synthesizes everything into a detailed scene specification. The BlenderAgent writes Python code that constructs the 3D scene. And the QAAgent evaluates the output, requesting revisions if the quality falls below the threshold.

The entire process typically takes between two and five minutes, depending on the complexity of your brief and the speed of your cloud LLM providers. When it completes, you find rendered video files, Blender scripts, and QA reports in the production output directory.

## What Happens Next

With DeepBl4nder running, you have several paths forward. The **Architecture** section explains how the 4-layer system is organized and why each design decision was made. The **Agents** section introduces you to the 14 specialized agents and their roles in the production pipeline. The **Pipeline** section walks through the complete flow from brief to final output, including the checkpoint system that protects against crashes and the budget tracking that prevents runaway costs.
`

export default function GettingStartedPage() {
  return <MDXRenderer source={mdxContent} />
}
