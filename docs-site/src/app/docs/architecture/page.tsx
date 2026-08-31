import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Architecture - DeepBl4nder',
  description: 'The design philosophy and technical architecture of DeepBl4nder.',
}

const section1 = `
# Architecture

## Why Architecture Matters

Every software system makes implicit promises about how it will behave under pressure, how it will grow over time, and how contributors will navigate its internals. The architecture of DeepBl4nder is not an accident — it is the result of deliberate choices about what matters most in a local-first AI production pipeline. Understanding these choices helps you not only use the system effectively but also contribute meaningfully to its evolution.

The core insight behind DeepBl4nder's architecture is that **separation of concerns is not just a software engineering principle — it is a survival strategy for complex AI systems**. When you have 14 agents, each with different skills, different context requirements, and different output formats, the only way to keep the system manageable is to give each component a clear, bounded responsibility.

## The Four Layers

The system is organized into four distinct layers, each with a specific purpose and a well-defined interface to the layers above and below it.

**The User Interface Layer** is what you interact with directly. It consists of the Textual terminal UI and the command-line interface. This layer has one job: translate human intentions into machine-executable instructions and present machine outputs in a human-readable format. The TUI connects to the agent layer through an embedded API — not an HTTP server, not a message queue, but a direct in-process call. This means there is zero serialization overhead between your keystrokes and the agents that process them.

**The Agent Layer** contains the 14 specialized NOOA agents. Each agent is an expert in one aspect of the production pipeline: one understands narrative structure, another understands camera composition, another understands Blender's Python API. These agents do not compete for resources or share mutable state. They communicate through typed domain objects — a StorySpec flows from the StoryAgent to the StoryboardAgent, a SceneSpec flows from the DirectorAgent to the BlenderAgent. This typed communication means that errors are caught at the boundary between agents, not deep inside some opaque processing step.

**The LLM Layer** handles all language model interactions through a cascade routing system. Instead of sending every request to the largest, most expensive model, DeepBl4nder classifies each task and routes it to the smallest model that can handle it effectively. Simple classification tasks go to the 1.5B model. Narrative planning goes to the 4B model. Code generation goes to the 8B model. If a model fails or produces an invalid response, the system automatically escalates to the next heavier model. This cascade approach means you get the quality of the 8B model for code generation while using the 1.5B model for the majority of simple routing decisions — saving both time and VRAM.

**The Worker Layer** manages the actual execution of generated code. When the BlenderAgent produces a Python script, that script does not run in the same process as the agents. It runs in an isolated Docker container with its own GPU access, its own filesystem, and its own resource limits. This isolation is critical: if a generated script crashes or consumes excessive memory, it does not bring down the entire system. The worker layer also handles multiple rendering engines — Blender, Unreal Engine 5, Godot, and AI Video — each running in its own container with engine-specific configuration.
`

const chart1 = `graph TB
    subgraph UI["UI Layer"]
        TUI["TUI (Textual)"]
        CLI["CLI"]
    end
    subgraph Agent["Agent Layer"]
        NOOA["NOOA Framework"]
        AGENTS["14 Agents"]
        SKILLS["36+ Skills"]
    end
    subgraph LLM["LLM Layer"]
        CLASSIFIER["TaskClassifier"]
        ROUTER["CascadeRouter"]
        MODELS["Qwen3 1.5B/4B/8B"]
    end
    subgraph Worker["Worker Layer"]
        DOCKER["Docker Services"]
        BLENDER["Blender Bridge"]
        UE5["Unreal Bridge"]
        GODOT["Godot Bridge"]
    end
    UI --> Agent
    Agent --> LLM
    Agent --> Worker`

