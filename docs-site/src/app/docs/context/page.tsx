import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Context Management - DeepBl4nder',
  description: 'How DeepBl4nder manages context windows, token budgets, and prompt caching.',
}

const section1 = `
# Context Management

## The Context Window Problem

Language models have a fundamental limitation: they can only process a fixed number of tokens in a single request. DeepBl4nder's largest model supports 32K tokens, which sounds generous until you realize how quickly that budget fills up. A typical agent's context includes a system prompt explaining the agent's role and capabilities, summaries of relevant skills, domain schema definitions, conversation history, dynamic context like QA feedback, and the user's creative brief. Each of these components consumes tokens, and together they can easily exceed the model's capacity.

The context management system exists to solve this problem intelligently. Instead of naively truncating everything to fit, it makes deliberate decisions about what to keep, what to summarize, and what to discard entirely. These decisions are based on a deep understanding of how language models use context — which parts of the prompt are most influential, which parts can be compressed without losing meaning, and which parts can be safely dropped without affecting output quality.

## The Three Pillars of Context Management

DeepBl4nder's context management rests on three pillars, each addressing a different aspect of the problem.

**Context Injection** is the process of adding runtime information to an agent's context before each LLM call. This is where pipeline events, QA feedback, and human-in-the-loop comments enter the picture. The ContextInjector adds these dynamic elements to the context dictionary, ensuring that agents have the most current information about the production state.

**Context Pruning** is the process of reducing the context to fit within token budgets. The ContextPruner deduplicates content by computing MD5 hashes of each context element and removing duplicates. It then truncates each context type to its allocated budget, using intelligent truncation that breaks at word or sentence boundaries rather than cutting mid-token. When a context element exceeds its budget, it is summarized before truncation.

**Prompt Caching** is the process of maximizing KV cache efficiency on the LLM provider. The PromptCacheManager separates context into PREFIX blocks (stable across turns) and SUFFIX blocks (volatile, recomputed per turn). Stable blocks like the system prompt and skill summaries are cached and reused across multiple turns. Volatile blocks like conversation history and dynamic context are recomputed each turn. This separation maximizes the cache hit rate, which directly translates to faster response times.
`

const chart1 = `graph TB
    RAW["Raw Context"] --> PRUNE["Pruner"]
    PRUNE --> DEDUP["Deduplicator"]
    DEDUP --> CACHE["PromptCache"]
    CACHE --> INJECT["ContextInjector"]
    SKILL["Skill Loader"] --> INJECT
    SCHEMA["SchemaVectorStore"] --> INJECT
    INJECT --> LLM["LLM Context Window"]`

