"""PropertyGraphIndex: build from documents and query helpers."""

from __future__ import annotations

from llama_index.core import Document
from llama_index.core.indices.property_graph import (
    PropertyGraphIndex,
    SimpleLLMPathExtractor,
)
from llama_index.llms.azure_openai import AzureOpenAI

from resume_graph.config import settings
from resume_graph.graph.store import get_graph_store

# Custom extraction prompt that encodes our schema into the LLM prompt directly.
# This avoids SchemaLLMPathExtractor's structured_predict which generates
# JSON schemas incompatible with newer Azure OpenAI models.
EXTRACT_PROMPT = """\
Extract knowledge graph triplets from the following resume text.

Entity types: Employee, Skill, Company, University, Certification, City
Relationship types and valid paths:
- Employee -HAS_SKILL-> Skill
- Employee -WORKED_AT-> Company
- Employee -STUDIED_AT-> University
- Employee -HAS_CERTIFICATION-> Certification
- Employee -LOCATED_IN-> City
- Skill -RELATED_TO-> Skill

For each triplet, output one line in this exact format:
(subject_entity_name, RELATIONSHIP_TYPE, object_entity_name)

Rules:
- Extract the person's full name as an Employee entity
- Extract each technical skill, language, framework, tool as a Skill entity
- Extract each company they worked at as a Company entity
- Extract their university as a University entity
- Extract certifications as Certification entities
- Extract their city/location as a City entity
- Use UPPERCASE for relationship types
- Extract up to {max_paths_per_chunk} triplets

Text:
{text}

Triplets:
"""


def _parse_triplets(response: str) -> list[tuple[str, str, str]]:
    """Parse triplet lines from LLM response."""
    triplets = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line.startswith("("):
            continue
        # Remove parentheses
        line = line.strip("()")
        parts = [p.strip().strip("'\"") for p in line.split(",", 2)]
        if len(parts) == 3:
            triplets.append((parts[0], parts[1], parts[2]))
    return triplets


def get_llm() -> AzureOpenAI:
    """Create the Azure OpenAI LLM for LlamaIndex."""
    return AzureOpenAI(
        engine=settings.azure_openai_deployment_name,
        model="gpt-4o",
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        temperature=0.0,
    )


def get_kg_extractor() -> SimpleLLMPathExtractor:
    """Create the knowledge graph extractor with our resume schema prompt."""
    return SimpleLLMPathExtractor(
        llm=get_llm(),
        extract_prompt=EXTRACT_PROMPT,
        parse_fn=_parse_triplets,
        max_paths_per_chunk=20,
        num_workers=2,
    )


def build_index(documents: list[Document], show_progress: bool = True) -> PropertyGraphIndex:
    """Build a PropertyGraphIndex from documents, extracting entities into Neo4j."""
    graph_store = get_graph_store()
    kg_extractor = get_kg_extractor()

    index = PropertyGraphIndex.from_documents(
        documents=documents,
        property_graph_store=graph_store,
        kg_extractors=[kg_extractor],
        show_progress=show_progress,
        embed_kg_nodes=False,
    )
    return index


def get_existing_index() -> PropertyGraphIndex:
    """Get a PropertyGraphIndex connected to the existing Neo4j graph (no ingestion)."""
    graph_store = get_graph_store()
    return PropertyGraphIndex.from_existing(
        property_graph_store=graph_store,
        embed_kg_nodes=False,
    )
