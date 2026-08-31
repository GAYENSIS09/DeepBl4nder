import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'LLM System - DeepBl4nder',
  description: 'The cascade routing system, task classification, and local model management.',
}

const section1 = `
# LLM System

## The Case for Local Language Models

Running language models locally is not just about privacy — though privacy matters enormously when your creative briefs contain proprietary stories and your Blender scripts contain trade secrets. The deeper reason for local inference is **determinism and control**. When you call a cloud API, you are at the mercy of the provider's rate limits, availability, and model updates. A model that works perfectly today might behave differently tomorrow after an silent update. With local models, you control the exact version, the exact configuration, and the exact behavior.

DeepBl4nder uses three Qwen3 models in GGUF format, served through llama-cpp-python. These are not the largest or most capable models in the world — they are the right models for the job. The 1.5B model handles routing and classification with minimal latency. The 4B model handles narrative planning and dialogue generation. The 8B model handles code generation and complex reasoning. Each model is sized to fit comfortably in GPU memory alongside the other components that need it.

## The Cascade Philosophy

The cascade routing system embodies a simple but powerful idea: **use the smallest model that can do the job well**. This is not about saving tokens or reducing costs — with local models, token cost is essentially zero. It is about speed and quality.

The 1.5B model responds in milliseconds. The 4B model responds in a second or two. The 8B model takes several seconds. For a routing decision — "which category does this task belong to?" — waiting several seconds for the 8B model is wasteful when the 1.5B model can make the same decision in a fraction of the time. For code generation — "write a Blender script that creates this scene" — the 8B model's additional capability produces meaningfully better code than the 4B model.

The cascade approach gives you the speed of the small model for simple tasks and the quality of the large model for complex tasks. The system selects the appropriate model automatically, so you never have to think about which model to use. And if a model fails — produces invalid output, times out, or encounters an error — the system automatically escalates to the next heavier model. This escalation is transparent: you see the final output, not the intermediate failures.

## Task Classification Without Language Models

One of the most interesting design decisions in DeepBl4nder's LLM system is that **task classification does not use a language model**. The TaskClassifier is a purely heuristic system that categorizes tasks based on keyword matching, regex patterns, and message history analysis.

This is a deliberate choice. Using a language model to classify tasks would mean spending tokens and time on a decision that can be made faster and more reliably with simple rules. The classifier checks for coding keywords ("import", "bpy", "def", "class"), reasoning keywords ("analyze", "plan", "evaluate"), and general keywords ("write", "describe", "explain"). It applies regex patterns to detect code snippets. It analyzes the message history to boost coding scores when previous messages contain code indicators. And it boosts the FAST category for short messages of five words or fewer.

The result is a classification system that runs in microseconds, costs zero tokens, and is deterministic — the same input always produces the same classification. This determinism is important because it means the system's behavior is predictable and debuggable. You can trace exactly why a particular task was routed to a particular model, which is essential for understanding and optimizing the system's performance.

Here is how a task gets classified:

\`\`\`python
from DeepBl4nder.llm.classifier import TaskClassifier

classifier = TaskClassifier()
complexity = classifier.classify("Generate a medieval castle scene with fog")
# Returns: ComplexityLevel.COMPLEX -> routes to Qwen3-8B
\`\`\`
`

const heuristicChart = `graph LR
    H1["Token Count"] --> SCORE["Complexity Score"]
    H2["Code Blocks"] --> SCORE
    H3["Schema Refs"] --> SCORE
    H4["Conversation Depth"] --> SCORE
    SCORE -->|"< 5"| LITE["1.5B Model"]
    SCORE -->|"5-15"| MID["4B Model"]
    SCORE -->|"> 15"| HEAVY["8B Model"]`