const section2 = `
## How Context Injection Works

When an agent is about to make an LLM call, the ContextInjector builds a dictionary of runtime variables and adds them to the agent's context. There are three types of injected context, each serving a different purpose.

**Run History** injects the last eight events from the EventLog. These events tell the agent what steps have already completed, what errors have occurred, and what the current pipeline state is. Without this context, an agent would have no awareness of its surroundings — it would process each request in isolation, unaware of what came before.

**Revision Feedback** is injected only during revision loops. When the QA agent identifies issues, it generates a RevisionSpec that targets the specific agent responsible. The ContextInjector formats these issues and adds them to the targeted agent's context. This means the agent sees exactly what went wrong and where, enabling surgical fixes rather than wholesale regeneration.

**Human Feedback** comes from revision request files that users can create in the production directory. This is the Human-In-The-Loop mechanism that allows users to provide direct feedback on any step. The ContextInjector reads these files and adds the feedback to the relevant agent's context, ensuring that human preferences are respected throughout the pipeline.

Here is a simplified view of the ContextInjector API:

\`\`\`python
from DeepBl4nder.context.injector import ContextInjector

injector = ContextInjector(max_tokens=8192)
injector.add_system_prompt(system_prompt)
injector.add_schemas(relevant_schemas)  # from SchemaVectorStore
injector.add_skill(blender_skill)       # loaded via SkillRegistry
context = injector.build()              # pruned, deduped, cached
\`\`\`

## How Context Pruning Works

The ContextPruner operates on a set of token budgets that define how much context each element is allowed to consume. The system prompt gets 3,000 tokens. Available skill summaries get 800 tokens. Each individually loaded skill gets 1,200 tokens. Domain schema injections get 600 tokens. The creative brief gets 400 tokens. Dynamic context gets 500 tokens. Conversation history gets 2,000 tokens.

These budgets are not arbitrary. They are calibrated based on the relative importance of each context type. The system prompt is the most important because it defines the agent's behavior and capabilities. Skills are next because they provide domain-specific knowledge. Domain schemas help the agent understand the data structures it works with. The brief provides the creative intent. Dynamic context provides runtime state. History provides continuity across turns.

The pruning process is more sophisticated than simple truncation. First, the pruner computes MD5 hashes of all context elements and removes duplicates. This prevents the same information from being injected twice, which can happen when multiple context sources overlap. Then, for each context type, the pruner checks whether the content fits within its budget. If it does, the content is passed through unchanged. If it does not, the pruner attempts to summarize the content, then truncates at a word boundary if summarization is not sufficient.

## How Prompt Caching Works

The PromptCacheManager exploits a fundamental property of language model inference: the key-value pairs computed for earlier tokens are cached and reused for later tokens. If the first 1,000 tokens of a prompt are identical across multiple requests, the KV cache for those tokens can be computed once and reused.

The challenge is that not all tokens are equally stable. The system prompt and skill summaries change rarely — they are set once at the beginning of a conversation and remain constant. These are PREFIX blocks. The loaded skills, dynamic context, and conversation history change every turn. These are SUFFIX blocks.

By separating these block types, the PromptCacheManager ensures that the stable PREFIX blocks are cached across turns, while only the volatile SUFFIX blocks are recomputed. This means that a typical agent call might only need to recompute 30% of its context, with the remaining 70% served from cache. The practical impact is significant: cache-friendly calls complete in half the time of cache-unfriendly calls.

The cache manager tracks prefix stability by hashing PREFIX blocks between turns. If the hash has not changed, the cached KV pairs are reused. If the hash has changed (which happens when skills are loaded or unloaded), the cache is invalidated and recomputed. This hash-based invalidation is both reliable and efficient — it guarantees correctness while adding negligible overhead.

## NOOA's Native Context Management

Beyond DeepBl4nder's custom context management, the NOOA framework provides its own context handling that operates at a lower level. NOOA's TruncationConfig defines a 64K context window with 8 preserved events and a 2K response reserve. When the total context exceeds this window, NOOA's TokenBudgetSummarizer compresses the conversation history by preserving the last 10 messages verbatim and summarizing older messages.

This native context management operates as a safety net. DeepBl4nder's custom pruning happens first, reducing the context to fit within per-element budgets. If the total still exceeds NOOA's window, the summarizer kicks in to compress the history. This layered approach means that agents always have access to the most relevant context within the model's capacity.

The optional MemorySkill extends this further by providing long-term memory across productions. When enabled, agents can recall information from previous runs — what worked, what did not, what the user preferred. This memory is stored separately from the per-production context and is loaded on demand, ensuring that it does not consume context budget unless it is relevant to the current task.

## Why This Matters

Context management is not just a technical optimization — it directly affects the quality of the output. An agent that has access to relevant context produces better results than an agent that is working blind. A StoryAgent that knows about the previous production's themes can create more coherent sequels. A BlenderAgent that has access to the full SceneSpec produces more accurate scripts. A QAAgent that sees the complete history of revisions can provide more targeted feedback.

By investing in sophisticated context management, DeepBl4nder ensures that every agent has the information it needs to do its job well, within the constraints of the model's context window. This is the difference between an AI system that produces generic output and one that produces thoughtful, context-aware results.
`

export default function ContextPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={chart1} title="Context Management Pipeline" />
      <MDXRenderer source={section2} />
    </>
  )
}
