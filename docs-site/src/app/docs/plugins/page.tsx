import { MDXRenderer } from '@/components/MDXRenderer'

export const metadata = {
  title: 'Plugins: External System Bridges - DeepBl4nder',
  description: 'The plugin architecture philosophy, how the PluginRegistry manages 10 built-in plugins, and why each plugin exists as a boundary between agents and the outside world.',
}

const mdxContent = `
# Plugins: External System Bridges

In the architecture of DeepBl4nder, a plugin occupies a specific and carefully bounded role: it is a bridge between the agent runtime and the outside world. A plugin is not an agent — it does not reason, it does not make decisions, it does not generate code. It is a passive interface that provides access to external systems: Blender for rendering, FFmpeg for transcoding, audio synthesis for sound generation, storage for artifact persistence, and knowledge graphs for production memory.

This distinction is not pedantic. The decision to keep plugins as thin bridges rather than giving them agent-like capabilities was driven by a fundamental architectural principle: **separation of concerns**. Agents are responsible for reasoning about what to do. Plugins are responsible for connecting to the systems that do it. When a plugin starts making decisions — choosing which codec to use, deciding how to arrange a scene, selecting which assets to load — it becomes a second runtime, and the system's behavior becomes unpredictable because two runtimes are making independent decisions about the same task.

By keeping plugins as passive bridges, DeepBl4nder ensures that all reasoning happens in one place: the agents. The plugins are tools in the truest sense — they do exactly what they are told, and nothing more.

## The Plugin Architecture

Every plugin in DeepBl4nder inherits from a single abstract base class: \`Plugin\`. This base class defines the minimum interface that all plugins must implement: a name, a description, and an \`available()\` method that checks whether the external system is reachable.

\`\`\`python
from abc import ABC, abstractmethod

class Plugin(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def available(self) -> bool:
        """Check if the external system is reachable."""
        ...

    def info(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "available": self.available(),
        }
\`\`\`

The \`available()\` method is the plugin's health check. Before an agent uses a plugin, it calls \`available()\` to verify that the external system is responding. This prevents the agent from attempting operations that will fail — a BlenderPlugin that cannot reach Blender, a FFmpegPlugin that cannot find the FFmpeg binary, a TTSPlugin that has no audio model available.

The plugin base class is deliberately minimal. It does not define methods for specific operations like \`render()\` or \`transcode()\` because those methods are specific to each plugin's domain. The base class provides the contract that the registry can rely on, while each concrete plugin implements the operations that its external system supports.

This minimalism is intentional. By defining only three attributes — name, description, and available — the base class ensures that all plugins share a common interface without constraining their implementation. A plugin can use subprocess calls, REST APIs, in-process libraries, or any other mechanism to interact with its external system. The only requirement is that it can report whether it is available.

## The PluginRegistry: Managing 10 Built-in Plugins

The PluginRegistry is the central authority for plugin lifecycle management. It instantiates all 10 built-in plugins at startup, provides methods for accessing them, and tracks their usage for observability.

The registry is a dataclass that holds a dictionary of plugin instances. On initialization, it iterates over the \`_BUILTINS\` dictionary — a module-level mapping of plugin names to plugin classes — and instantiates each one. This eager initialization means that all plugins are ready to use immediately, without any lazy loading or on-demand instantiation.

\`\`\`python
from DeepBl4nder.plugins.registry import PluginRegistry

registry = PluginRegistry()

# All 10 plugins are instantiated and ready
for plugin in registry.all_plugins():
    status = "available" if plugin.available() else "unavailable"
    print("  " + plugin.name + ": " + status)

# Access a specific plugin
blender = registry.get("blender")
if blender.available():
    result = blender.render_scene("scene_001")
\`\`\`

The registry also provides a \`record()\` method that tracks plugin usage. Every time a plugin is used — whether for scene inspection, rendering, or transcoding — the registry records the event. This observability data is published to the EventBroker, where it appears in the TUI's agent stream as "plugin: blender.inspect_scene" or "plugin: ffmpeg.transcode". This gives operators visibility into which plugins are being used and how often.

One plugin — RenderFarmPlugin — receives special treatment during initialization. It receives a reference to the registry itself, because the render farm needs to coordinate with other plugins (particularly BlenderPlugin) to distribute rendering work across multiple workers. This cross-plugin coordination is the only case where one plugin depends on another, and it is handled explicitly rather than through a general dependency injection mechanism.

The registry also provides a \`discover()\` method that returns information about all registered plugins. This method is used by the CLI's \`inspect\` command to display plugin status, and by the TUI to show available services. The \`available()\` method returns a list of plugin names that are currently reachable — useful for checking whether the system is ready for production.

## The 10 Built-in Plugins

Each of the 10 built-in plugins exists because it bridges a specific external system that agents need to interact with. The plugins are organized into four categories: rendering, media, storage, and knowledge.

### Rendering Plugins

**BlenderPlugin** is the most critical plugin in the system. It provides headless Blender execution, scene inspection, asset loading, and rendering. Every production run that involves 3D content goes through BlenderPlugin. The plugin manages the Blender process lifecycle, handles GPU detection, and communicates with the BlenderBridge for script execution.

The BlenderPlugin wraps the BlenderBridge, which provides the validation-first execution model. When an agent calls \`blender.execute_python(script)\`, the plugin does not immediately run the script. It passes the script through the AST validator, checks it against the CodePolicy, and only then writes it to a temporary file and launches Blender in headless mode. This validation-first approach means that dangerous code never reaches the Blender process.

The plugin also provides scene inspection capabilities. Before generating a script, an agent can call \`blender.inspect_scene()\` to see what objects exist in the current scene. This information helps the agent make informed decisions about what to create, modify, or render.

**FFmpegPlugin** handles video transcoding, audio mixing, and format conversion. After Blender renders a sequence of frames, FFmpegPlugin assembles them into a video file, mixes in audio tracks, and transcodes to the target codec. The plugin wraps the FFmpeg binary, providing a Python interface for the complex command-line operations that FFmpeg requires.

FFmpeg is notoriously complex — its command-line interface has hundreds of options, and getting the right combination for a specific use case requires deep expertise. FFmpegPlugin encapsulates this complexity behind simple methods: \`mux()\` for combining video and audio, \`transcode()\` for format conversion, and \`extract_audio()\` for audio extraction. The agent does not need to know FFmpeg's syntax; it just calls the method with the right parameters.

**RenderFarmPlugin** distributes rendering across a pool of worker nodes. When a production requires rendering many frames or multiple camera angles, the render farm parallelizes the work across available workers. The plugin manages worker discovery, job distribution, and result aggregation.

The render farm is the only plugin that depends on other plugins. It uses BlenderPlugin to execute rendering jobs on each worker, and it coordinates with StoragePlugin to store the results. This cross-plugin coordination is handled through the registry — RenderFarmPlugin receives a reference to the PluginRegistry at initialization, allowing it to access other plugins as needed.

### Media Plugins

**AudioPlugin** provides deterministic audio synthesis. Unlike TTSPlugin, which generates speech from text, AudioPlugin generates ambient sounds, tones, and silence — the building blocks of a soundscape. The plugin uses Python's standard library for synthesis, ensuring deterministic output without requiring external models.

Determinism is important here. When an agent generates a script that creates a 30-second ambient track, the output must be identical every time the script runs. External AI models are non-deterministic — they produce different outputs for the same input. AudioPlugin uses algorithmic synthesis, which guarantees that the same parameters always produce the same audio.

**TTSPlugin** generates speech from text. It supports multiple backends — Bark, CosyVoice, and fallback synthesis — and automatically selects the best available backend. The plugin handles text preprocessing, audio generation, and output formatting.

The multi-backend design reflects a practical reality: not every deployment has GPU resources for neural TTS models. TTSPlugin's fallback synthesis — which uses basic waveform generation — provides acceptable (if not high-quality) speech output when GPU-dependent backends are unavailable. This ensures that productions can proceed even on CPU-only systems.

**SubtitlePlugin** generates SRT subtitle files from dialogue and timing information. It parses dialogue content, computes timing based on speech rates, and produces standard SRT files that can be embedded in video output.

The SRT format is deliberately chosen over more complex subtitle formats (like WebVTT or TTML) because it is universally supported by video players and editors. A subtitle file that works in VLC, YouTube, and Blender's video editor is more valuable than a technically superior format that only works in specialized tools.

### Storage Plugins

**StoragePlugin** provides artifact persistence with path traversal protection. Every file written by the system — renders, audio, scripts, reports — goes through StoragePlugin, which ensures that files are stored in the correct location and that no operation can write outside the designated directory.

Path traversal protection is the critical security feature here. Without it, a generated script could write files to arbitrary locations on the host filesystem — \`../../etc/passwd\` or \`~/.ssh/authorized_keys\`. StoragePlugin validates every path before writing, rejecting any path that resolves outside the designated directory.

**GitPlugin** provides version control for production artifacts. Major milestones in a production — completed scenes, approved renders, final outputs — are committed to a local Git repository, creating an auditable history of the production's evolution.

GitPlugin does not attempt to be a full Git client. It provides three operations: \`commit()\` for saving snapshots, \`log()\` for viewing history, and \`diff()\` for comparing versions. These operations cover the use cases that production workflows require without the complexity of branch management, merging, or rebasing.

### Knowledge Plugins

**AssetLibraryPlugin** maintains a local catalog of 3D assets with SHA-256 provenance tracking. When an agent needs a character model, a texture, or a sound effect, it queries the asset library to find matching assets. The provenance tracking ensures that every asset can be traced back to its source — its original creator, its license, and its creation date.

The SHA-256 hashing serves two purposes. First, it ensures content integrity — if an asset's hash does not match the catalog, the asset has been modified or corrupted. Second, it enables deduplication — assets with identical content are stored once, regardless of how many copies exist.

**KnowledgeGraphPlugin** maintains a production knowledge graph in JSON format. This graph tracks relationships between scenes, characters, assets, and decisions — providing a structured memory that agents can query to understand the production's context.

The knowledge graph is not a database — it is a lightweight JSON file that represents the production's structure. It answers questions like "Which scenes feature this character?", "What assets were used in this scene?", and "What decisions were made about this lighting setup?". This structured context helps agents maintain consistency across a multi-step production.

## Why Each Plugin Exists

The decision to include each plugin was driven by the question: "What external system does the agent need to interact with, and what is the simplest way to provide that interaction?"

BlenderPlugin exists because agents generate Blender scripts that need to execute. FFmpegPlugin exists because rendered frames need to become videos. AudioPlugin exists because productions need sound. TTSPlugin exists because characters need voices. StoragePlugin exists because artifacts need to persist. GitPlugin exists because productions need history. AssetLibraryPlugin exists because agents need to find and reuse assets. SubtitlePlugin exists because accessibility requires captions. KnowledgeGraphPlugin exists because productions need structured memory. RenderFarmPlugin exists because rendering needs parallelism.

None of these plugins would exist if the system were purely algorithmic — if agents simply computed results without interacting with external tools. But 3D production is inherently physical: it involves rendering images, generating audio, writing files, and managing state. Plugins are the system's connection to that physical reality.

## The Tool Registry

Plugins expose their capabilities through the ToolRegistry, which defines 8 canonical tools that agents use. These tools are the high-level operations that agents call, and they are backed by specific plugin methods.

The 8 tools are: \`inspect_scene\` (list scene objects in Blender), \`load_asset\` (append an asset to a Blender scene), \`save_blend\` (save a .blend file), \`render\` (render a scene), \`inspect_render\` (verify a rendered image), \`create_audio\` (generate an audio track), \`compose\` (mux video and audio), and \`export\` (transcode to a target codec).

\`\`\`python
from DeepBl4nder.plugins.tools import ToolRegistry

tools = ToolRegistry()

# List all available tools
for tool in tools.tools():
    print("  " + tool.name + ": " + tool.description)

# Execute a tool
render_tool = tools.get("render")
result = render_tool.execute(scene_name="forest_scene")
\`\`\`

The tool registry deliberately avoids **micro-tools** — fine-grained operations like \`move_object\`, \`rotate_object\`, or \`set_material\`. These operations are instead handled through Code-as-Action: the agent generates Python code that performs the operation directly. This design keeps the tool surface small and focused on operations that require interaction with external systems, while delegating pure Blender operations to the code generation pipeline.

The rationale is straightforward. A tool like \`move_object\` would require the plugin to interpret a high-level command, translate it into Blender API calls, and execute them. But the agent can already generate that Python code directly — and the code is more flexible, more expressive, and easier to validate. Adding a \`move_object\` tool would duplicate functionality that already exists in the code generation pipeline, while adding complexity to the plugin interface.

## Design Principles

The plugin system follows several design principles that ensure consistency and reliability across all 10 built-in plugins.

**Plugin is not Agent.** A plugin never makes decisions. It receives a command, executes it, and returns a result. If a plugin cannot fulfill a request — because the external system is unavailable or the request is invalid — it raises a \`PluginError\` rather than attempting to recover on its own. This clear boundary prevents the kind of unpredictable behavior that arises when multiple runtimes make independent decisions.

**Fail-closed.** Critical operations that go through plugins — particularly BlenderPlugin — are validated via AST analysis before execution. The plugin is the enforcement point for the fail-closed policy. If the validator blocks a script, the plugin does not execute it — regardless of what the agent requested.

**Deterministic fallbacks.** Media plugins (AudioPlugin, TTSPlugin) have fallback implementations using Python's standard library. If the primary audio model is unavailable, AudioPlugin falls back to synthesized tones. If the neural TTS model is unavailable, TTSPlugin falls back to basic waveform synthesis. This ensures that productions can proceed even when GPU-dependent services are offline.

**No micro-tools.** The tool registry exposes only 8 canonical tools. Fine-grained operations are handled through code generation, not through plugin methods. This keeps the plugin API surface minimal and focused.

**Availability check.** Every plugin operation should be preceded by an \`available()\` check. This is not enforced by the framework — agents are trusted to check availability — but it is a strong convention that prevents runtime errors. An agent that calls \`blender.render()\` without checking \`blender.available()\` first is making an assumption that may not hold.

<Callout type="info" title="Plugin vs Agent vs Tool">
The distinction between plugins, agents, and tools is fundamental to understanding DeepBl4nder's architecture:

- A **plugin** is a bridge to an external system (Blender, FFmpeg, storage). It connects.
- An **agent** is a runtime object that reasons, decides, and generates code. It thinks.
- A **tool** is a high-level action primitive that agents call (inspect_scene, render). It acts.

Plugins connect. Agents reason. Tools act. The three work together but serve fundamentally different purposes.
</Callout>
`

export default function PluginsPage() {
  return <MDXRenderer source={mdxContent} />
}
