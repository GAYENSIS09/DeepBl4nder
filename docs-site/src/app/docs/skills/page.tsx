import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Skills - Progressive Disclosure of Domain Knowledge - DeepBl4nder',
  description: 'How 36+ skills provide on-demand expertise through progressive loading, and why context efficiency is the foundation of every agent interaction.',
}

const mermaidChart1 = `graph LR
    A["Agent"] -->|discovers| B["Skill Summary"]
    B -->|loads| C["SKILL.md Content"]
    C -->|selects| D["Reference Files"]
    D -->|applies| E["Action"]
  `

const mermaidChart2 = `graph TB
    subgraph Skills["Skill Categories"]
      subgraph Core["3D & Modeling (8+)"]
        BP["blender-python"]
        MD["modeling"]
        AS["assets"]
        UV["uv"]
        TX["texturing"]
        SH["shading"]
        RG["rigging"]
        LG["lighting"]
        RN["rendering"]
      end

      subgraph Narrative["Narrative (3)"]
        ST["storytelling"]
        DL["dialogue"]
        SB["storyboard"]
      end

      subgraph Quality["Quality (3)"]
        QA["qa"]
        CT["continuity"]
        FE["feasibility"]
      end

      subgraph Audio["Audio (3)"]
        SD["sound-design"]
        MU["music"]
        VO["voice"]
      end

      subgraph Integration["Integration (5+)"]
        TR["translation"]
        SUB["subtitles"]
        AN["animation"]
        SM["simulation"]
        CP["compositing"]
      end
    end
  `

const section1 = `
# Skills: Progressive Disclosure of Domain Knowledge

In the world of autonomous 3D production, an agent faces a fundamental paradox: it needs deep domain expertise to perform well, but loading all that expertise at once would overwhelm the very context window that makes reasoning possible. DeepBl4nder resolves this tension through a principle borrowed from cognitive science and user interface design — **progressive disclosure** — applied not to human users, but to the agents themselves.

A skill in DeepBl4nder is not an agent, not a tool, and not a plugin. It is a structured unit of knowledge: a collection of instructions, rules, reference material, and examples that an agent can load on-demand to become temporarily expert in a specific domain. When the BlenderAgent needs to generate a Python script for rigging a character, it does not need to know the nuances of sound design. When the AudioAgent is composing a soundscape, it does not need to know the intricacies of UV unwrapping. Skills make this selective expertise possible without bloating the context.

## The Philosophy of Progressive Loading

The core insight behind progressive disclosure is that **not all knowledge is needed at the same time**. Rather than loading all 36+ skill definitions into an agent's context at initialization — which would consume precious tokens before a single task has been attempted — DeepBl4nder loads skills in stages. Each stage provides just enough information for the agent to decide whether it needs deeper knowledge, and only when that deeper knowledge is needed does it get loaded.
`

