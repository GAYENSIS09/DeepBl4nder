import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Bridges & Engine Integration - DeepBl4nder',
  description: 'How DeepBl4nder connects to Blender, Unreal Engine 5, Godot, and AI video servers through validated bridge abstractions.',
}

const mermaidChart1 = `graph TB
    subgraph Agents["Agent Layer"]
      BA["BlenderAgent"]
      UEA["UE5Agent"]
      GA["GodotAgent"]
      AIVA["AIVideoAgent"]
    end

    subgraph Bridges["Bridge Layer"]
      BB["BlenderBridge"]
      UB["UE5Bridge"]
      GB["GodotBridge"]
      AB["AIVideoBridge"]
    end

    subgraph Engines["External Engines"]
      BLENDER["Blender 4.1+"]
      UE5["Unreal Engine 5"]
      GODOT["Godot 4"]
      AIVID["AI Video Server"]
    end

    BA --> BB
    UEA --> UB
    GA --> GB
    AIVA --> AB
    BB --> BLENDER
    UB --> UE5
    GB --> GODOT
    AB --> AIVID
  `

const mermaidChart2 = `graph TB
    subgraph Docker["Docker Compose"]
      subgraph Core["Core Services"]
        LLM["llm-server :8080"]
        BW["blender-worker"]
      end

      subgraph Optional["Optional Profiles"]
        UE5["ue5-server :8081"]
        GODOT["godot-server :8082"]
        AIV["ai-video-server :8083"]
      end
    end

    LLM --> BW
    BW --> UE5
    BW --> GODOT
    BW --> AIV
  `

const section1 = `
# Bridges & Engine Integration: The Abstraction Layer

At the heart of any multi-engine 3D production system lies a deceptively difficult problem: how do you let agents talk to completely different 3D engines — each with its own language, its own API, its own way of doing things — without coupling the agents to the quirks of any single engine? DeepBl4nder solves this through the **bridge pattern**, an abstraction layer that provides a uniform interface to diverse external engines while handling the messy reality of validation, security, and process isolation behind the scenes.

A bridge is not merely a wrapper. It is a boundary that enforces security policies, validates generated code, manages process lifecycles, and isolates the agent runtime from the external engine. When a BlenderAgent generates a Python script, that script does not execute directly in the agent's process. It passes through BlenderBridge, which validates it via AST analysis, writes it to a temporary file, and launches Blender in headless mode to execute it. This separation is not ceremony — it is the architectural spine that keeps the system safe and maintainable.

## Why Bridges Exist as an Abstraction Layer

The decision to introduce a bridge layer was driven by three observations about the problem domain. First, 3D engines are heterogeneous. Blender uses Python scripts and runs headless via the command line. Unreal Engine 5 uses a REST API exposed by a dedicated server process. Godot 4 has its own REST API. AI video models run as separate services with their own protocols. There is no common interface that all these engines share.

Second, each engine requires different security considerations. BlenderBridge executes Python code in a subprocess — it needs AST validation to prevent malicious or dangerous operations. UE5Bridge communicates via HTTP — it needs authentication and input sanitization. Each bridge must enforce the security model appropriate to its engine.

Third, engines have different lifecycle requirements. Blender must be launched fresh for each script execution or kept running as a persistent service. UE5 and Godot run as persistent servers that accept commands. AI video servers may have long-running GPU jobs. The bridge layer manages these lifecycle differences so that agents do not need to know whether an engine is a subprocess, a REST server, or a cloud service.
`