const section2 = `
## The NOOA Foundation

DeepBl4nder does not reimplement its agent runtime. It builds on **NOOA 0.0.8**, a purpose-built framework for orchestrating AI agents. This is a deliberate architectural decision with profound implications.

By using NOOA as the foundation, DeepBl4nder inherits a battle-tested agent loop, sophisticated context management, event streaming, optional memory persistence, and distributed tracing — all features that would take months to implement from scratch and years to stabilize. The NOOA framework handles the mechanical aspects of agent execution: looping through turns, managing conversation history, invoking the LLM, parsing responses, and handling errors. DeepBl4nder's contribution is the domain-specific intelligence layered on top.

The \`BaseAgent\` class extends NOOA's \`Agent\` with capabilities specific to 3D production: skill management (loading domain knowledge about Blender, cinematography, storytelling), schema injection (using TF-IDF search to find relevant domain types), context pruning (fitting everything within token budgets), and prompt caching (separating stable prefix blocks from volatile suffix blocks for KV cache optimization). These extensions are possible because NOOA provides clean extension points — it was designed to be composed with domain-specific logic, not to be a monolithic framework.

## The Factory Pattern

All 14 agents are constructed through a single function: \`build_agents()\`. This is not just a convenience — it is a architectural constraint that ensures consistency. Every agent shares the same LLM client instance, which means model selection, caching, and budget tracking happen at a single point of control. If you want to switch from the 8B model to a different model, you change one line in the factory and all 14 agents adapt.

The factory also ensures that agents are constructed in a known order with known dependencies. The StoryAgent does not depend on the BlenderAgent, but the DirectorAgent depends on both the StoryAgent and the StoryboardAgent. The factory makes these dependency relationships explicit and enforceable at construction time, not at runtime when a missing dependency would cause a cryptic error deep in the pipeline.

## Fail-Closed Security

When an AI system generates code that will be executed on your machine, security is not optional — it is existential. DeepBl4nder takes a **fail-closed** approach to generated code: every Blender Python script passes through an AST (Abstract Syntax Tree) validator before execution.

The validator checks the script against a set of security policies defined in \`CodePolicy\`. It verifies that the script only imports allowed modules (\`bpy\`, \`mathutils\`, \`math\`), does not call forbidden builtins (\`exec\`, \`eval\`, \`compile\`), does not invoke system commands (\`subprocess\`, \`os.system\`), and does not exceed a maximum source length. If any of these checks fail, the script is never executed — period.

Beyond security, the validator also enforces quality standards. It checks that the script sets up file paths correctly, specifies a render engine, creates at least one material, configures camera positioning, and enables denoising. These are not arbitrary rules — they are the patterns that distinguish a working Blender script from one that silently produces black frames.

The fail-closed philosophy extends to the entire pipeline. If the QA agent finds that a generated script does not meet quality thresholds, it does not silently pass the output downstream. It generates a \`RevisionSpec\` that targets the specific agent responsible for the deficiency, and the pipeline loops back to that agent with the feedback. This revision loop continues until the output meets the quality bar or the maximum number of revisions is reached.

## Checkpoint and Resume

Production pipelines are fragile by nature. A GPU can run out of memory, a Docker container can crash, a user can accidentally close their terminal. DeepBl4nder handles these failures through a checkpoint system that saves the output of each pipeline step to disk.

The checkpoint system is more sophisticated than simple file saving. Each checkpoint includes a fingerprint of its inputs — a hash of the creative brief, a hash of the scene specification. When the pipeline resumes after a crash, it compares the current fingerprint against the saved fingerprint. If they match, the checkpoint is still valid and can be reused. If they do not match (because the user modified the brief, for example), the checkpoint is invalidated and the step is re-executed.

This fingerprint-based invalidation means that changes cascade correctly through the pipeline. If you modify the creative brief, all downstream steps are invalidated. If you modify only the scene specification, only the steps that depend on it are invalidated. The system never silently uses stale data.

## Context Management Philosophy

Language models have finite context windows. DeepBl4nder's 8B model supports 32K tokens, which sounds generous until you realize that a single agent's prompt — system instructions, loaded skills, domain schemas, conversation history, and dynamic context — can easily exceed that limit. The context management system exists to make intelligent decisions about what to keep and what to discard.

The approach is multi-layered. First, the \`ContextInjector\` adds runtime variables like recent pipeline events and QA feedback. Then the \`ContextPruner\` deduplicates content by hash, truncates each context type to its token budget, and summarizes content that exceeds its limit. Finally, the \`PromptCacheManager\` separates stable prefix blocks (system prompt, skill summaries) from volatile suffix blocks (loaded skills, dynamic context) to maximize KV cache hits on the LLM provider.

This layered approach means that agents always have access to the most important context within their token budget, while less critical information is summarized or truncated gracefully. The system never silently drops context — it makes explicit decisions about what to keep based on token budgets and content relevance.
`

const chart2 = `graph LR
    BRIEF["Creative Brief"] -->|"text"| STORY["StorySpec"]
    STORY -->|"acts, beats"| BOARD["StoryboardSpec"]
    BOARD -->|"shots, camera"| SCENE["SceneSpec"]
    SCENE -->|"env, characters"| SCRIPT["Python Script"]
    SCRIPT -->|"execute"| RENDER["Rendered Output"]
    RENDER -->|"evaluate"| QA["QA Report"]
    QA -->|"revise"| SCRIPT`

const section3 = `
## Parallel Post-Production

After the QA agent approves the generated scripts and animations, the pipeline enters post-production. This phase runs multiple tasks concurrently: rendering, music composition, sound design, audio mixing, localization, and compositing. These tasks are independent — they do not depend on each other's outputs — so running them in parallel dramatically reduces total production time.

The parallelism is controlled through async semaphores. LLM calls are limited to two concurrent requests to prevent GPU memory exhaustion. GPU rendering is limited to four concurrent shots to avoid overwhelming the graphics card. Post-production tasks have no concurrency limit because they primarily use CPU resources or external tools like FFmpeg.

This controlled parallelism is a practical compromise between speed and resource management. Without limits, the system would attempt to run all 14 agents simultaneously, all rendering tasks at once, and all post-production in parallel — which would quickly exhaust GPU memory and cause cascading failures. The semaphore approach gives you the speed benefits of parallelism while respecting the physical constraints of your hardware.
`

export default function ArchitecturePage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={chart1} title="4-Layer Architecture" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={chart2} title="Data Flow" />
      <MDXRenderer source={section3} />
    </>
  )
}
