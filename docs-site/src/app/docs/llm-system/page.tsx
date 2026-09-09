import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'LLM System - DeepBl4nder',
  description: 'The cloud multi-provider LLM router, model discovery, fallback strategies, and budget management.',
}

const section1 = `
# LLM System

## Cloud Multi-Provider Architecture

DeepBl4nder uses a cloud-based multi-provider LLM router built on \`litellm\`. Rather than relying on a single API or running models locally, the system aggregates five providers into a unified pool: **Gemini**, **Groq**, **NVIDIA**, **OpenRouter**, and **Cloudflare**. Each provider is configured via its own API key, and at least one key is required to use the system.

The router implements NOOA's \`UnifiedLLM\` interface, meaning every agent in the pipeline interacts with it through a single, consistent API — regardless of which provider ultimately handles the request. This abstraction decouples your agents from any specific vendor and gives you the flexibility to use whichever providers you have access to.

## Provider Configuration

Providers are configured through environment variables and an optional configuration file at \`~/.deepbl4nder/llm.json\`. The environment variable \`DeepBl4nder_LLM_PROVIDERS\` can specify a comma-separated list of providers to use, overriding the defaults.

| Provider | Environment Variable | Notes |
|---|---|---|
| Gemini | \`GEMINI_API_KEY\` | Google's Gemini models |
| Groq | \`GROQ_API_KEY\` | Low-latency inference on Groq hardware |
| NVIDIA | \`NVIDIA_API_KEY\` | NVIDIA NIM-hosted models |
| OpenRouter | \`OPENROUTER_API_KEY\` | Multi-model aggregator |
| Cloudflare | \`CLOUDFLARE_API_KEY\` + \`CLOUDFLARE_ACCOUNT_ID\` | Cloudflare Workers AI |

Each provider is registered with a set of selection rules that filter which models are available from that provider. The router performs dynamic model discovery by querying each provider's \`/models\` endpoint at startup, and applies these rules to build a curated pool of available models.

## Fallback vs Vote Modes

The router supports two operational modes, configurable at runtime.

**Fallback mode** (default) sends each request to the first healthy provider in pool order. If the request fails — due to a timeout, rate limit, or error — the router moves to the next provider in the pool and retries. This gives you reliability: as long as at least one provider is healthy, your pipeline keeps running.

**Vote mode** queries all healthy providers in parallel and collects their responses. It then applies majority voting to select the best response, using provider health scores as a tiebreaker. Vote mode is useful when you need higher confidence in the output and are willing to spend more tokens to get it.

## Health, Cooldown, and Budget

The router tracks per-provider health. When a provider fails, it is placed on a cooldown period during which it is excluded from the pool. After the cooldown expires, the provider is retried with a lightweight health check before being fully reinstated.

Budget tracking is built into the router. It monitors cumulative USD spend across all providers and can enforce a configurable budget cap. Once the cap is reached, the router stops issuing requests and returns a budget-exceeded error. This prevents runaway costs from a misbehaving pipeline or an unexpectedly long production run.

## Dynamic Model Discovery

Instead of hardcoding model names, the router queries each provider's \`/models\` endpoint to discover available models at startup. Selection rules filter these models based on criteria such as provider priority, model capabilities, and cost tiers. This means that if a provider adds or removes models, the router adapts automatically without code changes.

The selection rules are configured in \`~/.deepbl4nder/llm.json\` and can be overridden per environment. This makes it straightforward to experiment with different model configurations or restrict the pipeline to a specific provider for compliance reasons.
`

const providerPoolChart = `graph LR
    REQ["Agent Request"] --> ROUTER["LLMRouter"]
    ROUTER --> GEMINI["Gemini"]
    ROUTER --> GROQ["Groq"]
    ROUTER --> NVIDIA["NVIDIA"]
    ROUTER --> OPENROUTER["OpenRouter"]
    ROUTER --> CLOUDFLARE["Cloudflare"]
    GEMINI -->|"success"| RESP["Response"]
    GEMINI -->|"failure"| FALLBACK["Fallback"]
    FALLBACK --> GROQ`

const section2 = `
## Fallback Routing in Detail

When an agent sends a request, the router selects the first healthy provider from its pool. The pool order is determined by provider priority, which can be configured in \`~/.deepbl4nder/llm.json\`. If the selected provider fails — returns an error, times out, or returns malformed output — the router records the failure, places that provider on cooldown, and retries the request with the next provider in the pool.

This escalation continues until either a provider succeeds or all providers have been exhausted. If all providers fail, the router raises an error with details about each failure, allowing the calling agent to decide how to proceed. The escalation history is logged for debugging and monitoring.

The cooldown period is adaptive: repeated failures from the same provider increase its cooldown duration, while successful requests reset it. This prevents a provider that is experiencing a sustained outage from being hammered with retry traffic.
`

