import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'CodeGen: Fail-Closed Code Execution - DeepBl4nder',
  description: 'The philosophy of fail-closed code execution, AST validation as a security layer, CodePolicy rules, and the 8 quality checks that ensure production-ready output.',
}

const mermaidChart1 = `graph LR
    LLM["LLM Output"] --> AST["AST Parser"]
    AST --> POLICY["CodePolicy"]
    POLICY -->|Pass| QUALITY["Quality Checks"]
    QUALITY -->|Pass| EXEC["Execute"]
    QUALITY -->|Fail| FEEDBACK["Feedback to Agent"]
    POLICY -->|Fail| BLOCK["Blocked"]
  `

const section1 = `
# CodeGen: The Philosophy of Fail-Closed Code Execution

When an LLM generates Python code for Blender, that code will be executed. Not reviewed by a human, not run in a sandbox for observation, but executed with the full power of the Python interpreter and the Blender API. This is the fundamental reality of Code-as-Action: the agent's reasoning produces executable code, and that code must run correctly and safely.

DeepBl4nder treats this reality with the gravity it deserves. The CodeGen system is built on a single, unyielding principle: **fail-closed**. Any code that cannot be definitively validated as safe is blocked. Not flagged, not warned, not allowed with a caveat — blocked. The system defaults to the assumption that unknown code is dangerous, and the burden of proof is on the code to demonstrate otherwise.

This is a deliberate architectural choice that prioritizes safety over convenience. In a system where LLMs generate code that will execute autonomously, the alternative — fail-open, where code runs unless it is known to be dangerous — is an invitation to catastrophe. An LLM can hallucinate an \`os.system()\` call, misimport a forbidden module, or construct a path traversal attack without any malicious intent. The fail-closed model catches all of these cases because it does not need to distinguish between accidental and intentional danger. It simply blocks anything it cannot verify as safe.

The fail-closed principle is borrowed from security engineering, where it is the standard for systems that handle sensitive data. A firewall that blocks all traffic by default and only allows known-safe connections is fail-closed. A medical device that stops when it detects an anomaly rather than continuing with potentially dangerous behavior is fail-closed. DeepBl4nder's code validator follows the same philosophy: when in doubt, do not execute.

## The Validation Pipeline

The journey from LLM output to executed code passes through a rigorous validation pipeline. This pipeline is not optional, not configurable for production use, and not bypassable. Every script, regardless of its source or apparent simplicity, must pass through every stage.
`

