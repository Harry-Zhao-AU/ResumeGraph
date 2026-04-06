# ResumeGraph — HR Skill Graph Tool (Python + Neo4j + LlamaIndex)

## Context

Build an HR skill graph tool that generates realistic fake employee resumes via Azure OpenAI, uses LlamaIndex's `PropertyGraphIndex` + `Neo4jPropertyGraphStore` to extract entities/relationships and store them in Neo4j, then exposes graph queries via REST API and MCP server for NanoBotTS to consume. No real resume management — just LLM-generated fake data.

**GitHub account:** `Harry-Zhao-AU`
**Project location:** `C:\SideProject\ResumeGraph`

---

## Tech Stack

| Layer | Package | Why |
|-------|---------|-----|
| Runtime | **Python 3.12+** | Best ecosystem for LlamaIndex + NLP |
| Graph RAG | **LlamaIndex** (`llama-index-core`, `llama-index-graph-stores-neo4j`) | PropertyGraphIndex handles entity extraction, graph storage, and graph RAG queries |
| LLM Integration | `llama-index-llms-azure-openai` | Azure OpenAI provider for LlamaIndex |
| Embeddings | `llama-index-embeddings-azure-openai` | For embedding-based retrieval (optional) |
| Database | **Neo4j 5 Community** (Docker) | Graph-native skill relationships |
| API | **FastAPI** + uvicorn | Async, auto OpenAPI docs |
| MCP Server | `mcp` (Python MCP SDK) | Official SDK, stdio transport |
| Validation | `pydantic` v2 | Comes with FastAPI + LlamaIndex |
| Config | `pydantic-settings` | Env loading with type safety |
| PDF Generation | `reportlab` | Python-native PDF creation from structured data |
| Dev | `pytest`, `ruff`, `uv` | Fast tooling |

---

## Architecture

```
CLI: generate profiles → generate PDFs → ingest into Neo4j

                    ┌──────────────────────────┐
                    │   FastAPI (port 3100)     │
                    │   GET /employees          │
                    │   POST /query             │
                    │         │                 │
                    │   LlamaIndex Retrievers   │
                    │         │                 │
                    │      Neo4j DB             │
                    └──────────┬───────────────┘
                               │ HTTP
              ┌────────────────┼────────────────┐
              │                │                 │
        MCP Server        NanoBotTS          curl/browser
       (stdio wrapper)   (HTTP tool)
```

API server = single backend with all logic. MCP server = thin stdio adapter that calls the API.

---

## How LlamaIndex Fits

LlamaIndex handles two things in this project:

### 1. Ingestion: PDF text -> graph entities (SimpleLLMPathExtractor)
- `PyMuPDFReader` extracts raw text from resume PDFs (no LLM)
- `SimpleLLMPathExtractor` sends the text to Azure OpenAI with a custom prompt
- The LLM reads the resume and extracts structured triplets: `(Priya Nair, HAS_SKILL, Java)`
- `PropertyGraphIndex` stores these triplets as nodes + edges in Neo4j via `Neo4jPropertyGraphStore`
- Duplicate entities (e.g. "Docker" from 18 resumes) are automatically merged into one node

### 2. Querying: Natural language -> Cypher (TextToCypherRetriever)
- `TextToCypherRetriever` takes a question like "Who knows Kubernetes in Melbourne?"
- It sends the question + Neo4j schema to the LLM
- The LLM generates a Cypher query: `MATCH (e)-[:HAS_SKILL]->(s {name: 'Kubernetes'}), (e)-[:LOCATED_IN]->(c {name: 'Melbourne'}) RETURN e.name`
- LlamaIndex executes the Cypher and returns results
- Also supports raw Cypher via `graph_store.structured_query()` for the `/employees` endpoint

---

## Graph Schema (for SchemaLLMPathExtractor)

