# ResumeGraph — System Flow

## 1. Data Generation Pipeline

```mermaid
flowchart TD
    A[Azure OpenAI] -->|"Generate 30 profiles<br/>in batches of 5-6"| B[JSON Profiles]
    B -->|"data/profiles/*.json"| C[30 JSON Files]
    
    C -->|"For each profile"| D[Azure OpenAI]
    D -->|"Write resume markdown<br/>4 writing styles"| E[Markdown Text]
    
    E -->|"reportlab renders PDF<br/>4 visual styles"| F[PDF Resumes]
    F -->|"data/resumes/*.pdf"| G[30 PDF Files]

    style A fill:#4a90d9,color:#fff
    style D fill:#4a90d9,color:#fff
    style G fill:#2ecc71,color:#fff
```

**CLI:** `uv run python -m resume_graph.generate`

---

## 2. Ingestion Pipeline (PDF to Graph)

```mermaid
flowchart TD
    A[30 PDF Files<br/>data/resumes/*.pdf] -->|"PyMuPDFReader<br/>(no LLM)"| B[Raw Text<br/>per resume]
    
    B -->|"SimpleLLMPathExtractor<br/>(uses Azure OpenAI)"| C{LLM reads text<br/>extracts triplets}
    
    C -->|"(Priya Nair, HAS_SKILL, Java)"| D[Triplets]
    C -->|"(Priya Nair, WORKED_AT, Canva)"| D
    C -->|"(Priya Nair, LOCATED_IN, Sydney)"| D
    C -->|"(Priya Nair, STUDIED_AT, UNSW)"| D
    
    D -->|"PropertyGraphIndex<br/>merges duplicates"| E[(Neo4j<br/>302 nodes<br/>1,270 edges)]

    style A fill:#e74c3c,color:#fff
    style C fill:#4a90d9,color:#fff
    style E fill:#2ecc71,color:#fff
```

**CLI:** `uv run python -m resume_graph.ingest`

---

## 3. Embedding Pipeline (Post-processing)

```mermaid
flowchart TD
    A[(Neo4j<br/>186 skill nodes)] -->|"Read all<br/>skill names"| B[sentence-transformers<br/>all-MiniLM-L6-v2<br/>LOCAL model]
    
    B -->|"Embed each skill<br/>to 384-dim vector"| C["Vectors<br/>'Docker' → [0.45, 0.88, ...]<br/>'Kubernetes' → [0.43, 0.91, ...]"]
    
    C -->|"Cosine similarity<br/>between all pairs"| D{"Similarity<br/>above 0.65?"}
    
    D -->|Yes| E["Create RELATED_TO edge<br/>(Docker)→(Kubernetes) weight:0.95"]
    D -->|No| F[Skip]
    
    E -->|"94 new edges"| G[(Neo4j<br/>+ RELATED_TO edges)]

    style A fill:#2ecc71,color:#fff
    style B fill:#9b59b6,color:#fff
    style G fill:#2ecc71,color:#fff
```

**CLI:** `uv run python -m resume_graph.graph.embeddings`

---

## 4. Query Flow — API Server

```mermaid
flowchart TD
    subgraph Clients
        A[curl / browser]
        B[NanoBotTS]
        C[Claude Code]
    end

    subgraph MCP["MCP Server (stdio)"]
        D[search_employees tool]
        E[query_graph tool]
    end

    subgraph API["FastAPI :3100"]
        F["GET /employees<br/>?skill=Python&city=Melbourne"]
        G["POST /query<br/>{question: '...'}"]
    end

    subgraph Backend
        H[Cypher Query Builder<br/>+ semantic skill matching]
        I[TextToCypherRetriever<br/>LLM generates Cypher]
        J[(Neo4j)]
    end

    A --> F
    A --> G
    B --> F
    B --> G
    C -->|stdio| D
    C -->|stdio| E
    D -->|HTTP| F
    E -->|HTTP| G
    F --> H
    G --> I
    H --> J
    I -->|"LLM → Cypher"| J

    style C fill:#4a90d9,color:#fff
    style J fill:#2ecc71,color:#fff
```

