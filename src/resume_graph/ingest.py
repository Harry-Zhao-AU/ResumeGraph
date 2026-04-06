"""CLI: Read PDFs from data/resumes/, feed into LlamaIndex PropertyGraphIndex -> Neo4j.

Usage:
  python -m resume_graph.ingest           # ingest (appends to existing graph)
  python -m resume_graph.ingest --clean   # clear graph first, then ingest
"""

from __future__ import annotations

import sys
from pathlib import Path

from llama_index.core import Document
from llama_index.readers.file import PyMuPDFReader

from resume_graph.graph.index import build_index
from resume_graph.graph.store import get_graph_store, close_graph_store

RESUMES_DIR = Path("data/resumes")


def load_resume_documents() -> list[Document]:
    """Load all resume PDFs as LlamaIndex Documents."""
    pdf_paths = sorted(RESUMES_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDFs found in {RESUMES_DIR}/")
        return []

    print(f"Found {len(pdf_paths)} PDFs in {RESUMES_DIR}/")

    documents: list[Document] = []
    reader = PyMuPDFReader()

    for path in pdf_paths:
        try:
            docs = reader.load_data(file_path=path)
            # Merge multi-page docs into single document per resume
            if docs:
                full_text = "\n".join(d.text for d in docs if d.text)
                doc = Document(
                    text=full_text,
                    metadata={"source": path.name, "file_path": str(path)},
                )
                documents.append(doc)
                print(f"  Loaded: {path.name} ({len(full_text)} chars)")
        except Exception as e:
            print(f"  Error loading {path.name}: {e}")

    return documents


def clear_graph() -> None:
    """Delete all nodes and relationships from Neo4j."""
    store = get_graph_store()
    print("Clearing all nodes and relationships from Neo4j...")
    store.structured_query("MATCH (n) DETACH DELETE n")
    print("Graph cleared.")


def main() -> None:
    clean = "--clean" in sys.argv

    print("=" * 60)
    print("Ingesting resume PDFs into Neo4j via LlamaIndex...")
    print("=" * 60)

    if clean:
        clear_graph()

    documents = load_resume_documents()
    if not documents:
        return

    print(f"\nBuilding PropertyGraphIndex from {len(documents)} documents...")
    print("This will extract entities and relationships using Azure OpenAI...")
    print("(This may take a few minutes)\n")

    try:
        index = build_index(documents, show_progress=True)
        print(f"\nDone! Graph built from {len(documents)} resumes.")
        print("Check Neo4j Browser at http://localhost:7474")
        print("Try: MATCH (n) RETURN n LIMIT 50")
    finally:
        close_graph_store()


if __name__ == "__main__":
    main()