```python
entities = [
    EntityType("Employee", properties=["name", "email", "title", "department", "years_experience"]),
    EntityType("Skill", properties=["name", "category"]),
    EntityType("Company", properties=["name"]),
    EntityType("University", properties=["name"]),
    EntityType("Certification", properties=["name"]),
    EntityType("City", properties=["name", "state"]),
]

relations = [
    RelationType("HAS_SKILL", properties=["level", "years"]),
    RelationType("WORKED_AT", properties=["role", "start_year", "end_year"]),
    RelationType("STUDIED_AT", properties=["degree", "field"]),
    RelationType("HAS_CERTIFICATION"),
    RelationType("LOCATED_IN"),
    RelationType("RELATED_TO", properties=["weight"]),
]

schema = GraphSchema(
    entities=entities,
    relations=relations,
    possible_paths=[
        ("Employee", "HAS_SKILL", "Skill"),
        ("Employee", "WORKED_AT", "Company"),
        ("Employee", "STUDIED_AT", "University"),
        ("Employee", "HAS_CERTIFICATION", "Certification"),
        ("Employee", "LOCATED_IN", "City"),
        ("Skill", "RELATED_TO", "Skill"),
    ],
)
```

### In Neo4j this creates:
```
(:Employee {name, email, title, department, years_experience})
  -[:HAS_SKILL {level, years}]->(:Skill {name, category})
  -[:WORKED_AT {role, start_year, end_year}]->(:Company {name})
  -[:STUDIED_AT {degree, field}]->(:University {name})
  -[:HAS_CERTIFICATION]->(:Certification {name})
  -[:LOCATED_IN]->(:City {name, state})

(:Skill)-[:RELATED_TO {weight}]->(:Skill)
```

6 node types, 6 relationship types. Graph is densely connected through multiple dimensions — shared companies, universities, certifications, and locations create rich traversal paths beyond just skills.

---

## Docker Compose

```yaml
services:
  neo4j:
    image: neo4j:5-community
    container_name: resumegraph-neo4j
    ports:
      - "7474:7474"   # Browser UI
      - "7687:7687"   # Bolt protocol
    environment:
      NEO4J_AUTH: neo4j/<NEO4J_PASSWORD>
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
volumes:
  neo4j_data:
```

---

## Project Structure

```
C:\SideProject\ResumeGraph\
  pyproject.toml
  docker-compose.yml
  .env.example
  .gitignore
  data/
    profiles/                     # Generated JSON profiles (30 files)
    resumes/                      # Generated PDF resumes (30 files)
  src/
    resume_graph/
      __init__.py
      config.py                   # pydantic-settings: Neo4j + Azure OpenAI env vars
      models.py                   # Pydantic models: Profile, Skill, WorkExperience, etc.
      generate/
        __init__.py
        profiles.py               # Step 1: LLM generates 30 structured JSON profiles
        resumes.py                # Step 2: Convert profiles -> varied markdown -> PDF
        pdf_builder.py            # reportlab PDF rendering (varied layouts/styles)
      graph/
        __init__.py
        store.py                  # Neo4jPropertyGraphStore setup
        schema.py                 # Entity/relation schema for extraction
        index.py                  # PropertyGraphIndex: build + query helpers
        retrievers.py             # CypherRetriever + TextToCypherRetriever wrappers
      ingest.py                   # CLI: read PDFs from data/resumes/, feed into LlamaIndex -> Neo4j
      api/
        __init__.py
        app.py                    # FastAPI app: 2 endpoints (/employees, /query)
      mcp/
        __init__.py
        server.py                 # MCP stdio server -- thin wrapper, calls API over HTTP
      main.py                     # Entry: starts FastAPI on port 3100
  tests/
    test_graph.py
    test_generate.py
    test_api.py
```

---

## Resume Generation Pipeline (2 steps)

### Step 1: Generate Profiles (`generate/profiles.py`)

Call Azure OpenAI to generate 30 structured JSON profiles. Generate in batches of 5-6 to keep quality high and ensure skill overlap between profiles.

```python
class Profile(BaseModel):
    name: str                          # diverse backgrounds
    email: str
    location: str                      # Australian cities
    years_experience: int              # 2-20
    current_role: str                  # junior/mid/senior/staff/principal
    title: str                         # e.g. "Senior Backend Engineer"
    department: str
    companies: list[Company]           # 2-3 previous employers
    skills: list[SkillEntry]           # 5-10 skills with category + level
    certifications: list[str]          # 0-2, optional
    education: Education

class SkillEntry(BaseModel):
    name: str                          # e.g. "Kubernetes"
    category: str                      # language/framework/database/cloud/devops/soft-skill/methodology
    level: str                         # beginner/intermediate/advanced/expert
    years: int
```