const section2 = `
At **discovery time**, when an agent is first initialized, it receives only a list of skill names and their one-line descriptions. This costs almost nothing in context — a few dozen tokens per skill. The agent knows that the "blender-python" skill exists, knows it covers "Blender Python API for script generation," and knows where to find it. That is all it needs to know at this stage.

At **load time**, when the agent determines that a particular skill is relevant to the current task, it loads the full SKILL.md file. This document contains the core concepts, common patterns, rules, and code examples that the agent needs to produce correct output. The loaded content is targeted and focused — it does not contain everything Blender could do, only what is most commonly needed.

At **reference time**, during execution, the agent can access specific files within the skill's references directory. If it needs detailed documentation on a particular Blender module, it loads that one reference file rather than the entire documentation set. This is the finest granularity of knowledge retrieval.

The result is that an agent working on a simple scene might load only two or three skills at their summary level, pull in one full SKILL.md for the primary skill, and access two reference files. The context cost is perhaps 4,000 tokens instead of the 60,000+ that would be required if all skills were loaded at once. That difference is the difference between an agent that can reason clearly and one that drowns in noise.

<Callout type="info" title="Context Efficiency">
Progressive loading reduces context consumption by approximately 60% compared to injecting all skills at once. In a system where context windows are the scarcest resource, this is not a luxury — it is a survival strategy. Every token spent on irrelevant knowledge is a token stolen from reasoning about the actual task.
</Callout>

## The SKILL.md Format

Every skill in DeepBl4nder is defined by a directory containing a SKILL.md file with YAML frontmatter. This format was chosen deliberately for several reasons. Markdown is human-readable and human-writable, which means domain experts who are not software engineers can author and maintain skills. The YAML frontmatter provides machine-parseable metadata — the skill's name, description, and tags — without requiring a separate configuration file. And the directory structure allows skills to include supplementary materials like reference documents, code examples, and reusable scripts.

A SKILL.md file begins with frontmatter that declares the skill's identity:

\`\`\`markdown
---
name: blender-python
description: Blender Python API for script generation
tags: [blender, python, 3d]
---

# Blender Python API

## Core Concepts
- bpy.context.scene for scene access
- bpy.data for data blocks
- bpy.ops for operators

## Rules
- Always use bpy.ops.object.select_all for selection
- Save scene after modifications
\`\`\`

The frontmatter is minimal by design. The name is the unique identifier used in agent configurations and the skill registry. The description is the single sentence loaded at discovery time. The tags enable search and filtering but are not used in the loading pipeline itself.

The body of the SKILL.md file is where the real knowledge lives. It is structured with clear headings, concise rules, and embedded code examples. The conventions are straightforward: describe the core concepts first, show common patterns with working code, and then state the rules that the agent must follow. Rules are not suggestions — they are constraints that ensure generated code and decisions are consistent with the domain's requirements.

## The Skill Catalog: 36+ Skills Across Every Aspect of 3D Production

DeepBl4nder ships with over 36 skills, each covering a specific domain of 3D production. The breadth is intentional: the system is designed to handle the entire pipeline from story development through final compositing, and that requires expertise at every stage.

The **3D and Modeling** category contains the foundational skills: blender-python for the Blender Python API, modeling for mesh creation and manipulation, assets for asset management and library operations, uv for UV unwrapping and layout, texturing for material creation and texture painting, shading for shader development, rigging for character and mechanical rigging, lighting for scene illumination, and rendering for output generation. These skills form the backbone of the BlenderAgent's expertise, and they are the ones most frequently loaded during production.

The **Narrative** category covers the creative foundation: storytelling for narrative structure, dialogue for character voice and conversation, and storyboard for visual planning. These skills are used by the StoryAgent and StoryboardAgent before any 3D work begins.

The **Quality** category ensures production standards: qa for quality assessment, continuity for visual and narrative consistency, and feasibility for technical viability checks.

The **Audio** category handles sound: sound-design for audio production, music for composition, and voice for vocal performance and narration.

The **Engine-Specific** category provides deep expertise for each target engine: cinematography for camera work, composition for visual arrangement, camera for camera mechanics, lighting for engine-specific illumination, and rendering for engine-specific output.

The **Integration** category bridges different production stages: translation for localization, subtitles for captioning, animation for motion, simulation for physics, and compositing for post-processing.
`