const section2 = `
The first stage is **AST parsing**. The script is parsed into an Abstract Syntax Tree using Python's built-in \`ast\` module. This is a pure analysis step — no code is executed, no imports are resolved, no side effects occur. If the script contains syntax errors, the pipeline stops immediately with a clear error message indicating the line and nature of the problem.

The AST is the script's structural representation. It captures the hierarchy of statements, expressions, and declarations without executing any of them. This is crucial for security: by analyzing the structure rather than running the code, the validator can identify dangerous patterns without exposing the system to them.

The second stage is **CodePolicy enforcement**. The AST is walked node by node, and each node is checked against the CodePolicy. Imports are checked against the allowlist. Function calls are checked against the forbidden builtins list. Attribute accesses are checked against the forbidden attributes list. Any violation produces a validation error that blocks the script.

The CodePolicy check is fast — it operates on the AST, not on the code text, so it does not need to parse strings or interpret comments. The entire policy check for a typical script completes in under 10 milliseconds, which means it adds negligible overhead to the execution pipeline.

The third stage is **semantic quality checks**. These are not security checks — they are quality checks that identify common issues in generated Blender scripts. Missing render output paths, unset render engines, missing camera setups, low sample counts, absent denoising, and missing compositing nodes are all flagged as warnings. In strict mode, these warnings are promoted to errors, blocking the script until the quality issues are resolved.

The quality checks are the most nuanced part of the pipeline. They do not block dangerous code — they flag suboptimal code. A script that renders without setting \`scene.render.filepath\` is not dangerous, but it will produce output in an unexpected location. A script that does not set the render engine is not dangerous, but it will default to EEVEE when the user might have intended Cycles. These checks help the agent produce better code, not just safer code.

## CodePolicy: The Security Boundary

The CodePolicy is the security boundary of the CodeGen system. It is a frozen dataclass — immutable at runtime — that defines three things: which modules can be imported, which builtins cannot be called, and the maximum source code length.

\`\`\`python
from dataclasses import dataclass, field

ALLOWED_IMPORTS: frozenset[str] = frozenset({
    "bpy", "math", "mathutils", "random", "json"
})

FORBIDDEN_BUILTINS: frozenset[str] = frozenset({
    "exec", "eval", "compile", "open", "input", "__import__"
})

@dataclass(frozen=True)
class CodePolicy:
    allowed_imports: frozenset[str] = field(
        default_factory=lambda: ALLOWED_IMPORTS
    )
    forbidden_builtins: frozenset[str] = field(
        default_factory=lambda: FORBIDDEN_BUILTINS
    )
    max_source_length: int = 100_000
\`\`\`

The **allowed imports** list is deliberately short: \`bpy\` for the Blender Python API, \`math\` and \`mathutils\` for mathematical operations, \`random\` for procedural generation, and \`json\` for data parsing. Every other module is blocked. This is not because other modules are inherently dangerous — \`pathlib\`, \`os.path\`, and \`typing\` are perfectly safe — but because the cost of maintaining a larger allowlist outweighs the benefit. If a generated script needs \`pathlib\`, the LLM can construct paths using string operations instead.

The short allowlist also has a practical benefit: it makes the policy easy to audit. When a new module needs to be added, the change is small, focused, and easy to review. A long allowlist would be harder to maintain and easier to get wrong.

The **forbidden builtins** list blocks the functions that can circumvent the validation pipeline. \`exec()\` and \`eval()\` can execute arbitrary code strings. \`compile()\` can prepare code for later execution. \`__import__()\` can dynamically import modules outside the allowlist. \`open()\` can read and write arbitrary files. \`input()\` can block execution waiting for user input. None of these are needed for legitimate Blender scripting.

The **max source length** limit of 100,000 characters is a defense against pathological LLM output. An LLM that enters a loop or generates excessively long code could consume unreasonable resources during validation. The limit ensures that validation completes quickly regardless of the script's size.

### The Forbidden Attributes Check

Beyond the builtins list, the validator checks attribute accesses against a list of forbidden attribute combinations. The most important of these are the subprocess-related calls: \`subprocess.Popen\`, \`subprocess.run\`, \`subprocess.call\`, \`os.system\`, and \`os.popen\`. These combinations are blocked even if the \`subprocess\` module is not in the forbidden builtins list, because they represent the most common patterns for executing system commands.

The attribute check is more granular than the import check. It does not block all uses of the \`os\` module — only the specific attributes that can execute system commands. This allows scripts to use \`os.path\` for path manipulation while blocking \`os.system\` for command execution.

### What Gets Blocked

The CodePolicy blocks several categories of operations that represent security risks:

<Callout type="danger" title="Security Rules">
The following operations are always blocked in strict mode, regardless of context:

- **Dynamic code execution**: \`exec()\`, \`eval()\`, \`compile()\` — these can execute arbitrary strings as Python code, completely bypassing the validation pipeline
- **Dynamic imports**: \`__import__()\` — this can import any module, including those not in the allowlist
- **System commands**: \`os.system()\`, \`os.popen()\`, \`subprocess.Popen()\`, \`subprocess.run()\`, \`subprocess.call()\` — these can execute arbitrary shell commands
- **Network operations**: \`socket\`, \`requests\`, \`urllib\` — these can exfiltrate data or download malicious code
- **Path traversal**: File write operations outside the workspace directory
- **Native code**: \`ctypes\` — this can load and call native libraries
</Callout>

### What Gets Allowed

The CodePolicy allows the operations that are essential for legitimate Blender scripting:

\`\`\`python
# ALLOWED: Standard bpy operations
import bpy
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.render.render(write_still=True)

# ALLOWED: Math and procedural generation
import math
import random
from mathutils import Vector, Matrix

# ALLOWED: File operations within workspace
bpy.ops.wm.save_as_mainfile(filepath="/data/output.blend")
\`\`\`

The key insight is that the allowlist is not a whitelist of "good" operations — it is a whitelist of "necessary" operations. The system errs on the side of restriction because the cost of blocking safe code (the LLM regenerates with a different approach) is far lower than the cost of executing dangerous code (compromise of the host system).

## The 8 Quality Checks

Beyond security, the CodeGen system performs eight semantic quality checks that identify common issues in generated Blender scripts. These checks do not block execution in their default mode — they produce warnings that inform the agent about potential problems. In strict mode, however, warnings are promoted to errors, ensuring that production output meets high quality standards.

**Check 1: Render Output Path.** The validator verifies that \`scene.render.filepath\` is set to an absolute path. In headless mode, Blender's default relative path (\`//\`) resolves to an unpredictable location, causing renders to be lost. This check catches the issue before rendering begins, saving the time and compute resources that a lost render would waste.

**Check 2: Render Engine.** The validator checks that \`scene.render.engine\` is explicitly set. Without this, Blender defaults to EEVEE, which may not be appropriate for production-quality output. The check warns the agent to specify the engine intentionally, ensuring that the rendering engine matches the production's quality requirements.

**Check 3: Compositing Nodes.** The validator looks for compositing node setup in the script. Without compositing, the output is a raw render with no post-processing. This check reminds the agent that production-quality output typically requires color grading, denoising, or other compositing operations.

**Check 4: Materials.** The validator checks that materials are created in the script. Without materials, the scene renders with default gray shading. This check catches scripts that model geometry but forget to apply materials — a common oversight in generated code.

**Check 5: Camera Setup.** The validator verifies that a camera is configured. In headless mode, Blender may not have a default camera, causing renders to fail silently. This check ensures the camera is explicitly set, preventing wasted render cycles.

**Check 6: Sample Count.** The validator extracts the render sample count and warns if it is below 128. Low sample counts produce noisy output that fails quality assessment. The check guides the agent toward production-appropriate settings.

**Check 7: Denoising.** The validator checks whether denoising is enabled. Without denoising, even high sample counts may produce visible noise in complex scenes. This check reminds the agent to enable denoising for clean output.

**Check 8: Render Passes.** When compositing is enabled, the validator checks whether render passes (depth, normal, mist) are configured. Without passes, the compositor has limited data to work with, restricting post-processing options.

<Callout type="info" title="Quality vs Security">
The quality checks are fundamentally different from the security checks. Security checks block scripts that could cause harm. Quality checks warn about scripts that could produce suboptimal output. Both are important, but they serve different purposes. In development mode, quality warnings are informational. In production mode (strict), they become errors because suboptimal output wastes resources and fails quality assessment.
</Callout>

## Validation Modes

The CodeGen system supports three validation modes, each designed for a different context:

In **strict mode**, all security checks are enforced and all quality warnings are promoted to errors. This is the default mode for production use, where every script must pass every check before execution. Strict mode is the fail-closed philosophy in its purest form.

In **permissive mode**, security checks are enforced but quality warnings remain as warnings. Scripts with quality issues are allowed to execute, but the issues are logged for review. This mode is useful during development, when the priority is quick iteration rather than production polish.

In **disabled mode**, no validation is performed. This mode exists only for testing purposes and should never be used in production. It is the equivalent of disabling all security features on a computer because they slow down your workflow — technically possible, but inadvisable.

The mode selection is not just a configuration flag — it changes the behavior of the entire validation pipeline. In strict mode, the \`ASTValidator\` runs with \`strict=True\`, which promotes all warnings to errors. In permissive mode, warnings are logged but do not affect the validation result. In disabled mode, the validator returns a valid report without performing any checks.

## Integration with BlenderAgent

The BlenderAgent uses the CodeGen validator as an integral part of its CodeAct strategy. When the agent generates a Blender script, it immediately validates the script. If validation fails, the agent receives the specific error messages and can regenerate the script with corrections.

\`\`\`python
class BlenderAgent(Agent):
    @strategy(CodeActStrategy())
    async def build_scene(self, scene: SceneSpec) -> BlenderScript:
        # Generate code via LLM
        code = await self.runtime.generate(
            prompt=f"Create a Blender scene: {scene.description}",
            output_model=BlenderScript,
        )

        # Validate before execution
        report = validate_for_worker(code.code, mode="strict")

        if not report.ok:
            # Provide specific feedback for regeneration
            feedback = "\\n".join(report.errors)
            code = await self.runtime.generate(
                prompt=f"Fix these validation errors:\\n{feedback}",
                output_model=BlenderScript,
            )

        # Execute validated code
        result = self.bridge.execute_python(code.code)
        return code
\`\`\`

This feedback loop is one of the most powerful aspects of the system. Rather than simply blocking bad code and giving up, the agent receives detailed information about what went wrong and can fix it. The result is that the system is self-correcting: initial code generation may fail validation, but the agent learns from the errors and produces correct code on subsequent attempts.

The validator also produces a \`ValidationReport\` that includes the list of imports found in the script. This information is useful for debugging and for understanding what the script actually does — if the report shows an import of \`subprocess\`, something has gone wrong even if the import was blocked.

## Extending the Policy

The CodePolicy is designed to be extended as the system evolves. New allowed modules can be added to the \`ALLOWED_IMPORTS\` frozenset, and new forbidden builtins can be added to the \`FORBIDDEN_BUILTINS\` frozenset. However, all changes to the policy require review because they affect the security boundary of the system.

Adding a module to the allowlist means that every generated script will be able to import that module. Adding a builtin to the forbidden list means that every generated script will be blocked from calling that function. These are system-wide changes that affect every production run, and they must be evaluated carefully.

The policy is defined in \`DeepBl4nder/codegen/policy.py\` and the validator is in \`DeepBl4nder/codegen/validator.py\`. Both files are small, focused, and easy to understand. The entire security boundary of the system is defined in less than 200 lines of code, which means it can be audited by a single developer in an afternoon.

This smallness is a feature, not a limitation. A security boundary that is too large to understand is a security boundary that cannot be trusted. By keeping the policy and validator small and focused, DeepBl4nder ensures that the security boundary is transparent, auditable, and trustworthy.
`

export default function CodegenPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="Code Validation Pipeline" />
      <MDXRenderer source={section2} />
    </>
  )
}