**Skill archetype distribution** (ensures graph connectivity):
- ~6 backend-heavy: Java, Spring Boot, Kafka, PostgreSQL, Redis, gRPC
- ~6 cloud/infra: AWS, Terraform, Kubernetes, Docker, CloudFormation, Lambda
- ~6 full-stack: React, TypeScript, Node.js, GraphQL, Next.js, CSS
- ~5 data/ML: Python, PyTorch, Spark, Airflow, Pandas, SQL
- ~4 DevOps: GitHub Actions, ArgoCD, Helm, Jenkins, Ansible
- ~3 mobile/other: Swift, Kotlin, Flutter, React Native

**Overlapping skills** are critical — e.g. Python appears in backend, data/ML, and DevOps profiles. Docker/Kubernetes appear in cloud and DevOps. TypeScript appears in full-stack and backend. This creates a densely connected graph.

Output: `data/profiles/*.json` (30 files)

### Step 2: Generate Resume PDFs (`generate/resumes.py` + `generate/pdf_builder.py`)

For each JSON profile, generate a resume in two sub-steps:

**2a. Profile -> Markdown resume text** (via Azure OpenAI)
```python
async def profile_to_resume_markdown(profile: Profile) -> str:
    """LLM generates a natural-language resume from structured profile."""
    prompt = f"""Write a realistic resume for this person. Vary the format and tone.
    Include: professional summary (2-3 sentences), work experience (2-3 roles
    with bullet points), skills section, education, certifications.
    
    Profile: {profile.model_dump_json()}
    
    Don't use the exact same format every time. Some resumes should be:
    - Concise and bullet-heavy
    - More narrative/paragraph style
    - Technical with project highlights
    - Traditional chronological format"""
```

**2b. Markdown -> PDF** (via `reportlab`)
```python
def render_pdf(markdown_text: str, output_path: Path, style: str = "random") -> None:
    """Convert resume markdown to PDF with varied visual styles."""
    # 3-4 layout templates to vary appearance:
    # - "clean": minimal, lots of whitespace
    # - "compact": dense, two-column skills
    # - "modern": colored headers, sidebar
    # - "traditional": Times New Roman, conservative
```

Output: `data/resumes/*.pdf` (30 files, varied styles)

### Ingestion into Neo4j (`ingest.py`)

The ingestion pipeline has two stages — one is plain text extraction, the other uses LLM:

```
PDF file
  -> Stage 1: PyMuPDFReader (NO LLM — just extracts raw text from PDF)
  -> Raw text: "Priya Nair, Senior Backend Engineer at Canva.
                Skills: Java, Spring Boot, Kafka..."

  -> Stage 2: SimpleLLMPathExtractor (USES LLM to understand the text)
  -> Graph triplets:
       (Priya Nair, HAS_SKILL, Java)
       (Priya Nair, HAS_SKILL, Spring Boot)
       (Priya Nair, WORKED_AT, Canva)
       (Priya Nair, LOCATED_IN, Sydney)

  -> Stage 3: Neo4jPropertyGraphStore (stores triplets as nodes + edges)
```

**Stage 1 — PDF to text** (`PyMuPDFReader`): No LLM involved. Just reads the PDF bytes and
extracts the text content. Each PDF becomes a LlamaIndex `Document`.

**Stage 2 — Text to graph triplets** (`SimpleLLMPathExtractor`): This is where the LLM
comes in. It reads the resume text and *understands* who the person is, what skills they
have, where they worked, etc. It outputs structured triplets like
`(entity, RELATIONSHIP, entity)`. A custom prompt constrains extraction to our 6 entity
types and 6 relationship types.

**Stage 3 — Triplets to Neo4j** (`PropertyGraphIndex`): Takes the triplets and creates/merges
nodes and edges in Neo4j. Duplicate entities (e.g. "Docker" from multiple resumes) are
merged into a single node.

**Why SimpleLLMPathExtractor instead of SchemaLLMPathExtractor?**
`SchemaLLMPathExtractor` uses `response_format` with a JSON schema for structured output,
but LlamaIndex generates a schema that newer Azure OpenAI models (like gpt-5.4-mini) reject
because it's missing `additionalProperties: false`. `SimpleLLMPathExtractor` avoids this by
using plain text prompts — the LLM returns triplets as text lines, which we parse. The
tradeoff: entity names and relationships are extracted, but not entity properties (like skill
level or years). Good enough for graph connectivity.