const fallbackChart = `graph TB
    REQ["Agent Request"] --> ROUTER["LLMRouter"]
    ROUTER -->|"priority 1"| P1["Provider A"]
    P1 -->|"success"| RESP["Response"]
    P1 -->|"failure"| COOLDOWN["Cooldown"]
    COOLDOWN -->|"try next"| P2["Provider B"]
    P2 -->|"success"| RESP
    P2 -->|"failure"| P3["Provider C"]
    P3 -->|"success"| RESP`

const section3 = `
## The Unified Interface

All 14 agents interact with the LLM system through NOOA's \`UnifiedLLM\` interface. The shared router instance is built via the \`build_llm()\` function in \`DeepBl4nder/llm/__init__.py\`, which always returns an \`LLMRouter\` instance (unless \`fake=True\` is passed for testing). This single function call constructs the router, registers all configured providers, and returns a client ready for use.

The interface handles provider selection, request routing, health tracking, cooldown management, and budget enforcement — all transparently to the calling agent. An agent simply sends a request with a prompt and receives a response. It does not need to know which provider handled the request, how many retries occurred, or what the current budget status is.

## Configuration File

The optional configuration file at \`~/.deepbl4nder/llm.json\` allows you to customize provider priority, selection rules, model filters, cooldown durations, and budget caps. The file is loaded at startup and merged with environment variable configuration, with environment variables taking precedence.

A minimal configuration might specify which providers to enable and their relative priorities. A full configuration might include per-provider selection rules that filter models by capability, cost tier, or context window size. The configuration is optional — with at least one API key set, the router works with sensible defaults.

## Prompt Caching

DeepBl4nder enables LiteLLM cache-control by default: each client is created with \`cache_control_injection_points=["messages"]\`, which keeps the stable request prefix (system prompt, skills, schema) in the provider's KV cache between calls. On long multi-turn runs (every agent reuses the same system prompt prefix), this measurably cuts latency and token cost. It can be disabled per environment with:

\`\`\`bash
export DeepBl4nder_LLM_CACHE=off
\`\`\`

## Live LLM Observability

Every LLM call is recorded by an in-process, thread-safe metrics sink (\`DeepBl4nder/llm/metrics.py\`), fed from the real-time agent event bridge. For each call it captures:

- **tokens** (input, output, cached) and **cost** (USD)
- **latency** per call (wall-clock between call start and completion)
- **provider/model attribution** (the actual winner, not the static pool config)
- success/failure and **cache hits**

A snapshot is exposed live to the TUI through \`EmbeddedAPI.llm_metrics()\` and rendered in the side panel (calls, cumulative cost, token count, average/p50/p95 latency, and the top agents by call volume). The same spans are appended to \`<data>/logs/llm_spans.jsonl\` for offline analysis, so you can audit cost and behavior after a run without leaving the terminal.
`

const metricsChart = `graph TB
    AGENT["Agent (NOOA)"] -->|"LLMComplete / LLMCallStart"| BRIDGE["Event Bridge"]
    BRIDGE --> METRICS["LLMMetrics sink"]
    METRICS --> JSONL["llm_spans.jsonl"]
    METRICS --> TUI["TUI side panel (live)"]
    METRICS --> STATS["routing_stats / llm_metrics()"]`

const section4 = `
## Metrics You Can Act On

The live metrics panel answers the questions that matter for an autonomous pipeline:

- **Cost**: total spend for the current run, plus per-agent and per-model breakdowns.
- **Latency**: average, p50, and p95 per call — a persistent p95 spike points to a slow provider worth reordering out of the pool.
- **Tokens**: total token burn, so you can spot a runaway agent or an oversized skill block.
- **Success rate and cache hit rate**: tells you whether prompt caching is working and whether a provider is flaky.

These numbers are consumed from the same event stream that powers the TUI, so there is no separate wiring or daemon — observability is a byproduct of the normal event flow.
`

export default function LLMSystemPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={providerPoolChart} title="Provider Pool and Fallback" />
      <MDXRenderer source={section2} />
      <MermaidDiagram chart={fallbackChart} title="Fallback Routing Flow" />
      <MDXRenderer source={section3} />
      <MermaidDiagram chart={metricsChart} title="LLM Metrics Flow" />
      <MDXRenderer source={section4} />
    </>
  )
}
