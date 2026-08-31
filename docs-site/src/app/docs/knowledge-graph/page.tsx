import { MDXRenderer } from '@/components/MDXRenderer'
import { MermaidDiagram } from '@/components/diagrams/MermaidDiagram'

export const metadata = {
  title: 'Knowledge Graph - DeepBl4nder',
  description: 'How DeepBl4nder uses knowledge graphs and vector search for domain understanding.',
}

const section1 = `
# Knowledge Graph

## Why Knowledge Graphs Matter for AI

Language models are remarkably good at generating text, but they have a fundamental limitation: they do not remember what they have created. Each time an agent processes a request, it starts with a blank slate — it has no memory of the scenes it has designed, the scripts it has written, or the decisions it has made in previous productions. This is where the Knowledge Graph enters the picture.

The Knowledge Graph is a structured representation of everything the system knows about a production. It tracks scenes, shots, characters, assets, and the relationships between them. When the DirectorAgent creates a scene with two characters and three shots, the Knowledge Graph records not just the entities themselves but also how they relate to each other — which characters appear in which shots, which assets are used in which scenes, which decisions were made and why.

This structured memory serves two purposes. First, it enables agents to make informed decisions based on the full context of the production. A character designer can see what environment has already been created and design characters that fit that environment. A QA agent can compare a new shot against previous shots to ensure visual continuity. Second, it enables semantic search over the system's own domain knowledge, helping agents find the right types and patterns for the task at hand.

## The Graph Structure

The Knowledge Graph is stored as a JSON file — simple, portable, and human-readable. Each entity is a node with an ID, a label, and a set of properties. Each relationship is an edge connecting two nodes with a relation type. For example, a scene node might be connected to a shot node through a "contains" relation, and that shot node might be connected to a character node through a "features_character" relation.

This graph structure is intentionally simple. It does not use a graph database, a triple store, or any specialized infrastructure. The JSON file is loaded into memory at startup and saved back to disk after each modification. This simplicity means there is no external dependency, no server to manage, and no configuration to maintain. The graph is just a file that lives alongside your production data.

The simplicity also means that the graph is easy to inspect and debug. You can open the JSON file in any text editor and see exactly what the system knows about your production. There is no query language to learn, no schema to configure, and no indexing to manage. The graph is as transparent as possible, which is essential for a system that makes autonomous creative decisions.
`

const chart1 = `graph TB
    KG["KnowledgeGraphPlugin"] --> ENTITIES["Entity Store"]
    KG --> RELATIONS["Relation Store"]
    ENTITIES -->|"CameraSpec, LightingSpec..."| SVS["SchemaVectorStore"]
    SVS -->|"TF-IDF search"| QUERY["Agent Query"]
    QUERY -->|"relevant schemas"| AGENT["Agent Context"]
    RELATIONS -->|"dependencies, references"| AGENT`

const section2 = `
## SchemaVectorStore: Semantic Search Over Domain Types

The Knowledge Graph does more than track production entities. It also indexes the system's own domain types — the Python dataclasses that define CameraSpec, LightingSpec, CharacterSpec, and dozens of other domain objects. This indexing enables semantic search: you can ask "find me the types related to camera positioning" and get back CameraSpec, ShotSpec, and SceneSpec ranked by relevance.

The search uses TF-IDF (Term Frequency-Inverse Document Frequency) with bigram features. This is a classic information retrieval technique that works by computing a vector representation of each domain type's documentation and then measuring cosine similarity between the query and each type's vector. Types with higher similarity scores are returned first.

TF-IDF was chosen over neural embeddings for several practical reasons. First, it requires no external model — the embeddings are computed from the text itself using statistical methods. This means there is no neural network to load, no GPU memory to consume, and no inference time to wait for. Second, it is deterministic — the same query always produces the same results, which is important for debugging and reproducibility. Third, it is fast — the entire index fits in memory and searches complete in milliseconds.

The SchemaVectorStore is used by every agent through the \`BaseAgent._load_schema_context()\` method. When an agent needs to work with domain types — for example, when the DirectorAgent needs to know what fields are available in CameraSpec — it searches the vector store for relevant types and injects their compact representations into its context. This means agents always have access to the exact types they need, without cluttering their context with irrelevant definitions.

## How the Bootstrap Works

The domain schema bootstrap is the process that populates the Knowledge Graph with domain types at startup. It scans all dataclasses in the \`domain/\` module, extracts their names, fields, types, and docstrings, creates DomainClass nodes in the graph, and indexes them in the SchemaVectorStore.

This bootstrap happens once, at system startup, and the results are cached. The domain types are static — they do not change during a production — so there is no need to re-index them. The bootstrap process takes a few seconds, which is negligible compared to the minutes-long production runs.

The bootstrap also discovers the relationships between domain types. If CameraSpec references CharacterSpec through a field, the bootstrap creates an edge between the two nodes. These relationships enable agents to navigate the type hierarchy — starting from CameraSpec, an agent can discover that it relates to CharacterSpec, which relates to SceneSpec, which relates to the overall production.

## Why Not Use a Real Graph Database?

This is a question that comes up frequently, and the answer reveals something important about DeepBl4nder's design philosophy.

A real graph database — Neo4j, ArangoDB, Neptune — would provide more sophisticated query capabilities, better performance at scale, and more robust data management. But it would also add an external dependency, require configuration, consume additional resources, and increase the system's complexity.

DeepBl4nder's Knowledge Graph is not trying to be a general-purpose graph database. It is a specialized tool for a specific purpose: tracking production entities and enabling semantic search over domain types. For this purpose, a JSON file is sufficient. The graph typically contains a few hundred nodes and a few thousand edges — well within the performance envelope of an in-memory data structure.

More importantly, the simplicity of the JSON approach aligns with DeepBl4nder's local-first philosophy. There is no server to start, no database to configure, no credentials to manage. The graph is a file that lives on your hard drive, loads into memory at startup, and saves back to disk when modified. It is as simple and transparent as possible, which is exactly what a local-first system should be.

The trade-off is that the Knowledge Graph does not scale to millions of nodes. But for a production pipeline that typically generates a few dozen scenes and a few hundred shots per production, this is not a limitation. The graph is designed for the scale of the problem, not for theoretical maximum capacity.

## How Agents Use the Graph

Agents interact with the Knowledge Graph in two ways: through direct queries and through the SchemaVectorStore.

Direct queries are used when an agent needs to traverse the graph. The DirectorAgent might query for all shots in a scene to ensure continuity. The QAAgent might query for all assets used in a production to verify they exist. The AnimationAgent might query for all character movements to plan keyframes.

The SchemaVectorStore is used when an agent needs to find the right domain types for a task. The BlenderAgent searches for types related to "lighting" and discovers LightingSpec, LightType, and LightIntensity. The DirectorAgent searches for types related to "camera" and discovers CameraSpec, FocalLength, and CameraAngle. These searches happen automatically, without the agent needing to know the exact names or locations of the types.

This dual access pattern — direct queries for traversal, semantic search for discovery — gives agents the flexibility they need to work effectively with complex domain models. The Knowledge Graph is not just a data store — it is a knowledge base that helps agents understand the system's own architecture.
`

export default function KnowledgeGraphPage() {
  return (
    <>
      <MDXRenderer source={section1} />
      <MermaidDiagram chart={chart1} title="Knowledge Graph Schema" />
      <MDXRenderer source={section2} />
    </>
  )
}
