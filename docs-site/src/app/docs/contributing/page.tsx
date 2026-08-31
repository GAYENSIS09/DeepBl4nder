import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Contributing: The Contribution Philosophy - DeepBl4nder',
  description: 'What areas need help, how to get started, code conventions, and the philosophy of open-source contribution to an autonomous 3D production system.',
}

const mermaidChart1 = `graph TB
    subgraph Your["Your Contribution"]
      IDEA["Idea/Issue"]
      CODE["Code"]
      TEST["Tests"]
      PR["Pull Request"]
    end

    subgraph Review["Review Process"]
      CI["CI/CD"]
      REVIEW["Code Review"]
      MERGE["Merge"]
    end

    IDEA --> CODE
    CODE --> TEST
    TEST --> PR
    PR --> CI
    CI --> REVIEW
    REVIEW --> MERGE
  `

const section1 = `
# Contributing: The Contribution Philosophy

Contributing to DeepBl4nder is not like contributing to a typical open-source library. The system is a complex orchestration of agents, plugins, bridges, validators, and UI components — each with its own domain, its own conventions, and its own set of responsibilities. A contribution to the skill system is not the same as a contribution to the codegen validator, which is not the same as a contribution to the TUI. Each area has different requirements, different testing approaches, and different levels of risk.

This guide is designed to help you navigate that complexity. It explains the areas where contributions are most needed, the conventions that the codebase follows, and the process for getting your changes reviewed and merged. It also explains the philosophy behind these conventions — not just what to do, but why.

## The Contribution Philosophy

DeepBl4nder follows three principles that should guide every contribution.

**Separation of concerns is sacred.** The system is divided into modules — agents, skills, plugins, bridges, codegen, production, TUI — and each module has a specific responsibility. A contribution to the plugin system should not leak into the agent system. A contribution to the TUI should not change the codegen validator. If you find yourself modifying multiple modules for a single change, step back and consider whether the change is too broad.

**Safety is non-negotiable.** The fail-closed principle applies not just to code execution but to code review. Changes to the security boundary — the CodePolicy, the AST validator, the BlenderBridge — require extra scrutiny. A bug in the validator could allow dangerous code to execute. A bug in the TUI is merely cosmetic. Prioritize safety-critical changes accordingly.

**Small changes are better than large changes.** A pull request that adds one skill is easier to review than one that refactors the entire plugin system. A pull request that fixes one edge case in the validator is safer than one that rewrites the validation pipeline. Aim for changes that can be reviewed in under 30 minutes.
`