const section2 = `
The result is that an agent can write \`bridge.execute_python(script)\` without knowing whether Blender is running locally or in Docker, whether it uses CUDA or CPU rendering, or what operating system the host uses. The bridge absorbs all of that complexity.

## BlenderBridge: The Primary Engine

BlenderBridge is the most complex bridge in the system, and for good reason: Blender is the primary 3D engine, and it operates in a fundamentally different way from the other engines. Rather than receiving commands over a network, Blender executes Python scripts. This means BlenderBridge must handle script validation, file management, subprocess orchestration, and output verification.

### The Validation-First Architecture

Every script that passes through BlenderBridge is validated before execution. This is not a suggestion or a best practice — it is a hard requirement enforced at the bridge level. The bridge calls \`validate_for_worker()\` on the script, which runs the AST validator against the CodePolicy. If validation fails, the script is never executed. Period.

This design is rooted in the **fail-closed** principle: when in doubt, do not execute. The system assumes that generated code is potentially dangerous until proven otherwise. This is the opposite of the fail-open approach, which would allow code to run unless it is known to be dangerous. The fail-closed approach is more conservative, but it is the only approach that provides meaningful security guarantees when the code is generated by an LLM.

\`\`\`python
from DeepBl4nder.bridges.blender.bridge import BlenderBridge
from DeepBl4nder.domain.scene import BlenderScript

bridge = BlenderBridge(blender_exe="/usr/local/bin/blender")

# Create a script to execute
script = BlenderScript(
    code="import bpy\\nbpy.ops.mesh.primitive_cube_add()",
    scene_name="test",
    version=1,
)

# BlenderBridge validates before execution
# If validation fails, CodePolicyViolation is raised
result = bridge.run_script(script, workdir=Path("/tmp/output"))
\`\`\`

The validation pipeline has multiple layers. The AST parser checks that the code is syntactically valid Python. The CodePolicy checks that only allowed modules are imported. The forbidden builtins check blocks \`exec()\`, \`eval()\`, \`compile()\`, and other dangerous functions. The forbidden attributes check blocks \`os.system()\`, \`subprocess.Popen()\`, and similar system-level calls. And the semantic quality checks warn about common issues like missing render output paths, unset render engines, and missing camera setups.

### GPU Detection and Backend Selection

BlenderBridge automatically detects the available GPU backend — CUDA, OptiX, HIP, or Metal — and configures Blender to use it. This detection happens at initialization time, not at execution time, so there is no overhead during rendering.

The detection logic probes the system using platform-specific tools: \`nvidia-smi\` for NVIDIA GPUs, \`rocm-smi\` for AMD GPUs on Linux, and \`system_profiler\` for Apple Silicon on macOS. When an NVIDIA GPU is detected, the bridge prefers OptiX over CUDA because OptiX provides better ray tracing performance on RTX hardware.

The detected backend is communicated to Blender through environment variables rather than script modifications. This keeps the generated scripts clean and engine-agnostic — the same script runs on any platform, and the bridge handles the GPU configuration transparently.

### Headless Execution

BlenderBridge runs Blender in headless mode (\`blender -b -P <script>\`), which means Blender executes the script without opening a window. This is essential for server-side operation, Docker containers, and CI/CD pipelines. The bridge manages the subprocess lifecycle: it launches Blender with a configurable timeout (defaulting to 600 seconds for production renders), captures stdout and stderr, and returns a structured \`ProcessResult\`.

The timeout is deliberately generous. Production renders with 256+ samples, complex lighting, and high-resolution output can take several minutes. A 600-second timeout allows for thorough rendering without false timeouts. For development and testing, the timeout can be reduced via the bridge constructor.

## UE5Bridge: REST API Communication

Unreal Engine 5 operates differently from Blender. Rather than executing scripts, UE5 exposes a REST API through a dedicated server process. The UE5Bridge communicates with this server over HTTP, sending structured commands for level creation, asset import, material setup, lighting configuration, and rendering.

This REST-based architecture was chosen for several reasons. First, UE5 is a complex, multi-process system that cannot be easily launched and stopped for each script execution. A persistent server process is more efficient. Second, UE5's native scripting language (Blueprints and C++) is not Python, so the bridge cannot simply execute generated scripts the way BlenderBridge does. Instead, the bridge translates high-level commands into UE5 API calls.

The UE5Bridge supports five core commands: \`create_level\` for scene setup, \`import_asset\` for bringing in 3D models and textures, \`create_material\` for PBR material configuration, \`setup_lighting\` for illumination, and \`start_render\` for Movie Render Queue rendering.

\`\`\`python
from DeepBl4nder.bridges.ue5.bridge import UE5Bridge

bridge = UE5Bridge(host="localhost", port=8081)

# Create a forest scene
await bridge.create_level("ForestScene")

# Import a character asset
await bridge.import_asset("/assets/character.fbx")

# Configure volumetric lighting
await bridge.setup_lighting({
    "type": "directional",
    "intensity": 10.0,
    "color": [1.0, 0.95, 0.8],
    "volumetric": True,
})
\`\`\`

The UE5 server runs in its own Docker container, isolated from the rest of the system. It requires its own GPU allocation for real-time rendering and ray tracing. The bridge communicates with it via the Docker network, and the server exposes its API on port 8081.

## GodotBridge: Open-Source Engine Integration

GodotBridge follows a similar REST-based pattern to UE5Bridge, but targets the open-source Godot 4 engine. Godot is lightweight, cross-platform, and supports WebGL export — making it ideal for web-based interactive experiences.

The GodotBridge supports scene management, procedural mesh generation, PBR material setup, dynamic and baked lighting, and WebGL export. The WebGL export capability is particularly valuable: it allows DeepBl4nder to produce interactive 3D experiences that run directly in a web browser, without requiring users to install any software.

\`\`\`python
from DeepBl4nder.bridges.godot.bridge import GodotBridge

bridge = GodotBridge(host="localhost", port=8082)

# Create a procedural forest scene
await bridge.create_scene("ForestScene")
await bridge.create_mesh({
    "type": "plane",
    "size": [100, 100],
    "material": "grass",
})

# Export to WebGL for browser playback
await bridge.export_webgl("/output/web/")
\`\`\`

The Godot server runs on port 8082 and requires its own Docker container. Like the UE5 server, it depends on the LLM server being healthy before it starts, ensuring that the full pipeline is available when production begins.

## AIVideoBridge: AI-Powered Video Generation

AIVideoBridge connects to the AI video generation server, which provides text-to-video and image-to-video capabilities. This bridge supports three model families: CogVideoX for high-quality text-to-video generation, SVD (Stable Video Diffusion) for animating still images, and AnimateDiff for anime-style video generation.

The AI video server is the most GPU-intensive service in the DeepBl4nder stack. Text-to-video generation requires significant VRAM and compute time — a single 4-second clip at 24fps can take several minutes on consumer hardware. The bridge handles this by communicating asynchronously with the server, submitting generation requests and polling for completion.

\`\`\`python
from DeepBl4nder.bridges.ai_video.bridge import AIVideoBridge

bridge = AIVideoBridge(host="localhost", port=8083)

# Generate a 4-second video from text
result = await bridge.generate_t2v(
    prompt="A serene forest clearing at dawn, volumetric light rays",
    duration=4.0,
    fps=24,
)

# Animate a still image
result = await bridge.generate_i2v(
    image_path="/output/renders/scene_frame_001.png",
    duration=2.0,
)
\`\`\`

## Docker Isolation and Security

Every bridge that communicates with an external engine does so through Docker containers. This isolation is not merely a convenience — it is a security requirement. When BlenderBridge executes a Python script, that script runs inside a Docker container with limited filesystem access, no network access, and controlled resource allocation. Even if the AST validator misses a dangerous operation (which should never happen, but defense in depth demands we prepare for it), the Docker container limits the blast radius.

The Docker configuration uses Docker Compose profiles to manage which engines are available. By default, only the core services — the LLM server and the Blender worker — are started. Optional engines like UE5, Godot, and AI Video are started on demand using Docker Compose profiles.
`

const section3 = `
Each container has its own health checks, restart policies, and resource reservations. The LLM server and Blender worker both reserve GPU resources through the NVIDIA Container Toolkit. The optional servers only reserve GPUs when they are actually started, preventing resource waste.

<Callout type="tip" title="Engine Selection">
The DirectorAgent automatically selects the appropriate engine based on the production brief. If the brief calls for photorealistic rendering, it chooses Blender with Cycles. If it calls for real-time interactive content, it chooses Godot with WebGL export. If it calls for cinematic quality, it may choose UE5 with Lumen and Nanite. You can also force a specific engine in the TUI settings or via the CLI \`--engine\` flag.
</Callout>
`

export default function BridgesPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="Engine Bridge Architecture" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={mermaidChart2} title="Docker Service Architecture" />
      <MDXRenderer source={section3} />
    </>
  )
}