const section3 = `
## How Skills Map to Agents

Each agent in DeepBl4nder is configured with a specific set of skills that match its responsibilities. This mapping is not arbitrary — it reflects the principle that an agent should only carry the knowledge it actually needs.

The **BlenderAgent** carries the heaviest skill load: blender-python, modeling, assets, uv, texturing, shading, rigging, lighting, and rendering. This is because the BlenderAgent is responsible for generating and executing Blender Python scripts for nearly every aspect of 3D scene creation. It needs to be a generalist across all Blender domains.

The **StoryAgent** carries only storytelling and dialogue. Its job is to develop the narrative foundation — the brief, the character arcs, the emotional beats — and it does not need to know how meshes are constructed.

The **DirectorAgent** carries cinematography and composition. It translates narrative intent into visual language: camera positions, shot compositions, and visual pacing.

The **QAAgent** carries qa, continuity, and feasibility. It is the quality gatekeeper, and its expertise is in evaluation rather than creation.

The **AudioAgent** carries sound-design. The **MusicComposerAgent** carries music. The **SoundDesignerAgent** carries sound-design. The **CompositingAgent** carries compositing. Each audio and post-production agent has focused expertise in its narrow domain.

This one-to-many mapping between skills and agents is a core architectural decision. It means that the StoryAgent never wastes context tokens on rendering parameters, and the BlenderAgent never wastes context tokens on dialogue structure. Each agent is lean and focused, carrying only the knowledge it needs to perform its role well.

## The SkillRegistry Singleton

The SkillRegistry is the central authority for skill discovery and loading. It is implemented as a module-level singleton — a single instance that is shared across all agents and all operations. This is not an accident of implementation; it is a deliberate design choice rooted in the observation that skills are read-only knowledge. There is no reason to load the same SKILL.md file multiple times or maintain multiple copies of the same metadata.

The registry works by scanning the \`skills/\` directory for subdirectories containing SKILL.md files. Each discovered skill becomes a \`SkillInfo\` dataclass holding the skill's name, description (extracted from the YAML frontmatter), and filesystem path. The discovery process is lazy — it happens once, on first access, and the results are cached.

\`\`\`python
from DeepBl4nder.skills.registry import get_default_registry

registry = get_default_registry()

# Level 1: Discover all skills (cheap — only names and descriptions)
skills = registry.discover()
for skill in skills:
    print(skill.name + ": " + skill.description)

# Level 2: Load a specific skill (expensive — full SKILL.md content)
blender_skill = registry.resolve("blender-python")
# blender_skill is a NOOA TextSkill, ready for context injection
\`\`\`

The two-level API — \`discover()\` for cheap metadata and \`resolve()\` for full content — enforces the progressive disclosure pattern at the code level. Agents cannot accidentally load all skills because the registry does not expose a method to do so. They must explicitly choose which skill to resolve, and that choice is guided by the summaries they received at discovery time.

## Token Budget Tradeoffs

Every design decision in the skill system ultimately comes down to token economics. An LLM context window is a finite resource, and every token spent on skill content is a token not available for the conversation history, the current task description, or the model's own reasoning.

Consider the math. A typical SKILL.md file is between 500 and 2,000 tokens. The reference files within a skill add another 500 to 5,000 tokens. If all 36 skills were loaded at their summary level, that would cost approximately 1,000 tokens. If all 36 skills were loaded at their full SKILL.md level, that would cost approximately 36,000 tokens. If all reference files were loaded as well, the cost could exceed 100,000 tokens.

The progressive disclosure model means that a typical production run loads perhaps 5 to 8 skills at their summary level (500 tokens), 2 to 3 skills at their full SKILL.md level (3,000 tokens), and 1 to 2 reference files (1,000 tokens). The total cost is roughly 4,500 tokens — a 96% reduction compared to loading everything.

This is not just an optimization. It is a design philosophy that shapes every aspect of the skill system. Skills are kept focused and concise precisely because their content must justify its token cost. Reference files are separated from SKILL.md precisely because most execution paths do not need them. The registry is a singleton precisely because redundant loading would double the cost for no benefit.

<Callout type="tip" title="Skill Design Principles">
When creating custom skills, follow these principles to minimize token cost while maximizing utility: keep SKILL.md under 1,500 tokens, put detailed documentation in separate reference files, use code examples liberally (they are self-documenting), and state rules explicitly rather than implying them. Every token in a skill file should earn its place.
</Callout>

## Creating Custom Skills

The skill system is designed to be extensible. Any team member can create a new skill by following a simple convention: create a directory under \`skills/\`, write a SKILL.md file with the required frontmatter, and optionally add reference and example subdirectories.

The process of creating a skill follows a natural progression from identification to documentation to validation:

<Steps>
<Step number={1} title="Identify the Domain">
Determine what specific knowledge or procedure the skill should encode. A good skill has a single, clear responsibility. "Blender Python API" is a good skill name; "3D Production" is too broad.
</Step>
<Step number={2} title="Write the SKILL.md">
Begin with the YAML frontmatter — name, description, and tags. Then write the body: core concepts first, common patterns with code examples, and explicit rules. Keep the content focused on what an agent needs to know to perform tasks in this domain.
</Step>
<Step number={3} title="Add Reference Material">
If the domain is complex enough to warrant detailed documentation, create a \`references/\` directory and add targeted reference files. Each file should cover one specific aspect of the domain.
</Step>
<Step number={4} title="Add Examples">
Create an \`examples/\` directory with commented code examples that demonstrate common patterns. These examples serve as both documentation and validation — if an agent can follow the examples and produce correct output, the skill is working.
</Step>
<Step number={5} title="Register with an Agent">
Add the skill to the appropriate agent's configuration. The BlenderAgent should not carry sound-design skills, and the AudioAgent should not carry modeling skills. Match the skill to the agent's responsibilities.
</Step>
</Steps>

## Skill vs Tool vs Plugin

It is worth clarifying the distinction between skills, tools, and plugins, because these three concepts are often confused. A **skill** is knowledge — it tells an agent how to think about a domain, what patterns to follow, and what rules to obey. A **tool** is an action primitive — a function that performs a specific operation like inspecting a scene or rendering an image. A **plugin** is a bridge to an external system — a wrapper that communicates with Blender, FFmpeg, or another service.

Skills inform reasoning. Tools execute actions. Plugins connect to the outside world. An agent uses skills to decide what to do, tools to do it, and plugins to interact with external systems. The three work together but serve fundamentally different purposes.
`

export default function SkillsPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="Progressive Skill Loading Stages" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={mermaidChart2} title="Complete Skill Taxonomy" />
      <MDXRenderer source={section3} />
    </>
  )
}
