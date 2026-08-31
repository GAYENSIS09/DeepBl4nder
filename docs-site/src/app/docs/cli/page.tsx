import { MDXRenderer } from '@/components/MDXRenderer'

export const metadata = {
  title: 'CLI Reference: The Command Line Interface - DeepBl4nder',
  description: 'Each CLI command explained in narrative style — inspect, validate, tui, download — and the philosophy behind the unified entry point.',
}

const mdxContent = `
# CLI Reference: The Command Line Interface

DeepBl4nder exposes a single command-line entry point — \`DeepBl4nder\` — that serves as the gateway to every operation the system supports. This unified interface was a deliberate design choice: rather than scattering functionality across multiple executables or requiring users to remember different command names, DeepBl4nder consolidates everything under one command with subcommands.

The CLI is built with Python's \`argparse\` module, which provides automatic help generation, type checking, and shell completion. Each subcommand has its own set of flags and arguments, but the overall structure is consistent: \`DeepBl4nder <command> [options]\`.

The CLI serves two audiences. First, it serves the operator who wants to interact with the system directly — launching the TUI, inspecting the environment, validating scripts, downloading models. Second, it serves automation and CI/CD pipelines that need to script DeepBl4nder operations without the TUI.

The unified entry point also makes the CLI extensible. Adding a new operation requires adding a new subparser and a handler function. The existing commands are unaffected, and the new command automatically inherits the same help system, type checking, and shell completion. This is the Unix philosophy applied to a modern Python tool: do one thing well, compose with other tools, and provide a consistent interface.

## \`DeepBl4nder inspect\`: Understanding Your Environment

The inspect command is the system's diagnostic tool. It shows the current state of the DeepBl4nder installation — Python version, NOOA version, Blender availability, installed plugins, loaded skills, and registered tools. When something is not working, inspect is the first command to run.

The inspect command probes the system in real time. It does not read a configuration file or cache — it checks whether Blender is actually available, whether plugins can actually reach their external systems, and whether skills are actually discoverable. This live probing means that inspect always reflects the current state of the system, not a snapshot from when it was last configured.

The command uses several internal registries to gather its information. The SkillRegistry scans the skills directory and discovers all available skills. The PluginRegistry instantiates all built-in plugins and checks their availability. The BlenderBridge probes for the Blender binary and checks its version. Each of these checks is independent and can succeed or fail without affecting the others.

Running \`DeepBl4nder inspect\` produces a summary like this:

\`\`\`text
DeepBl4nder        : 0.1.0
Python             : 3.12.5
NOOA               : 0.3.2
Blender binaire    : disponible
Blender bpy        : 4.1.0
Workers            : 4 (gpu: 1)
Skills (36)        : blender-python, modeling, assets, uv, texturing, ...
Plugins            : blender (True), ffmpeg (True), audio (True), ...
Tools              : inspect_scene, load_asset, save_blend, render, ...
\`\`\`

The output is designed for quick scanning. Each line shows one aspect of the system and its current state. The Blender line shows whether Blender is installed and accessible. The Plugins line shows which plugins are available. The Skills line lists all discovered skills. The Tools line shows the 8 canonical tools that agents can use.

For automation, the inspect command can output JSON with the \`--json\` flag, making it easy to parse and integrate into scripts. The JSON output includes all the same information as the human-readable output, but in a structured format that other tools can consume.

The inspect command also supports filtered output. The \`--plugins\` flag shows detailed plugin information, including each plugin's availability and description. The \`--agents\` flag shows the full agent crew and their configurations. The \`--skills\` flag shows all discovered skills with their descriptions and tags. These filters allow operators to focus on specific aspects of the system without wading through unrelated information.

## \`DeepBl4nder validate\`: Checking Scripts Before Execution

The validate command runs the AST validator against a Python script, applying the same security and quality checks that BlenderBridge uses before execution. This is the command to run when you want to understand whether a generated script is safe and correct, without actually executing it.

The validate command reads the script file, parses it into an AST, and walks the tree checking for forbidden operations, disallowed imports, and quality issues. It reports each issue with the line number, the specific problem, and the severity level.

The validation process mirrors exactly what happens inside BlenderBridge. The same \`ASTValidator\` class is used, the same \`CodePolicy\` is applied, and the same quality checks are run. This means that if \`DeepBl4nder validate script.py\` reports that the script is valid, BlenderBridge will also accept it. And if validate rejects the script, BlenderBridge would reject it too. There is no discrepancy between the CLI's validation and the bridge's validation, because they use the same code.

Running \`DeepBl4nder validate script.py\` produces output like this:

\`\`\`bash
$ DeepBl4nder validate script.py

Validating: script.py
Mode: strict

✓ AST parse: OK
✓ Import validation: OK (bpy, mathutils)
✓ Operator validation: OK
✓ Path validation: OK
✓ Security checks: OK

Result: VALID (5 checks passed)
\`\`\`

When issues are found, the output is specific and actionable:

\`\`\`bash
$ DeepBl4nder validate malicious.py

Validating: malicious.py
Mode: strict

✓ AST parse: OK
✗ Import validation: FAILED
  Line 3: import subprocess (blocked)
✓ Operator validation: OK
✓ Path validation: OK
✗ Security checks: FAILED
  Line 5: os.system() call (blocked)

Result: INVALID (2 issues found)
\`\`\`

The validate command defaults to strict mode, which is the same mode used in production. For development, the \`--mode permissive\` flag relaxes quality checks while maintaining security checks. The \`--json\` flag produces structured output for automation, including the full list of imports, errors, and warnings.

The validate command is essential for debugging. When a production fails because BlenderBridge rejected a script, the validate command tells you exactly why. It shows each issue with its line number and severity, allowing you to fix the specific problem rather than guessing at what went wrong.

The validate command also serves as a teaching tool. By running it against scripts you have written, you can learn which operations the CodePolicy allows and which it blocks. This helps you understand the security boundaries of the system and write scripts that work within them.

## \`DeepBl4nder tui\`: Launching the Interactive Interface

The tui command launches the Textual terminal user interface — the primary way to interact with DeepBl4nder for production work. This command performs a preflight check before launching, verifying that the required models are downloaded and the system is ready.

\`\`\`bash
# Launch with defaults
DeepBl4nder tui

# Launch with a specific budget and engine
DeepBl4nder tui --budget 2.0 --engine ue5

# Launch in debug mode for troubleshooting
DeepBl4nder tui --debug
\`\`\`

The preflight check is important. The TUI assumes that the LLM models are available locally — it does not download them on demand because downloading large models would cause unexpected delays during production. If models are missing, the preflight check warns the operator and suggests the download command.

The preflight check also verifies that the TUI dependencies are installed. The Textual framework is an optional dependency — it is not installed with the base DeepBl4nder package because not every deployment needs the TUI. If Textual is not installed, the tui command prints a helpful error message suggesting the installation command.

The TUI command is the one that most operators will use daily. It starts the LLM server internally (if not already running), builds the agent crew, and presents the Console screen. From there, the operator can type a creative brief, select an engine, and start a production with Ctrl+R.

The TUI also handles graceful shutdown. When the operator presses Ctrl+Q, the TUI cancels any running production, saves the current state, and exits cleanly. This ensures that partial work is not lost and that the system is ready for the next session.

## \`DeepBl4nder download\`: Acquiring LLM Models

The download command fetches the GGUF model files that the LLM server needs for local inference. DeepBl4nder supports three model sizes: Qwen3-1.5B for routing and classification, Qwen3-4B for general chat and translation, and Qwen3-8B for code generation and reasoning.

\`\`\`bash
# List available models
DeepBl4nder download --list

# Download all models
DeepBl4nder download --all

# Download a specific model
DeepBl4nder download --model qwen3-8b

# Download to a custom directory
DeepBl4nder download --all --dir /data/models
\`\`\`

The download command shows progress as each model is downloaded, with file sizes and completion percentages. Models are stored in the \`models/\` directory by default, but the \`--dir\` flag allows customization.

The choice to include a download command rather than downloading models automatically reflects the reality that model files are large — the Qwen3-8B model alone is over 5 GB — and automatic downloads would be disruptive in environments with limited bandwidth or metered connections. By making downloads explicit, the system gives operators control over when and where models are acquired.

The \`--list\` flag is useful for understanding what models are available before downloading them. It shows each model's name, size, and purpose, helping operators choose the right model for their use case. A user with limited VRAM might choose only the 1.5B model, while a user with a high-end GPU might download all three.

The download command also verifies the integrity of downloaded files. After each download, it checks the file's checksum against the expected value. If the checksum does not match — indicating a corrupted download — the command reports the error and suggests re-downloading.

## \`DeepBl4nder serve\`: Manual LLM Server Control

The serve command starts the LLM server manually, outside of Docker. This is useful for development, debugging, and environments where Docker is not available.

\`\`\`bash
# Start with default model
DeepBl4nder serve

# Start with a specific model and port
DeepBl4nder serve --model qwen3-4b --port 9090

# Start with custom GPU settings
DeepBl4nder serve --gpu-layers 20 --ctx-size 16384
\`\`\`

The serve command wraps llama.cpp's server, providing a familiar Python interface for configuring the server. The \`--gpu-layers\` flag controls how many model layers are loaded into GPU memory — more layers mean faster inference but more VRAM usage. The \`--ctx-size\` flag controls the context window size — larger contexts allow more tokens but require more memory.

In most production deployments, the serve command is not used directly — Docker Compose starts the LLM server as a container. The serve command exists for development scenarios where the operator wants to run the LLM server as a local process, perhaps for debugging or for testing without Docker.

The serve command outputs a startup banner that shows the model being served, the port, the context size, and the GPU configuration. It also shows a health check URL that can be used to verify the server is running:

\`\`\`text
Starting LLM server...
  Model:    qwen3-8b-q4_k_m.gguf
  Port:     8080
  Context:  32768 tokens
  GPU:      35 layers

Server ready at http://127.0.0.1:8080
API: OpenAI-compatible (/v1/chat/completions)
\`\`\`

The OpenAI-compatible API means that any tool or library designed for the OpenAI API can also call the local server. This includes the NOOA runtime, which uses the OpenAI API format for LLM inference. The compatibility is seamless — agents do not need to know whether they are calling a local server or a remote API.

## The Unified Entry Point

The design of the CLI as a single command with subcommands follows the principle of least surprise. Users familiar with tools like \`git\`, \`docker\`, or \`cargo\` will immediately understand the pattern: one command name, subcommands for different operations, and flags for configuration.

This design also makes the CLI easy to extend. Adding a new operation — say, a \`DeepBl4nder benchmark\` command — requires adding a new subparser to the \`build_parser()\` function and a new handler function. The existing commands are unaffected, and the new command automatically inherits the same help system, type checking, and shell completion.

The CLI is the foundation that the TUI builds on. The TUI uses the same underlying functions — \`_cmd_inspect()\`, \`_cmd_validate()\`, \`_cmd_download()\` — that the CLI exposes. This code reuse ensures that the TUI and CLI always behave consistently, because they share the same implementation.

The CLI also serves as the system's escape hatch. When the TUI is not available — perhaps because the terminal does not support Textual, or because the operator prefers a scripting workflow — the CLI provides the same functionality in a non-interactive form. Every operation that the TUI can perform can also be performed through the CLI, ensuring that the system is accessible regardless of the operator's preferred workflow.

<Callout type="info" title="Development Mode">
For development, use \`DeepBl4nder tui\` which starts the LLM server internally on first launch. Use \`DeepBl4nder serve\` only when you need to run the server separately for debugging or testing. The TUI handles server lifecycle automatically, which is the preferred workflow for most operators.
</Callout>
`

export default function CLIPage() {
  return <MDXRenderer source={mdxContent} />
}
