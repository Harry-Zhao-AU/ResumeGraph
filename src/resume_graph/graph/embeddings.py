"""Embed skill nodes and create RELATED_TO edges based on cosine similarity.

Uses a local sentence-transformers model (no API needed).

Usage: python -m resume_graph.graph.embeddings
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from resume_graph.graph.store import get_graph_store, close_graph_store

# Small, fast model — good enough for skill name similarity
MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.65  # Only create edges above this cosine similarity


def get_all_skills() -> list[dict]:
    """Fetch all skill nodes from Neo4j."""
    store = get_graph_store()
    results = store.structured_query(
        "MATCH (s)-[:HAS_SKILL]->(skill) "
        "WITH DISTINCT skill.name AS name "
        "WHERE name IS NOT NULL "
        "RETURN name ORDER BY name"
    )
    return [r["name"] for r in results if r.get("name")]


def compute_embeddings(skills: list[str]) -> np.ndarray:
    """Compute embeddings for all skill names."""
    print(f"Loading model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Embedding {len(skills)} skills...")
    embeddings = model.encode(skills, show_progress_bar=True)
    return np.array(embeddings)


def compute_similarities(
    skills: list[str], embeddings: np.ndarray
) -> list[tuple[str, str, float]]:
    """Compute cosine similarity between all skill pairs, return those above threshold."""
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms

    # Cosine similarity matrix
    sim_matrix = normalized @ normalized.T

    pairs = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            sim = float(sim_matrix[i, j])
            if sim >= SIMILARITY_THRESHOLD:
                pairs.append((skills[i], skills[j], round(sim, 3)))

    # Sort by similarity descending
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


def create_related_edges(pairs: list[tuple[str, str, float]]) -> int:
    """Create RELATED_TO edges in Neo4j for similar skill pairs."""
    store = get_graph_store()

    # Clear existing computed RELATED_TO edges (keep LLM-extracted ones if any)
    # We'll use a property to mark our computed edges
    store.structured_query(
        "MATCH ()-[r:RELATED_TO]->() WHERE r.source = 'embedding' DELETE r"
    )

    created = 0
    for skill_a, skill_b, weight in pairs:
        store.structured_query(
            "MATCH (a {name: $a}), (b {name: $b}) "
            "WHERE a <> b "
            "MERGE (a)-[r:RELATED_TO {source: 'embedding'}]->(b) "
            "SET r.weight = $weight",
            param_map={"a": skill_a, "b": skill_b, "weight": weight},
        )
        created += 1

    return created


def main() -> None:
    print("=" * 60)
    print("Computing skill embeddings and creating RELATED_TO edges...")
    print("=" * 60)

    try:
        skills = get_all_skills()
        print(f"Found {len(skills)} unique skills")

        if len(skills) < 2:
            print("Not enough skills to compute similarities.")
            return

        embeddings = compute_embeddings(skills)
        pairs = compute_similarities(skills, embeddings)
        print(f"\nFound {len(pairs)} similar skill pairs (threshold: {SIMILARITY_THRESHOLD})")

        if pairs:
            print("\nTop 15 most similar pairs:")
            for a, b, sim in pairs[:15]:
                print(f"  {a} <-> {b}: {sim}")

        print("\nCreating RELATED_TO edges in Neo4j...")
        created = create_related_edges(pairs)
        print(f"Done! Created {created} RELATED_TO edges.")
    finally:
        close_graph_store()


if __name__ == "__main__":
    main()
