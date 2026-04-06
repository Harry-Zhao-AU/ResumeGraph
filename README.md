# ResumeGraph

HR Skill Graph tool — generates fake resumes, extracts employee-skill relationships into Neo4j, and exposes graph queries via FastAPI and MCP server.

## Architecture

```
CLI: generate profiles -> generate PDFs -> ingest into Neo4j

                    +---------------------------+
                    |   FastAPI (port 3100)      |
                    |   GET /employees           |
                    |   POST /query              |
                    |         |                  |
                    |   LlamaIndex Retrievers    |
                    |         |                  |
                    |      Neo4j DB              |
                    +------------+--------------+
                                 | HTTP
                +----------------+----------------+
                |                |                 |
          MCP Server        NanoBotTS          curl/browser
         (stdio wrapper)   (HTTP tool)
```

## Tech Stack

- **Python 3.12+** with FastAPI, LlamaIndex, Pydantic
- **Neo4j 5** (Docker) — graph database
- **LlamaIndex** — PDF text extraction, LLM-based entity extraction, text-to-Cypher queries
- **Azure OpenAI** — generates fake profiles, extracts graph triplets, natural language queries
- **sentence-transformers** — local embeddings for semantic skill matching
- **MCP SDK** — stdio server for Claude Code/Desktop integration

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (or Podman) for Neo4j

### Setup

```bash
# Clone
git clone git@github.com:Harry-Zhao-AU/ResumeGraph.git
cd ResumeGraph

# Install dependencies
uv sync

# Copy env and fill in Azure OpenAI credentials
cp .env.example .env
# Edit .env with your Azure OpenAI endpoint, key, and deployment name

# Start Neo4j
docker-compose up -d
```

### Generate Data

```bash
# Step 1: Generate 30 fake employee profiles + PDF resumes
uv run python -m resume_graph.generate

# Step 2: Ingest PDFs into Neo4j (extracts entities via LLM)
uv run python -m resume_graph.ingest

# Step 3: Compute skill embeddings for semantic search
uv run python -m resume_graph.graph.embeddings
```

### Run the API

```bash
uv run python -m resume_graph.main
# API at http://localhost:3100
# Swagger docs at http://localhost:3100/docs
```

### Run the MCP Server

Requires the API server to be running.

```bash
uv run python -m resume_graph.mcp.server
```

## API Endpoints

### GET /employees

Search employees with optional filters:

```bash
# List all employees
curl http://localhost:3100/employees

# Filter by skill (semantic — also matches related skills)
curl http://localhost:3100/employees?skill=Python

# Filter by company
curl http://localhost:3100/employees?company=Canva

# Filter by city
curl http://localhost:3100/employees?city=Melbourne

# Find similar employees (by shared skills)
curl http://localhost:3100/employees?similar_to=Daniel+Chen

# Skill gap analysis
curl "http://localhost:3100/employees?name=Daniel+Chen&skill_gap_with=Oliver+Thompson"
```

### POST /query

Natural language graph query — LLM converts your question to Cypher:

```bash
curl -X POST http://localhost:3100/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Who knows both Python and Docker?"}'
```

## MCP Integration

### Claude Code / Claude Desktop

Add to your MCP settings:

```json
{
  "mcpServers": {
    "resume-graph": {
      "command": "uv",
      "args": ["run", "--directory", "C:/SideProject/ResumeGraph", "python", "-m", "resume_graph.mcp.server"]
    }
  }
}
```

Then ask Claude: "Find employees who know Kubernetes in Melbourne"

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_employees` | Structured search by skill, company, city, certification, etc. |
| `query_graph` | Natural language questions converted to Cypher |

## Graph Model

6 node types, 6 relationship types:

```
(:Employee) -[:HAS_SKILL]-> (:Skill)
(:Employee) -[:WORKED_AT]-> (:Company)
(:Employee) -[:STUDIED_AT]-> (:University)
(:Employee) -[:HAS_CERTIFICATION]-> (:Certification)
(:Employee) -[:LOCATED_IN]-> (:City)
(:Skill) -[:RELATED_TO]-> (:Skill)   (computed via embeddings)
```

## Neo4j Browser

Open http://localhost:7474 (login with credentials from your `.env`)

Useful queries:

```cypher
-- See the full graph (excluding document chunks)
MATCH (a)-[r]->(b) WHERE type(r) <> 'MENTIONS' RETURN a, r, b LIMIT 100

-- Employees with a specific skill
MATCH (e)-[:HAS_SKILL]->(s {name: 'Python'}) RETURN e, s

-- Similar employees (shared skills)
MATCH (a)-[:HAS_SKILL]->(s)<-[:HAS_SKILL]-(b)
WHERE a.name = 'Daniel Chen' AND a <> b
WITH b, COUNT(s) AS shared ORDER BY shared DESC LIMIT 5
RETURN b.name, shared

-- Skill clusters via RELATED_TO
MATCH (s1)-[:RELATED_TO]->(s2) RETURN s1, s2
```

## Re-ingesting Data

To regenerate from scratch:

```bash
uv run python -m resume_graph.generate                # regenerate profiles + PDFs
uv run python -m resume_graph.ingest --clean           # clear Neo4j + re-ingest
uv run python -m resume_graph.graph.embeddings         # recompute skill embeddings
```
