import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Production Pipeline - DeepBl4nder',
  description: 'The complete production flow from creative brief to final output.',
}

const section1 = `
# Production Pipeline

## The Journey from Brief to Screen

A production pipeline is a sequence of transformations, each one taking the output of the previous step and refining it into something more concrete, more detailed, and closer to the final result. DeepBl4nder's pipeline begins with a few sentences of natural language and ends with rendered video, composed music, and mixed audio. Understanding how this journey unfolds — and what safeguards exist along the way — is essential for using the system effectively.

The pipeline is orchestrated by the \`PipelineRunner\`, which manages the flow of data between agents, enforces quality gates, handles crashes through checkpointing, and tracks costs through budget enforcement. The runner does not just execute steps in sequence — it manages a complex graph of dependencies, parallel tasks, and revision loops that together produce the final output.

## The Nine-Step Journey

Every production follows the same nine-step journey, though the specific agents and configurations may vary depending on the engine and complexity of the brief.

**Story Generation** is the first step. The StoryAgent reads the creative brief and produces a StorySpec — a structured narrative with acts, beats, characters, dialogue, and themes. This step transforms free-form human intention into a structured format that subsequent agents can process programmatically.

**Storyboard Planning** follows. The StoryboardAgent reads the StorySpec and produces a StoryboardSpec — an ordered sequence of shots with camera angles, movements, transitions, and timing. This step translates the abstract narrative into concrete visual planning.

**Human-In-The-Loop Approval** is the first quality gate. After the storyboard is generated, the pipeline pauses and waits for human approval. The user can approve the storyboard, request changes, or provide additional context. This pause is not just a formality — it is the moment where human creative vision intersects with machine execution. The pipeline will not proceed past this point without explicit approval, ensuring that the machine's interpretation aligns with the human's intent.

**Scene Direction** is where the DirectorAgent takes over. It reads the creative brief, the story, and the storyboard, and synthesizes them into a SceneSpec — a complete technical specification for the 3D scene. This is the most complex single step in the pipeline, as the DirectorAgent must make hundreds of creative decisions about environment, lighting, camera placement, and character positioning.

**Character and Environment Design** run in parallel. The CharacterDesignerAgent creates detailed specifications for each character in the scene. The EnvironmentArtistAgent designs the world they inhabit. These steps run concurrently because they are independent — the character design does not depend on the environment design, and vice versa.

**Blender Script Generation** is where the BlenderAgent produces the actual Python code that constructs the 3D scene. The agent reads the SceneSpec, loads relevant skills (modeling, shading, lighting, rendering), and generates a complete Blender Python script. It also handles asset management — downloading HDRI maps from PolyHaven and character models from Quaternius.

**Quality Assessment** is the critical quality gate. The QAAgent evaluates the generated script against the SceneSpec across four dimensions: technical correctness, visual quality, continuity, and semantic fidelity. If the score is above 70, the pipeline proceeds. If the score is below 70, a revision loop begins.

**Post-Production** runs multiple tasks concurrently. Rendering, music composition, sound design, audio mixing, localization, and compositing all happen in parallel because they are independent. This parallelism dramatically reduces total production time — a production that would take 30 minutes sequentially might complete in 10 minutes with parallel post-production.

**Final Review** is the last quality gate. The ReviewAgent examines the complete output — rendered video, mixed audio, composited effects — and approves or rejects the final result. This agent has the broadest perspective, seeing the entire production rather than individual components.
`

const chart1 = `graph TB
    START["Start Pipeline"] --> PARSE["Parse Brief"]
    PARSE --> STORY["StoryAgent"]
    STORY --> BOARD["StoryboardAgent"]
    BOARD --> DIR["DirectorAgent"]
    DIR --> BLEND["BlenderAgent"]
    BLEND --> QA["QAAgent"]
    QA -->|"score < 70"| REVISION["RevisionSpec"]
    REVISION -->|"target Agent"| BLEND
    QA -->|"score >= 70"| POST["Post-Production"]
    POST --> AUDIO["Audio Pipeline"]
    POST --> COMP["Compositing"]
    POST --> LOC["Localization"]
    AUDIO --> FINAL["Final Output"]
    COMP --> FINAL
    LOC --> FINAL`

