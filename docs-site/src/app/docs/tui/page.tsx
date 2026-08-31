import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'TUI Interface: Terminal-First Interaction - DeepBl4nder',
  description: 'Why DeepBl4nder chose a terminal UI over a web interface, the Textual framework, EmbeddedAPI for in-process communication, and EventBridge for real-time streaming.',
}

const mermaidChart1 = `graph TB
    subgraph Agents["Agent Layer"]
      BA["BlenderAgent"]
      DA["DirectorAgent"]
      QA["QAAgent"]
    end

    subgraph Bridge["EventBridge"]
      EB["attach_agent_bridge()"]
      BROKER["EventBroker"]
    end

    subgraph TUI["TUI Layer"]
      CS["Console Screen"]
      STREAM["Agent Stream"]
    end

    BA --> EB
    DA --> EB
    QA --> EB
    EB --> BROKER
    BROKER --> CS
    BROKER --> STREAM
  `

const section1 = `
# TUI Interface: Terminal-First Interaction

The choice to build DeepBl4nder's primary interface as a terminal application — rather than a web dashboard, a desktop GUI, or an API-only backend — was one of the most deliberate architectural decisions in the project. It was not a compromise, not a temporary solution, and not a concession to limited resources. It was a statement about what kind of interaction DeepBl4nder values: **direct, local, keyboard-driven, and fast**.

A terminal user interface provides something that web interfaces cannot: zero-latency interaction with no network overhead, no browser rendering pipeline, and no JavaScript framework initialization. When an operator presses Ctrl+R to start a production, the action travels directly from the keyboard to the Python runtime, through the EmbeddedAPI, into the PipelineRunner, and out to the agents. There is no HTTP request, no WebSocket handshake, no DOM update. The speed is the speed of Python.

But the TUI is not a throwback to the 1980s. It is built on Textual, a modern Python framework that brings rich interactive capabilities to the terminal: CSS styling, animated widgets, modal dialogs, scrollable regions, and real-time updates. The result is an interface that feels as responsive and visually rich as a web application, but with the immediacy and portability of a terminal tool.

## Why Terminal UI Over Web UI

The decision to favor terminal over web was driven by three practical observations about DeepBl4nder's use cases.

**First, DeepBl4nder runs locally.** The LLM server runs on the user's machine (or in Docker on the user's machine). The Blender worker runs locally. The production data lives on local disk. A web interface would add a network hop between the user and the system they are controlling — a hop that provides no benefit and introduces latency, complexity, and a failure mode (the web server process) that does not exist in the terminal approach.

**Second, DeepBl4nder targets developers and technical artists.** These users already live in the terminal. They use command-line tools daily, they are comfortable with keyboard-driven interfaces, and they value speed over visual polish. A terminal interface meets these users where they are, rather than forcing them to open a browser and navigate to localhost:3000.

**Third, the TUI is more portable.** It runs on any system with a terminal emulator — Linux, macOS, Windows. It does not require a browser, does not require a specific screen size, and does not require an internet connection. It works over SSH, in Docker containers, and on remote servers. This portability is essential for a system that may be deployed in diverse environments.

<Callout type="info" title="TUI Philosophy">
The TUI is not a "CLI with a nice output." It is a full interactive application with screens, widgets, keybindings, and real-time updates. It happens to run in a terminal because the terminal is the most direct, portable, and efficient interface available on every development machine.
</Callout>

## The Textual Framework

Textual is a Python framework for building rich terminal user interfaces. It provides a widget tree model, CSS-based styling, event handling, and asynchronous updates — all within the constraints of a terminal emulator.

DeepBl4nder's TUI uses Textual's screen system to organize its interface into distinct views. Each screen is a self-contained widget tree with its own layout, keybindings, and event handlers. The user navigates between screens using keyboard shortcuts, and the TUI maintains state across screen transitions.

### Console Screen

The Console screen is the primary interface for creating and managing productions. It contains a multi-line text input for the creative brief, an engine picker for selecting the target engine, run and cancel controls, and a real-time agent stream that shows what the agents are doing.

<img src="/DeepBl4nder/capture/img_console.png" alt="TUI Console Screen" className="rounded-lg border border-db-border my-6" />

The agent stream is the most distinctive feature of the Console screen. As agents reason, generate code, and execute operations, their activity appears in real-time in a scrollable region at the bottom of the screen. The stream shows which agent is active, what it is thinking, what tools it is calling, and what results it is getting. This transparency is not just informative — it is essential for debugging and for building trust in the system's decisions.

### Library Screen

The Library screen provides a browsable view of all past productions. Each production is listed with its status, brief, cost, and timestamp. Selecting a production shows its artifacts — renders, audio files, scripts, and reports — in a detailed view.

<img src="/DeepBl4nder/capture/img_library_ctrl_b.png" alt="TUI Library Screen" className="rounded-lg border border-db-border my-6" />

The Library screen also shows QA reports, which include quality scores, identified issues, and recommendations. This allows operators to review production quality without leaving the TUI, and to use the QA feedback to improve future productions.

### Settings Screen

The Settings screen allows operators to configure the pipeline's behavior. Budget limits, model selections, file paths, and advanced options like parallel execution settings and cache TTL are all configurable from this screen.

<img src="/DeepBl4nder/capture/img_setting.png" alt="TUI Settings Screen" className="rounded-lg border border-db-border my-6" />

### Search

The TUI includes a quick-search feature that allows operators to find productions, artifacts, and settings by name. The search is invoked with Ctrl+P and filters results as the operator types.

<img src="/DeepBl4nder/capture/img_search_cmd_ctrl_p.png" alt="TUI Search" className="rounded-lg border border-db-border my-6" />

## EmbeddedAPI: In-Process Communication

The TUI communicates with the production pipeline through the EmbeddedAPI — a direct, in-process interface that bypasses HTTP entirely. When the user presses Ctrl+R to start a production, the TUI calls \`EmbeddedAPI.run_production()\`, which constructs a PipelineRunner, builds the agent crew, and executes the production — all within the same Python process.

This in-process design was a deliberate choice. The alternative — running the pipeline as a separate HTTP server and communicating via REST — would add latency, require serialization/deserialization of all data, and introduce a failure mode (the HTTP connection) that does not exist in the in-process approach.

The EmbeddedAPI manages the entire lifecycle of a production: creating the production record, building the agent crew, running the pipeline, tracking costs, managing the event stream, and handling cancellation. It provides the TUI with a clean, simple interface that hides the complexity of the underlying system.

\`\`\`python
from DeepBl4nder.tui.embedded_api import EmbeddedAPI

api = EmbeddedAPI(data_dir="data", budget=1.0)

# Build the agent crew (14 agents)
api.create_agents()

# Start a production
outcome = await api.run_production(production_id)

# Check status
productions = api.list_productions()
for prod in productions:
    print("  " + prod.name + ": " + prod.status)

# Subscribe to real-time events
queue = await api.subscribe_events(production_id)
\`\`\`

The API also provides artifact management: listing artifacts for a production, downloading them, and checking QA reports. The path traversal protection built into the storage layer ensures that artifacts can only be accessed within their designated directories.

### Agent Building

When the TUI first starts a production, the EmbeddedAPI builds the full crew of 14 agents. Each agent is a NOOA agent instance with its own skills, LLM configuration, and event handlers. The agents are built once and reused across productions, avoiding the overhead of re-creation.

The agent building process includes attaching the EventBridge to each agent, which connects the agents' internal events to the TUI's event stream. This attachment is what makes the real-time agent stream possible — every LLM call, every tool invocation, and every reasoning step flows through the EventBridge to the TUI.

## EventBridge: Real-Time Streaming

The EventBridge is the nervous system of the TUI. It connects the agents' internal events — LLM calls, tool invocations, reasoning steps, errors — to the TUI's display, providing real-time visibility into what the agents are doing and why.

The EventBridge is built on the EventBroker, an in-process async pub/sub system with a ring buffer for history. When an agent emits an event — a \`BeforeTurn\`, an \`LLMComplete\`, a \`PythonOutput\` — the EventBridge normalizes it into a \`StreamEvent\` and publishes it to the broker. The TUI subscribes to the broker and receives events as they happen.
`

