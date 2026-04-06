# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Start Neo4j (requires Docker/Podman — use docker-compose not docker compose)
docker-compose up -d

# Generate fake employee data (30 profiles + 30 PDF resumes)
uv run python -m resume_graph.generate

# Ingest PDFs into Neo4j graph (uses Azure OpenAI for entity extraction)
uv run python -m resume_graph.ingest          # append to graph
uv run python -m resume_graph.ingest --clean   # clear graph first

# Compute skill embeddings and create RELATED_TO edges
uv run python -m resume_graph.graph.embeddings

# Start API server (port 3100)
uv run python -m resume_graph.main

# Start MCP server (stdio — requires API server running)
uv run python -m resume_graph.mcp.server

# Lint
uv run ruff check src/

# Run tests
uv run pytest
uv run pytest tests/test_api.py -k "test_name"
```

## Architecture

Three-stage pipeline, all sharing the same Neo4j graph:

**Stage 1 — Generate** (`generate/`): Azure OpenAI creates 30 structured JSON profiles in batches by skill archetype (backend, cloud, fullstack, data/ML, devops, mobile), converts each to markdown resume text, renders to PDF via reportlab with 4 visual styles.

**Stage 2 — Ingest** (`ingest.py` + `graph/`): PyMuPDFReader extracts text from PDFs (no LLM). SimpleLLMPathExtractor sends text to Azure OpenAI with a custom prompt that constrains extraction to 6 entity types (Employee, Skill, Company, University, Certification, City) and 6 relationship types. PropertyGraphIndex stores triplets in Neo4j. A separate embeddings step (`graph/embeddings.py`) uses a local sentence-transformers model to create RELATED_TO edges between semantically similar skills.

**Stage 3 — Serve** (`api/` + `mcp/`): FastAPI exposes 2 endpoints: `GET /employees` (structured Cypher queries with semantic skill matching via RELATED_TO) and `POST /query` (natural language → Cypher via TextToCypherRetriever). MCP server is a thin stdio wrapper that calls the API over HTTP with httpx.

## Key Design Decisions

- **SimpleLLMPathExtractor over SchemaLLMPathExtractor**: The schema extractor uses `response_format` JSON schemas that newer Azure OpenAI models reject (missing `additionalProperties: false`). The simple extractor uses plain text prompts instead.
- **Local embeddings** (sentence-transformers `all-MiniLM-L6-v2`): No Azure embedding deployment needed. Runs locally, computes cosine similarity between skill names, creates RELATED_TO edges above 0.65 threshold.
- **MCP server wraps API**: MCP server makes HTTP calls to FastAPI, not direct Neo4j access. API must be running for MCP to work.
- **Semantic skill search**: `GET /employees?skill=X` first queries RELATED_TO edges to expand the skill list, then uses `WHERE s.name IN $skill_names` instead of exact match.

## Environment

Requires `.env` with: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`. See `.env.example` for defaults.
