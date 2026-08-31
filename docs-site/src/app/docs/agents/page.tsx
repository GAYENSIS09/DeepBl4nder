import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Agents - DeepBl4nder',
  description: 'The 14 specialized agents and their roles in the production pipeline.',
}

const agentCommFlow = `graph LR
    User["Creative Brief"] -->|text prompt| StoryAgent
    StoryAgent -->|StorySpec| StoryboardAgent
    StoryboardAgent -->|StoryboardSpec| DirectorAgent
    User -->|text prompt| DirectorAgent
    DirectorAgent -->|SceneSpec| BlenderAgent
    BlenderAgent -->|Python Script| QAAgent
    QAAgent -->|QA Report| BlenderAgent
    QAAgent -->|QA Report| DirectorAgent
`

const coreAgentsPipeline = `graph LR
    S["StoryAgent"] -->|StorySpec| SB["StoryboardAgent"]
    SB -->|StoryboardSpec| D["DirectorAgent"]
    D -->|SceneSpec| B["BlenderAgent"]
    B -->|Script| QA["QAAgent"]
    QA -->|"Revision (if score < 70)"| B
    QA -->|"Pass (score >= 70)"| OUT["Final Output"]
`

const section1 = `
# Agents

## The Philosophy of Specialization

In traditional software architecture, a single module often handles multiple concerns — parsing input, processing data, and producing output all happen in the same function or class. This works for simple systems, but it breaks down when the system grows complex enough that no single developer can hold the entire codebase in their head.

DeepBl4nder takes a different approach. Instead of building a monolithic "AI agent" that handles every aspect of 3D production, it creates 14 specialized agents, each with deep expertise in one specific domain. The StoryAgent understands narrative structure — acts, beats, themes, character arcs. The BlenderAgent understands Blender's Python API — nodes, materials, lighting, rendering. The QAAgent understands quality metrics — composition, continuity, technical correctness.

This specialization is not just about code organization. It reflects a deeper truth about how language models work. A model that has been prompted with detailed Blender documentation and examples will produce better Blender code than a model that has been prompted with a generic "generate 3D scene" instruction. By giving each agent focused context — relevant skills, domain schemas, and examples — we get better output from each agent than we would from a single generalist agent.

## How Agents Communicate

The agents do not share memory or pass messages directly to each other. Instead, they communicate through typed domain objects — Python dataclasses with well-defined fields. The StoryAgent produces a \`StorySpec\` containing the logline, synopsis, acts, beats, and dialogue. The StoryboardAgent reads that \`StorySpec\` and produces a \`StoryboardSpec\` containing ordered shots with camera angles and timings. The DirectorAgent reads both and produces a \`SceneSpec\` containing environment, characters, and shot specifications.

This typed communication serves two purposes. First, it makes the system debuggable. When something goes wrong, you can inspect the domain object at any point in the pipeline and see exactly what information was passed between agents. There are no hidden side effects, no shared mutable state, no race conditions. Second, it makes the system testable. You can create a mock \`StorySpec\` and test the StoryboardAgent in isolation, without running the StoryAgent or the LLM server.
`

const section2 = `
## The Core Pipeline: Five Agents That Matter Most

While there are 14 agents in the system, five of them form the critical path of every production. Understanding these five gives you a complete picture of how a creative brief becomes a 3D scene.
`