---

## LlamaIndex Pipeline (`graph/index.py`)

```python
from llama_index.core.indices.property_graph import PropertyGraphIndex, SimpleLLMPathExtractor
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.readers.file import PyMuPDFReader
from llama_index.llms.azure_openai import AzureOpenAI

# 1. Read PDFs into Documents (no LLM)
reader = PyMuPDFReader()
documents = [reader.load_data(path) for path in pdf_paths]

# 2. Setup Neo4j store
graph_store = Neo4jPropertyGraphStore(
    url="bolt://localhost:7687",
    username="neo4j",
    password="<NEO4J_PASSWORD>",
)

# 3. Setup LLM extractor with custom prompt for our entity/relation types
kg_extractor = SimpleLLMPathExtractor(
    llm=AzureOpenAI(engine="gpt-5.4-mini", ...),
    extract_prompt=EXTRACT_PROMPT,  # constrains to Employee, Skill, Company, etc.
    parse_fn=_parse_triplets,       # parses "(entity, REL, entity)" lines
    max_paths_per_chunk=20,
)

# 4. Build index — runs the extraction + stores in Neo4j
index = PropertyGraphIndex.from_documents(
    documents=documents,
    property_graph_store=graph_store,
    kg_extractors=[kg_extractor],
)

# 5. Query (two modes)
# Natural language: LLM generates Cypher from question
retriever = TextToCypherRetriever(graph_store=graph_store, llm=llm)
# Raw Cypher: direct structured query
result = graph_store.structured_query("MATCH (e)-[:HAS_SKILL]->(s) ...")
```

---

## CLI Commands

```bash
# Generate 30 JSON profiles + PDF resumes
python -m resume_graph.generate

# Ingest PDFs into Neo4j via LlamaIndex
python -m resume_graph.ingest

# Start API server (must be running for everything to work)
python -m resume_graph.main

# Start MCP server (thin stdio wrapper -- calls the API over HTTP)
python -m resume_graph.mcp.server
```

---

## API Endpoints (2 only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/employees` | List/search employees. Query params: `?skill=`, `?name=`, `?department=`, `?company=`, `?certification=`, `?city=`, `?similar_to=`, `?skill_gap_with=` |
| POST | `/query` | Natural language graph query via LlamaIndex TextToCypherRetriever. Body: `{"question": "..."}` |

The `/employees` endpoint handles all structured queries via query params:
- `/employees` — list all
- `/employees?skill=python` — filter by skill
- `/employees?name=John` — search by name
- `/employees?company=Atlassian` — filter by company
- `/employees?certification=AWS` — filter by certification
- `/employees?city=Melbourne` — filter by location
- `/employees?similar_to=John+Smith` — find similar employees
- `/employees?skill_gap_with=Jane+Doe&name=John+Smith` — skill gap analysis

The `/query` endpoint handles everything else — any natural language question the LLM can turn into Cypher.

---

## MCP Server (thin wrapper over API)

The MCP server is a **stdio adapter** that calls the FastAPI server over HTTP. It does NOT contain business logic — just translates MCP tool calls into `GET /employees` and `POST /query` requests.

```
Claude Code / Claude Desktop
  -> MCP server (stdio, JSON-RPC)
    -> HTTP requests to FastAPI (localhost:3100)
      -> LlamaIndex + Neo4j
```

### MCP Tools (2 tools, 1:1 with API)

1. **`search_employees`** — Calls `GET /employees?...`. Params: `skill`, `name`, `department`, `company`, `certification`, `city`, `similar_to`, `skill_gap_with`. Returns matching employees with their full graph context.

2. **`query_graph`** — Calls `POST /query`. Accepts any natural language question (e.g. "AWS-certified engineers in Melbourne", "ex-Atlassian employees who know Kubernetes"). LlamaIndex generates + executes Cypher against the full 6-node graph.

---

## NanoBotTS Integration

Create `C:\NanoBotTS\src\tools\resume-graph.ts` — a single tool calling ResumeGraph FastAPI via HTTP:

