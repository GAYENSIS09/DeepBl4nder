import { MDXRenderer } from '@/components/MDXRenderer'

export const metadata = {
  title: 'CLI Reference: The Command Line Interface - DeepBl4nder',
  description: 'Each CLI command explained in narrative style — inspect, validate, tui — and the philosophy behind the unified entry point.',
}

const mdxContent = `
# CLI Reference: The Command Line Interface

DeepBl4nder exposes a single command-line entry point — \`DeepBl4nder\` — that serves as the gateway to every operation the system supports. This unified interface was a deliberate design choice: rather than scattering functionality across multiple executables or requiring users to remember different command names, DeepBl4nder consolidates everything under one command with subcommands.

The CLI is built with Python's \`argparse\` module, which provides automatic help generation, type checking, and shell completion. Each subcommand has its own set of flags and arguments, but the overall structure is consistent: \`DeepBl4nder <command> [options]\`.

The CLI serves two audiences. First, it serves the operator who wants to interact with the system directly — launching the TUI, inspecting the environment, and validating scripts. Second, it serves automation and CI/CD pipelines that need to script DeepBl4nder operations without the TUI.

The unified entry point also makes the CLI extensible. Adding a new operation requires adding a new subparser and a handler function. The existing commands are unaffected, and the new command automatically inherits the same help system, type checking, and shell completion. This is the Unix philosophy applied to a modern Python tool: do one thing well, compose with other tools, and provide a consistent interface.

## \`DeepBl4nder inspect\`: Understanding Your Environment

The inspect command is the system's diagnostic tool. It shows the current state of the DeepBl4nder installation — Python version, NOOA version, Blender availability, installed plugins, loaded skills, and registered tools. It also reports the LLM router configuration, including which cloud providers are configured via their API keys. When something is not working, inspect is the first command to run.

The inspect command probes the system in real time. It does not read a configuration file or cache — it checks whether Blender is actually available, whether plugins can actually reach their external systems, whether skills are actually discoverable, and whether at least one LLM provider API key is configured. This live probing means that inspect always reflects the current state of the system, not a snapshot from when it was last configured.

The command uses several internal registries to gather its information. The SkillRegistry scans the skills directory and discovers all available skills. The PluginRegistry instantiates all built-in plugins and checks their availability. The BlenderBridge probes for the Blender binary and checks its version. The LLM router reports which cloud providers are ready. Each of these checks is independent and can succeed or fail without affecting the others.

Running \`DeepBl4nder inspect\` produces a summary like this:

\`\`\`text
DeepBl4nder        : 0.2.0
Python             : 3.12.5
NOOA               : 0.3.2
Blender binaire    : disponible
Blender bpy        : 4.1.0
Workers            : 4 (gpu: 1)
Skills (32)        : blender-python, modeling, assets, uv, texturing, ...
Plugins            : blender (True), ffmpeg (True), audio (True), ...
Tools              : inspect_scene, load_asset, save_blend, render, ...
LLM Provider       : gemini (configured), groq (configured), nvidia (missing)
Router mode        : fallback
\`\`\`

The output is designed for quick scanning. Each line shows one aspect of the system and its current state. The Blender line shows whether Blender is installed and accessible. The Plugins line shows which plugins are available. The Skills line lists all discovered skills. The Tools line shows the 8 canonical tools that agents can use. The LLM Provider lines show which cloud router providers are configured.

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

The tui command launches the Textual terminal user interface — the primary way to interact with DeepBl4nder for production work. This command performs a preflight check before launching, verifying that at least one cloud LLM provider API key is configured and the system is ready.

\`\`\`bash
# Launch with defaults
DeepBl4nder tui

# Launch with a specific budget and engine
DeepBl4nder tui --budget 2.0 --engine blender

# Launch in debug mode for troubleshooting
DeepBl4nder tui --debug
\`\`\`

The preflight check is important. The TUI's agents rely on the cloud LLM router, which requires at least one provider API key (Gemini, Groq, NVIDIA, OpenRouter, or Cloudflare) to be configured. The \`_tui_preflight()\` function checks the configured providers for missing keys and warns if none are available, since agents cannot reason without an LLM backend. There is nothing to download — the LLM is served from the cloud, not hosted locally.

The preflight check also verifies that the TUI dependencies are installed. The Textual framework is an optional dependency — it is not installed with the base DeepBl4nder package because not every deployment needs the TUI. If Textual is not installed, the tui command prints a helpful error message suggesting the installation command.

The TUI command is the one that most operators will use daily. It validates the LLM configuration, builds the agent crew, and presents the Console screen. From there, the operator can type a creative brief, select an engine, and start a production with Ctrl+R. All agent reasoning is routed through the cloud LLM router, which is configured by API keys and aggregates five providers with automatic fallback.

The TUI also handles graceful shutdown. When the operator presses Ctrl+Q, the TUI cancels any running production, saves the current state, and exits cleanly. This ensures that partial work is not lost and that the system is ready for the next session.

## The Unified Entry Point

The design of the CLI as a single command with subcommands follows the principle of least surprise. Users familiar with tools like \`git\`, \`docker\`, or \`cargo\` will immediately understand the pattern: one command name, subcommands for different operations, and flags for configuration.

This design also makes the CLI easy to extend. Adding a new operation — say, a \`DeepBl4nder benchmark\` command — requires adding a new subparser to the \`build_parser()\` function and a new handler function. The existing commands are unaffected, and the new command automatically inherits the same help system, type checking, and shell completion.

The CLI is the foundation that the TUI builds on. The TUI uses the same underlying functions — \`_cmd_inspect()\`, \`_cmd_validate()\`, \`_cmd_tui()\` — that the CLI exposes. This code reuse ensures that the TUI and CLI always behave consistently, because they share the same implementation.

The CLI also serves as the system's escape hatch. When the TUI is not available — perhaps because the terminal does not support Textual, or because the operator prefers a scripting workflow — the CLI provides the same functionality in a non-interactive form. Every operation that the TUI can perform can also be performed through the CLI, ensuring that the system is accessible regardless of the operator's preferred workflow.

<Callout type="info" title="Cloud LLM Configuration">
DeepBl4nder's agents use a cloud multi-provider LLM router built on litellm, aggregating Gemini, Groq, NVIDIA, OpenRouter, and Cloudflare. At least one provider API key is required. The router defaults to \`fallback\` mode and can be set to \`vote\` mode via \`DeepBl4nder_LLM_MODE\`. Providers are discovered dynamically and each has its own health, cooldown, and budget handling.
</Callout>
`

export default function CLIPage() {
  return <MDXRenderer source={mdxContent} />
}