const section2 = `
## The Model Server

The ModelServer manages a llama-cpp-python subprocess that loads and serves one model at a time. The server exposes an OpenAI-compatible API, which means any tool or library that works with OpenAI's API can also work with the local server.

Starting the server is a heavyweight operation — it involves loading the model weights from disk into GPU memory, which can take anywhere from a few seconds for the 1.5B model to nearly a minute for the 8B model. The server stays running between requests, so this startup cost is paid only once per model load.

When the cascade router determines that a different model is needed, the server performs a hot swap. It shuts down the current subprocess, starts a new one with the different model, and waits for the health check to pass. This swap takes a few seconds, during which requests are queued. The swap is necessary because llama-cpp-python does not support dynamic model switching within a single process.

The server auto-detects the GPU backend at startup. For NVIDIA GPUs, it prefers OptiX (NVIDIA's hardware-accelerated ray tracing API) over CUDA. For AMD GPUs, it uses HIP. For Apple Silicon, it uses Metal. This detection happens transparently — you do not need to configure anything. The server simply uses the fastest available backend for your hardware.

## Model Selection and Escalation

When an agent makes an LLM call, the system follows a precise sequence of decisions. First, the TaskClassifier categorizes the task. Then the CascadeRouter selects the lightest model that supports that category. The system ensures the selected model's server is running, sends the request, and validates the response.

If the response is invalid — the model produces malformed JSON, returns an empty response, or times out — the system escalates to the next heavier model. The 1.5B model escalates to the 4B model. The 4B model escalates to the 8B model. The 8B model has no heavier model to escalate to, so a failure at that level raises an error.

The escalation chain is recorded in the router's history. If a particular model fails repeatedly for a specific category, the router learns to skip it for future requests in that category. This adaptive behavior means the system becomes more efficient over time, avoiding models that are known to struggle with certain types of tasks.
`

const cascadeChart = `graph TB
    REQ["Agent Request"] --> CLASSIFY["TaskClassifier"]
    CLASSIFY -->|"trivial"| M1["Qwen3-1.5B"]
    CLASSIFY -->|"simple"| M2["Qwen3-4B"]
    CLASSIFY -->|"complex"| M3["Qwen3-8B"]
    M1 -->|"failure"| ESC1["Escalate"]
    ESC1 --> M2
    M2 -->|"failure"| ESC2["Escalate"]
    ESC2 --> M3
    M1 --> RESULT["Response"]
    M2 --> RESULT
    M3 --> RESULT`

const section3 = `
## The Unified Interface

All agents interact with the LLM system through a single \`LLMClient\` interface. This interface handles classification, model selection, server management, escalation, response validation, and caching — all in a single method call. The agent does not need to know which model is being used, how the server is managed, or what happens when a model fails. It simply sends a request and receives a response.

The LLMClient also caches responses for one hour. If an agent makes the same request twice within an hour, the cached response is returned without hitting the model. This caching is particularly useful during revision loops, where the same context might be sent multiple times with minor modifications. The cache key includes the full message history, so only identical requests are served from cache.

## VRAM Management

With only one model loaded at a time, VRAM management is straightforward but critical. The 8B model needs about 5.5GB of VRAM. Blender's Cycles renderer needs additional VRAM for the scene being rendered. If both the LLM server and the Blender worker are running on the same GPU, you need at least 8GB of VRAM to accommodate both.

For systems with limited VRAM, the Docker configuration allows you to run the LLM server on one GPU and the Blender worker on another. This separation ensures that neither component starves the other of memory. The \`CUDA_VISIBLE_DEVICES\` environment variable controls which GPU each container uses.

The system monitors VRAM usage and reports it through the TUI's status bar. If VRAM usage approaches the limit, the system can automatically switch to a smaller model to free up memory. This adaptive sizing ensures that the system remains responsive even under memory pressure.
`

export default function LLMSystemPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={heuristicChart} title="Model Selection Heuristics" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={cascadeChart} title="Cascade Routing Flow" />
      <MDXRenderer source={section3} />
    </>
  )
}