```typescript
// Implements NanoBotTS Tool interface from src/tools/base.ts
name: "resume_graph"
description: "Query the HR skill graph. Actions: search (structured employee lookup), query (natural language)"
parameters: {
  action: "search" | "query",
  // For "search": skill, name, department, company, certification, city, similar_to, skill_gap_with
  // For "query": question (free-text, e.g. "AWS-certified engineers in Sydney")
}
execute(): fetch(`http://localhost:3100/...`) -> formatted text
```

Register in `C:\NanoBotTS\src\index.ts`.

---

## Implementation Phases

### Phase 1: Foundation
- `pyproject.toml` with deps: `llama-index-core`, `llama-index-graph-stores-neo4j`, `llama-index-llms-azure-openai`, `fastapi`, `uvicorn`, `mcp`, `pydantic-settings`, `reportlab`
- `.gitignore`, `.env.example`, `docker-compose.yml`
- `config.py` — pydantic-settings (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, AZURE_OPENAI_*)
- `models.py` — Pydantic models: Profile, SkillEntry, Company, Education
- Verify: `docker compose up -d`, connect to Neo4j

### Phase 2: Resume Generation (profiles -> PDFs)
- `generate/profiles.py` — Azure OpenAI generates 30 structured JSON profiles (batches of 5-6)
  - Ensure skill archetype distribution and overlap
  - Output: `data/profiles/*.json`
- `generate/resumes.py` — For each profile, LLM generates varied markdown resume text
- `generate/pdf_builder.py` — reportlab renders markdown -> PDF with 3-4 visual styles
  - Output: `data/resumes/*.pdf`
- Verify: 30 PDFs in `data/resumes/`, visually varied, skills realistic per role

### Phase 3: LlamaIndex Graph Pipeline + Ingest CLI
- `graph/store.py` — Neo4jPropertyGraphStore singleton
- `graph/schema.py` — Entity/relation schema for extraction
- `graph/index.py` — PropertyGraphIndex with SchemaLLMPathExtractor
- `graph/retrievers.py` — Cypher + TextToCypher retriever wrappers
- `ingest.py` — CLI command: reads PDFs from `data/resumes/`, feeds into PropertyGraphIndex -> Neo4j
- Verify: `python -m resume_graph.ingest`, check Neo4j Browser, see Employee/Skill nodes

### Phase 4: REST API (2 endpoints)
- `api/app.py` — FastAPI with `/employees` (structured queries) and `/query` (natural language)
- `main.py` — uvicorn on port 3100
- Verify: `curl http://localhost:3100/employees?skill=python`, `POST /query`

### Phase 5: MCP Server (thin wrapper over API)
- `mcp/server.py` — stdio server with 2 tools that call `GET /employees` and `POST /query` over HTTP
- Requires API server to be running
- Entry: `python -m resume_graph.mcp.server`
- Verify: start API first, then test MCP with MCP Inspector

### Phase 6: NanoBotTS Integration
- `C:\NanoBotTS\src\tools\resume-graph.ts`
- Register in `C:\NanoBotTS\src\index.ts`
- End-to-end test

### Phase 7: Polish (optional)
- Embeddings for semantic skill matching
- `RELATED_TO` edges via LlamaIndex's relationship extraction
- pytest tests
- README

---

## Verification

1. `docker compose up -d` — Neo4j at http://localhost:7474
2. `python -m resume_graph.generate` — generates 30 JSON profiles + 30 PDFs
3. `python -m resume_graph.ingest` — reads PDFs, extracts entities via LlamaIndex -> Neo4j
4. Neo4j Browser: `MATCH (n) RETURN n LIMIT 50` — shows Employee/Skill/Company/University graph
5. `python -m resume_graph.main` — FastAPI at http://localhost:3100
6. `curl http://localhost:3100/docs` — OpenAPI docs
7. `curl http://localhost:3100/employees?skill=python` — structured query
8. `curl -X POST http://localhost:3100/query -d '{"question": "Who knows the most programming languages?"}'` — natural language graph RAG
9. `python -m resume_graph.mcp.server` — test with MCP Inspector
10. NanoBotTS: "find employees who know Kubernetes" -> triggers `resume_graph` tool