const section3 = `
### The StoryAgent: From Words to Narrative Structure

The StoryAgent is the first agent to process your creative brief. Its job is to transform a free-form text prompt into a structured narrative — a \`StorySpec\` with acts, beats, characters, and dialogue. This is not just summarization or extraction. The agent actively interprets your words, identifies the emotional core of your story, and structures it according to narrative principles.

When you write "a lone astronaut walking on Mars at sunset," the StoryAgent does not just extract "astronaut" and "Mars" as keywords. It infers themes of isolation and wonder, suggests a three-act structure (departure, exploration, reflection), creates character beats that show the astronaut's emotional journey, and generates dialogue lines that reveal personality through subtext. The output is not a technical specification — it is a narrative blueprint that the subsequent agents will translate into visual form.

The StoryAgent uses the CodeActStrategy, which means it generates Python code that constructs the StorySpec object. This approach is more reliable than asking the model to produce JSON directly, because Python code can be validated, executed, and debugged in ways that raw JSON cannot. If the model generates invalid Python, the NOOA framework catches the error and retries with corrected code.

### The StoryboardAgent: From Narrative to Visual Language

The StoryboardAgent reads the StorySpec and translates it into visual terms. Where the StoryAgent deals with acts and beats, the StoryboardAgent deals with shots and camera movements. This translation from narrative to visual language is one of the most creative steps in the pipeline.

The agent plans each shot with specific camera angles (wide, medium, close-up, overhead), camera movements (pan, tilt, dolly, crane), and transitions (cut, dissolve, fade). It estimates the duration of each shot based on the emotional weight of the corresponding beat. A dramatic reveal might get a slow, lingering shot. A tense action sequence might get rapid cuts between multiple angles.

This shot-by-shot planning is what separates DeepBl4nder from simpler AI video generators. Instead of producing a single continuous clip, it plans a sequence of shots that could be assembled by a professional editor. The storyboard is the bridge between the abstract narrative and the concrete 3D scene.

### The DirectorAgent: The Central Orchestrator

The DirectorAgent is the most complex agent in the system. It reads the creative brief, the story, and the storyboard, and synthesizes them into a complete \`SceneSpec\` — a detailed technical specification that describes every aspect of the 3D scene.

The SceneSpec includes the environment (terrain, sky, lighting mood), characters (position, description, asset references), and individual shot specifications (camera focal length, lighting setup, animation descriptions, render settings). The DirectorAgent makes hundreds of creative decisions in a single pass: where to place the camera, what lens to use, how to light the scene, what mood to create through color temperature.

This is where the Domain Schema system shines. The DirectorAgent uses the SchemaVectorStore to search for relevant domain types — CameraSpec, LightingSpec, CharacterSpec — and injects their definitions into its context. This means the agent knows exactly what fields are available and what values they accept, reducing the chance of generating invalid specifications.

### The BlenderAgent: From Specification to Code

The BlenderAgent takes the SceneSpec and generates deterministic Blender Python scripts. This is the most technically demanding step in the pipeline, because it requires deep knowledge of Blender's bpy API, asset management, and rendering configuration.

The agent loads a battery of skills — modeling, shading, lighting, rendering, animation — and uses the SchemaVectorStore to find the most relevant domain types for the current scene. It then generates Python code that constructs the entire scene programmatically: creating meshes, assigning materials, setting up lights, configuring the camera, and initiating the render.

What makes the BlenderAgent particularly interesting is its use of the ReflexionStrategy for script refinement. When the QA agent identifies issues in the generated script, the BlenderAgent does not start from scratch. It reads the QA feedback, identifies the specific lines of code that need to change, and modifies them while preserving the rest of the script. This iterative refinement loop — generate, evaluate, refine — is modeled on how human programmers actually work.

The agent also handles asset management automatically. If the SceneSpec calls for an HDRI environment map, the agent downloads it from PolyHaven. If it calls for a character model, the agent downloads it from Quaternius. These downloads are cached locally, so subsequent productions with the same assets do not require network access.

### The QAAgent: The Quality Gatekeeper

The QAAgent evaluates every artifact produced by the pipeline against the original SceneSpec. It does not just check for technical errors — it assesses the output across four dimensions: technical correctness, visual quality, continuity, and semantic fidelity.

Technical checks verify that the script is syntactically valid, imports the correct modules, and uses proper Blender API patterns. Visual checks assess composition, lighting quality, and material appearance. Continuity checks ensure that shots within a sequence are visually consistent — that the lighting does not change dramatically between cuts, that characters maintain their positions, that the camera movement is smooth. Semantic checks ask the fundamental question: does this output actually represent what the user asked for?

The QAAgent produces a \`QAReport\` with a score from 0 to 100. Scores above 70 are considered passing. Scores below 70 trigger a revision loop, where the QAAgent generates a \`RevisionSpec\` targeting the specific agent responsible for the deficiency. If the issue is with the scene composition, the revision targets the DirectorAgent. If the issue is with the generated code, it targets the BlenderAgent. This targeted feedback means that revisions are surgical — they fix the specific problem without redoing work that was already correct.

## The Remaining Nine Agents

The other nine agents handle specialized aspects of the production pipeline. The CharacterDesignerAgent creates detailed character specifications. The EnvironmentArtistAgent designs worlds and landscapes. The AnimatorAgent plans movement and keyframes. The AudioAgent, MusicComposerAgent, and SoundDesignerAgent handle the audio pipeline. The CompositingAgent manages post-processing. The LocalizationAgent handles subtitles and multi-language support. The ReviewAgent performs final quality checks on the complete output.

These agents are invoked during the post-production phase, after the core pipeline has produced the 3D scene and animations. They run in parallel where possible — music composition, sound design, and audio mixing can all happen simultaneously because they operate on independent audio tracks.

## Strategies: How Agents Think

Each agent uses one of four NOOA strategies, chosen based on the nature of the task.

The **CodeActStrategy** is the most common. The agent generates Python code that constructs domain objects, then executes that code to produce the output. This approach is more reliable than asking the model to produce structured data directly, because Python code can be validated and debugged.

The **ReflexionStrategy** wraps CodeAct with a self-reflection loop. After generating code, the agent evaluates its own output, identifies weaknesses, and generates a refined version. This loop runs up to two iterations, which is typically enough to catch most issues without wasting tokens on diminishing returns.

The **PredictStrategy** is used for simple classification tasks where the agent needs to make a single judgment call without generating code. The QAAgent's \`quick_scan\` method uses this strategy for fast syntax and structure checks.

The **TemplateStrategy** is used for deterministic outputs where the model's creativity is not needed. The BlenderAgent's \`build_probe_script\` method uses this strategy to generate a standard test script that verifies the rendering pipeline is working correctly.

## The Shared LLM Client

All 14 agents share a single LLMClient instance. This is not just a convenience — it is a architectural decision with important implications. The shared client means that model selection, caching, and budget tracking happen at a single point of control. When the TaskClassifier routes a request to the 8B model, the decision is made once and logged once. When a model fails and the CascadeRouter escalates to the next heavier model, the escalation history is shared across all agents.

The shared client also means that the KV cache is shared. If the StoryAgent's system prompt is in the cache, the StoryboardAgent can reuse those cached key-value pairs because they share the same client. This cache sharing reduces the total number of tokens that need to be processed, which directly translates to faster response times and lower VRAM usage.
`

export default function AgentsPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={agentCommFlow} title="Agent Communication Flow" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={coreAgentsPipeline} title="5 Core Agents Pipeline" />
      <MDXRenderer source={section3} />
    </>
  )
}