const section2 = `
### Event Types

The EventBridge translates NOOA's event types into a normalized format that the TUI can display. The key event types include:

**turn_start** and **turn_end** indicate when an agent begins and finishes an LLM generation turn. These events include the turn number, method name, and strategy — giving the operator visibility into the agent's reasoning process.

**llm_complete** is the most information-rich event. It includes the model used, token counts, cost, and the real provider and model from the LLM router. This event is what drives the agent stream's display of "DirectorAgent -> qwen3-8b ($0.0042, 1,247 tokens)."

**reasoning** captures the agent's chain-of-thought reasoning. This is the internal monologue that the agent produces before taking action — and it is displayed in the agent stream so the operator can understand why the agent is making specific decisions.

**tool_call** captures tool invocations. When an agent calls inspect_scene, render, or create_audio, the tool call event shows the tool name and its arguments, giving the operator visibility into what the agent is actually doing.

**python_output** captures stdout and stderr from executed Python scripts. This is essential for debugging — when a Blender script fails, the error output appears in the agent stream immediately.

**budget_alert** fires when the production exceeds its budget limit. The alert includes the budget, total cost, and overshoot amount, and it triggers an automatic production stop.

### The Ring Buffer

The EventBroker maintains a ring buffer of 1,000 events. When the buffer is full, the oldest events are dropped. This prevents memory growth during long productions — a production that runs for hours would accumulate millions of events, which would exhaust memory without the ring buffer.

The ring buffer also provides replay capability. When a new subscriber joins — for example, when the user navigates to the Console screen — the broker replays the recent history to the subscriber's queue. This ensures that the user sees the full context of the production, not just events that happened after they opened the screen.

### Fire-and-Forget Event Delivery

Events are delivered to subscribers using \`put_nowait()\`, which is non-blocking. This is a critical design choice: agent execution must never block on the UI. If the TUI is slow to render — perhaps because the terminal emulator is lagging — agent execution continues unaffected. Events accumulate in the queue and are delivered when the TUI catches up.

This fire-and-forget model ensures that the agents' performance is never degraded by the TUI's rendering performance. The agents run at full speed regardless of what the terminal is doing.

## Keybindings

The TUI uses keyboard shortcuts for all primary operations. The keybindings follow conventions that terminal users will find familiar:

- **Ctrl+Q** quits the application from any screen
- **Ctrl+B** opens the Library screen from any screen
- **Ctrl+O** opens the Settings screen from any screen
- **Ctrl+R** starts the current production on the Console screen
- **Ctrl+C** cancels the current production
- **F1** opens the help overlay
- **Tab** switches between panels on the Console screen
- **Enter** submits or confirms the current action
- **Escape** cancels or navigates back

These keybindings are designed to be discovered incrementally. The most important operations — start, cancel, navigate — are available with two-key combinations that are easy to remember. Less common operations — settings, help — are available with function keys or longer combinations.

## Ring Buffer Memory Management

The agent stream uses a ring buffer to manage memory during long productions. A typical production generates hundreds of events per minute — LLM calls, tool invocations, reasoning steps, output captures. Over a production that runs for an hour, this could accumulate to hundreds of thousands of events.

The ring buffer holds the most recent 1,000 events. When a new event arrives and the buffer is full, the oldest event is dropped. This ensures that memory usage remains constant regardless of production duration.

\`\`\`text
Ring Buffer (1000 events max)
┌─────────────────────────────────────┐
│ ┌───┬───┬───┬───┬───┬───┬───┬───┐  │
│ │ 1 │ 2 │ 3 │...│998│999│1000│   │  │
│ └───┴───┴───┴───┴───┴───┴───┴───┘  │
│ When full, oldest events are dropped│
└─────────────────────────────────────┘
\`\`\`

The 1,000-event limit was chosen based on empirical observation: it provides enough history for the user to scroll back and see what happened, while keeping memory usage under 10 MB even for the most complex productions.

<Callout type="tip" title="Performance">
The TUI processes events asynchronously and renders at up to 30fps. Events are delivered via non-blocking queues, so agent execution is never delayed by UI rendering. The ring buffer prevents memory growth during long productions. The result is an interface that remains responsive regardless of production complexity or duration.
</Callout>

## Installation and Requirements

The TUI requires Python 3.12 or later and the Textual framework. Installation is straightforward:

\`\`\`bash
# Install with TUI support
pip install -e ".[tui]"

# Launch the TUI
DeepBl4nder tui
\`\`\`

The TUI requires a terminal with 256 color support and a minimum size of 80x24 characters. Most modern terminal emulators meet these requirements. The TUI also requires the LLM models to be downloaded — the \`_tui_preflight()\` function checks for model availability at startup and warns if models are missing.
`

export default function TUIPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={mermaidChart1} title="EventBridge Architecture" />
      <MDXRenderer source={section2} />
    </>
  )
}