const section2 = `
## Getting Started

The path from "interested contributor" to "merged pull request" follows a natural progression.

<Steps>
<Step number={1} title="Fork and Clone">
Clone the repository and create a fork under your GitHub account. This gives you a personal copy where you can make changes without affecting the main repository.
\`\`\`bash
git clone https://github.com/YOUR_USERNAME/DeepBl4nder.git
cd DeepBl4nder
\`\`\`
</Step>
<Step number={2} title="Install Development Dependencies">
Install the development dependencies, which include the testing framework, linting tools, and type checker.
\`\`\`bash
pip install -e ".[dev,tui]"
\`\`\`
</Step>
<Step number={3} title="Create a Feature Branch">
Create a branch for your changes. Use a descriptive name that indicates what you are working on.
\`\`\`bash
git checkout -b feature/add-ocean-skill
\`\`\`
</Step>
<Step number={4} title="Make Your Changes">
Write the code, following the code style guidelines below. Write tests for any new functionality. Run the full test suite to verify that nothing is broken.
</Step>
<Step number={5} title="Run the Quality Checks">
Before submitting, run the automated quality checks. These are the same checks that CI runs — if they pass locally, they will pass in CI.
\`\`\`bash
black .
ruff check .
mypy DeepBl4nder/
pytest tests/ -v
\`\`\`
</Step>
<Step number={6} title="Submit a Pull Request">
Push your branch and create a pull request. Include a clear description of what the change does and why.
</Step>
</Steps>

## Areas That Need Help

DeepBl4nder has several areas where contributions are especially valuable. These areas range from easy entry points for new contributors to complex challenges for experienced developers.

### Skills: The Knowledge Layer

The skill system is the most accessible area for new contributors. Creating a new skill requires domain knowledge, not programming expertise. If you are an expert in ocean simulation, procedural vegetation, cloth dynamics, or any other 3D production domain, you can create a skill that encodes that expertise for the agents.

A skill consists of a SKILL.md file with YAML frontmatter and a body containing concepts, patterns, and rules. The format is simple, the bar is low, and the impact is high — a well-written skill immediately improves the agents' ability to work in that domain.

Skills are also the area where the progressive disclosure philosophy has the most visible impact. A skill that is too verbose wastes context tokens. A skill that is too terse fails to provide useful guidance. Finding the right balance is an art that improves with practice and feedback.

### Plugins: External Integrations

The plugin system is designed to be extensible. If there is an external tool or service that DeepBl4nder should interact with — a new rendering engine, a new audio service, a new storage backend — a plugin can be created to bridge that integration.

Creating a plugin requires implementing the \`Plugin\` base class, providing an \`available()\` method, and registering the plugin with the \`PluginRegistry\`. The plugin should be self-contained, with no dependencies on other plugins or on the agent system.

### TUI: The User Interface

The TUI is built on Textual and is ripe for improvement. New screens, better keybindings, more informative displays, and accessibility improvements are all welcome. The TUI code is in \`DeepBl4nder/tui/\`, and the Textual documentation is excellent.

### Documentation

Documentation contributions are among the most valuable and least risky. Fixing typos, adding examples, clarifying explanations, and translating content all improve the project without introducing code changes.

### Tests

The test suite is in \`tests/\` and covers the core functionality. Adding tests for edge cases, improving test coverage for existing modules, and creating integration tests for the agent pipeline are all valuable contributions.

## Code Conventions

The codebase follows conventions that ensure consistency and readability across all contributions.

**Python style.** The codebase follows PEP 8 with a few exceptions enforced by the linter. Type hints are required for all public functions and methods. Google-style docstrings are used for all public APIs.

**Formatting.** Code is formatted with \`black\` using its default settings. There is no configuration to debate — \`black\` makes the decision, and the codebase follows it.

**Linting.** Code is linted with \`ruff\`, which is fast and comprehensive. The \`ruff check .\` command must pass before any pull request is submitted. Ruff catches common errors, enforces import ordering, and flags unused variables.

**Type checking.** Code is type-checked with \`mypy\`. The \`mypy DeepBl4nder/\` command must pass. Type hints are not optional decoration — they are a contract that documents what a function expects and returns.

**Imports.** Imports are sorted by \`ruff\` and organized into groups: standard library, third-party, and local. The order within each group is alphabetical.

\`\`\`bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy DeepBl4nder/

# Run tests
pytest tests/ -v
\`\`\`

## Pull Request Process

Every pull request goes through a review process that ensures quality and consistency. The review is not a formality — it is a genuine evaluation of whether the change improves the project.

<Callout type="warning" title="Ask First">
Before starting work on a new feature, please open an issue to discuss the approach. This ensures your contribution aligns with the project's direction and avoids duplicate effort. A 5-minute conversation before coding can save hours of rework after coding.
</Callout>

### What Reviewers Look For

Reviewers evaluate pull requests on several dimensions:

**Correctness.** Does the change do what it claims? Are there edge cases that are not handled? Are there off-by-one errors, race conditions, or resource leaks?

**Safety.** Does the change affect the security boundary? If so, does it maintain the fail-closed principle? Are there paths where dangerous code could be executed?

**Consistency.** Does the change follow the existing code conventions? Does it use the same patterns as neighboring code? Does it introduce new patterns that should be documented?

**Testability.** Does the change include tests? Do the tests cover the happy path and the error paths? Are the tests deterministic?

**Documentation.** Does the change include documentation updates if needed? Are new functions documented with docstrings? Are new skills documented with examples?

### The PR Checklist

Every pull request should include:

- Code that follows the project style guidelines
- Tests for new functionality
- Passing test suite (all existing tests still pass)
- Documentation updates if the change affects user-facing behavior
- Clear commit messages that describe what changed and why
- No secrets, API keys, or credentials committed to the repository

## Good First Issues

If you are new to the project, look for issues tagged with \`good-first-issue\`. These are changes that are well-scoped, low-risk, and suitable for first-time contributors:

- Add a new skill for a specific domain (e.g., ocean simulation, cloth dynamics)
- Improve error messages in plugins
- Add tests for existing functionality
- Fix documentation typos
- Add CLI flags for existing commands

These issues are specifically prepared for new contributors. They come with clear requirements, minimal risk, and a straightforward implementation path.

## Project Structure

The project structure reflects the separation of concerns that guides the architecture:

- \`DeepBl4nder/agents/\` contains the 14 NOOA agents that drive the production pipeline
- \`DeepBl4nder/skills/\` contains the 36+ skill definitions that provide domain knowledge
- \`DeepBl4nder/plugins/\` contains the 10 built-in plugins that bridge external systems
- \`DeepBl4nder/bridges/\` contains the engine bridges for Blender, UE5, Godot, and AI Video
- \`DeepBl4nder/codegen/\` contains the AST validator and CodePolicy
- \`DeepBl4nder/production/\` contains the pipeline orchestrator and event system
- \`DeepBl4nder/tui/\` contains the Textual terminal user interface
- \`DeepBl4nder/llm/\` contains the LLM routing and model management
- \`tests/\` contains the test suite

When making a change, start by identifying which module it belongs to, and keep your changes within that module's boundaries.

<Callout type="tip" title="Need Help?">
If you have questions about the architecture, the conventions, or the contribution process, open an issue and ask. The maintainers are happy to help new contributors navigate the codebase. The worst thing you can do is make a change that does not fit the project's architecture — and the easiest way to avoid that is to ask before you start.
</Callout>

## License

By contributing to DeepBl4nder, you agree that your contributions will be licensed under the Apache 2.0 License. This is a permissive license that allows others to use, modify, and distribute your contributions without restriction.
`

export default function ContributingPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="Contributor Workflow" />
      <MDXRenderer source={section2} />
    </>
  )
}
