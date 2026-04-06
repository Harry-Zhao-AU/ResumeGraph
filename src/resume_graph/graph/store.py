"""Neo4jPropertyGraphStore singleton."""

from __future__ import annotations

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from resume_graph.config import settings

_store: Neo4jPropertyGraphStore | None = None


def get_graph_store() -> Neo4jPropertyGraphStore:
    """Get or create the Neo4j property graph store singleton."""
    global _store
    if _store is None:
        _store = Neo4jPropertyGraphStore(
            username=settings.neo4j_user,
            password=settings.neo4j_password,
            url=settings.neo4j_uri,
            database="neo4j",
        )
    return _store


def close_graph_store() -> None:
    """Close the Neo4j connection."""
    global _store
    if _store is not None:
        _store.close()
        _store = None