const section2 = `
## The Revision Loop

When the QA agent identifies issues, the pipeline does not simply fail and ask the user to start over. Instead, it enters a revision loop — a targeted feedback cycle that addresses specific deficiencies.

The QA agent generates a RevisionSpec that identifies the target agent (Director or Blender), the specific issues found, and the recommended fixes. The ContextInjector then adds this feedback to the target agent's context. The agent regenerates its output with the feedback in mind, and the QA agent evaluates the new output.

This loop continues until the score exceeds 70 or the maximum number of revisions is reached. The maximum is configurable, but the default of three revisions is usually sufficient. Most revisions converge within two iterations — the first revision fixes the major issues, and the second revision addresses the remaining minor ones.

The revision loop is what makes DeepBl4nder robust in practice. Without it, a single mistake by any agent would require starting the entire production from scratch. With it, the system can recover from errors gracefully, producing high-quality output even when individual agents make mistakes.

## Checkpointing and Crash Recovery

Production pipelines are inherently fragile. A GPU can run out of memory. A Docker container can crash. A user can accidentally close their terminal. DeepBl4nder handles these failures through a checkpoint system that saves the output of each pipeline step to disk.

Each checkpoint includes not just the step's output but also a fingerprint of its inputs — a hash of the creative brief, a hash of the scene specification. When the pipeline resumes after a crash, it compares the current fingerprint against the saved fingerprint. If they match, the checkpoint is valid and can be reused. If they do not match, the checkpoint is invalidated and the step is re-executed.

This fingerprint-based invalidation is more sophisticated than it first appears. Changes cascade correctly through the pipeline. If you modify the creative brief, all downstream steps are invalidated because their input fingerprints no longer match. If you modify only the scene specification, only the steps that depend on it are invalidated. The StoryAgent's output is still valid because the brief has not changed. The StoryboardAgent's output is still valid because the story has not changed. But the DirectorAgent's output is invalid because the scene specification has changed.

The checkpoint system also handles the case where a step produces invalid output. If the BlenderAgent generates a script that fails AST validation, the checkpoint is marked as invalid and the step is retried with the validation errors as feedback. This means that even within a single step, the system can recover from failures without human intervention.
`

const chart2 = `graph LR
    P1["Pipeline Stage N"] -->|checkpoint| DB[("Event Journal")]
    DB -->|resume| P2["Pipeline Stage N+1"]
    CRASH["Crash"] -->|replay events| DB
    DB -->|reconstruct state| P2`

const section3 = `
## Budget Tracking

Production costs can spiral unexpectedly. A complex production might require dozens of LLM calls, each consuming thousands of tokens. Multiple rendering passes might run for hours. Asset downloads might consume gigabytes of storage. Without budget tracking, a single production could exhaust your resources before you realize what happened.

The BudgetTracker monitors four cost categories: LLM usage, rendering, storage, and external services. You set a budget limit for each category, and the tracker fires alerts when usage approaches or exceeds the limits. If the budget is exceeded, new production runs are blocked until the budget is reset or increased.

This budget enforcement is not just about cost control — it is about predictability. When you know that a production will cost a certain amount in LLM tokens and GPU time, you can plan accordingly. The tracker provides real-time visibility into current usage, projected total cost, and remaining budget, all displayed in the TUI's status bar.

## Event Logging and Observability

Every action in the pipeline is recorded in an append-only JSONL event log. Each event includes a sequence number, a timestamp, the event kind (step_start, step_complete, error, etc.), and a payload with event-specific data.

This event log serves two purposes. First, it provides crash recovery through event replay. If the pipeline crashes, the system can replay the event log to reconstruct the pipeline state and resume from the last checkpoint. Second, it provides observability. You can examine the event log to understand exactly what happened during a production, which steps took the longest, where errors occurred, and how the pipeline responded to those errors.

The event log also feeds the TUI's real-time streaming display. As events are recorded, they are published to the EventBus, which the TUI subscribes to. This means you see each agent's activity as it happens — not after the entire pipeline completes, but as each step starts, processes, and finishes.

## Parallel Execution and Resource Management

The pipeline uses async semaphores to control parallelism. LLM calls are limited to two concurrent requests. GPU rendering is limited to four concurrent shots. Post-production tasks have no explicit limit because they primarily use CPU resources.

These limits are not arbitrary — they reflect the physical constraints of your hardware. Each LLM call consumes GPU memory for the model weights and the KV cache. Two concurrent calls is typically the maximum that fits in 8GB of VRAM alongside the model itself. Each rendering job consumes GPU memory for the scene data and the render buffers. Four concurrent jobs is typically the maximum that fits in 24GB of VRAM.

The semaphore approach ensures that the pipeline uses all available resources without overcommitting them. If you have more GPU memory, you can increase the limits. If you have less, you can decrease them. The system adapts to your hardware without requiring code changes.
`

export default function PipelinePage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={chart1} title="Pipeline Execution Flow" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={chart2} title="Checkpoint/Resume Flow" />
      <MDXRenderer source={section3} />
    </>
  )
}
