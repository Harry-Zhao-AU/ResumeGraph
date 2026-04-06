"""Retriever wrappers for querying the property graph."""

from __future__ import annotations

from llama_index.core.indices.property_graph import (
    TextToCypherRetriever,
    PGRetriever,
)

from resume_graph.graph.index import get_llm, get_existing_index
from resume_graph.graph.store import get_graph_store


def get_text_to_cypher_retriever() -> TextToCypherRetriever:
    """Get a retriever that converts natural language to Cypher queries."""
    graph_store = get_graph_store()
    return TextToCypherRetriever(
        graph_store=graph_store,
        llm=get_llm(),
        include_raw_response_as_metadata=True,
    )


def get_pg_retriever() -> PGRetriever:
    """Get the composite property graph retriever with text-to-cypher."""
    return PGRetriever(
        sub_retrievers=[get_text_to_cypher_retriever()],
    )


def query_with_cypher(cypher: str, params: dict | None = None) -> list[dict]:
    """Execute a raw Cypher query against the graph store."""
    graph_store = get_graph_store()
    result = graph_store.structured_query(cypher, param_map=params or {})
    return result


def query_natural_language(question: str) -> dict:
    """Query the graph using natural language (text-to-cypher).

    Returns dict with 'answer' and optionally 'cypher' keys.
    """
    retriever = get_text_to_cypher_retriever()
    nodes = retriever.retrieve(question)

    if not nodes:
        return {"answer": "No results found.", "cypher": None}

    # Combine node texts into answer
    answer_parts = []
    cypher = None
    for node in nodes:
        if node.text:
            answer_parts.append(node.text)
        # Extract generated Cypher from metadata if available
        if node.metadata and "query" in node.metadata:
            cypher = node.metadata["query"]

    return {
        "answer": "\n".join(answer_parts) if answer_parts else "No results found.",
        "cypher": cypher,
    }