---

## 5. GET /employees — Structured Query Flow

```mermaid
flowchart TD
    A["GET /employees?skill=monitoring"] --> B{Semantic<br/>skill lookup}
    
    B -->|"_get_related_skills()"| C["Find RELATED_TO edges<br/>monitoring → monitoring and alerting"]
    C --> D["skill_names = ['monitoring',<br/>'monitoring and alerting']"]
    
    D --> E["Build Cypher<br/>MATCH (e)-[:HAS_SKILL]->(s)<br/>WHERE s.name IN $skill_names"]
    
    E --> F[(Neo4j)]
    F --> G["2 employees:<br/>Mei Lin Tan (exact)<br/>Aisha Rahman (via RELATED_TO)"]

    style A fill:#e67e22,color:#fff
    style F fill:#2ecc71,color:#fff
```

---

## 6. POST /query — Natural Language Flow

```mermaid
flowchart TD
    A["POST /query<br/>{question: 'Who knows<br/>both Python and Docker?'}"] --> B[TextToCypherRetriever]
    
    B --> C["Azure OpenAI reads:<br/>- Your question<br/>- Neo4j schema (node labels, relationships)"]
    
    C --> D["LLM generates Cypher:<br/>MATCH (e)-[:HAS_SKILL]->(s1 {name:'Python'})<br/>MATCH (e)-[:HAS_SKILL]->(s2 {name:'Docker'})<br/>RETURN e.name"]
    
    D --> E[(Neo4j<br/>executes Cypher)]
    E --> F["Results:<br/>Aarav Patel, Mei Lin Tan, ..."]

    style A fill:#e67e22,color:#fff
    style C fill:#4a90d9,color:#fff
    style E fill:#2ecc71,color:#fff
```

---

## 7. Graph Model

```mermaid
graph LR
    E((Employee)) -->|HAS_SKILL| S((Skill))
    E -->|WORKED_AT| C((Company))
    E -->|STUDIED_AT| U((University))
    E -->|HAS_CERTIFICATION| Cert((Certification))
    E -->|LOCATED_IN| City((City))
    S -->|RELATED_TO| S2((Skill))

    style E fill:#3498db,color:#fff
    style S fill:#e74c3c,color:#fff
    style C fill:#2ecc71,color:#fff
    style U fill:#9b59b6,color:#fff
    style Cert fill:#f39c12,color:#fff
    style City fill:#1abc9c,color:#fff
    style S2 fill:#e74c3c,color:#fff
```

---

## 8. Full System Overview

```mermaid
flowchart TB
    subgraph Generate["Phase 2: Generate"]
        G1[Azure OpenAI] --> G2[30 JSON Profiles]
        G2 --> G3[30 PDF Resumes]
    end

    subgraph Ingest["Phase 3: Ingest"]
        I1[PyMuPDFReader] --> I2[SimpleLLMPathExtractor]
        I2 --> I3[PropertyGraphIndex]
    end

    subgraph Embed["Phase 7: Embed"]
        E1[sentence-transformers] --> E2[RELATED_TO edges]
    end

    subgraph Serve["Phase 4+5: Serve"]
        S1["FastAPI :3100"]
        S2["MCP Server (stdio)"]
        S2 -->|HTTP| S1
    end

    subgraph Query["Consumers"]
        Q1[curl / browser]
        Q2[NanoBotTS]
        Q3[Claude Code]
    end

    G3 --> I1
    I3 --> DB[(Neo4j)]
    E2 --> DB
    DB --> S1
    Q1 --> S1
    Q2 --> S1
    Q3 -->|stdio| S2

    style DB fill:#2ecc71,color:#fff
    style G1 fill:#4a90d9,color:#fff
    style I2 fill:#4a90d9,color:#fff
    style E1 fill:#9b59b6,color:#fff
```
