"""MCP stdio server — thin wrapper that calls the FastAPI over HTTP.

Usage: python -m resume_graph.mcp.server
Requires the API server to be running on localhost:3100.
"""

from __future__ import annotations

import httpx
from mcp.server.fastmcp import FastMCP

from resume_graph.config import settings

mcp = FastMCP(
    name="resume-graph",
    instructions=(
        "HR Skill Graph tool. Query employee skills, find similar employees, "
        "analyze skill gaps, and ask natural language questions about the workforce. "
        "The API server must be running on localhost:3100."
    ),
)

API_BASE = f"http://{settings.api_host}:{settings.api_port}"
if settings.api_host == "0.0.0.0":
    API_BASE = f"http://127.0.0.1:{settings.api_port}"


@mcp.tool()
def search_employees(
    skill: str | None = None,
    name: str | None = None,
    department: str | None = None,
    company: str | None = None,
    certification: str | None = None,
    city: str | None = None,
    similar_to: str | None = None,
    skill_gap_with: str | None = None,
) -> str:
    """Search employees in the HR skill graph.

    Filter by skill, name, department, company, certification, or city.
    Use similar_to to find employees with overlapping skills.
    Use skill_gap_with + name to see what skills one employee lacks vs another.

    Examples:
    - skill="Python" → employees who know Python
    - company="Canva" → employees who worked at Canva
    - similar_to="Daniel Chen" → employees with similar skills
    - name="Daniel Chen", skill_gap_with="Oliver Thompson" → skills Daniel lacks
    """
    params = {}
    if skill:
        params["skill"] = skill
    if name:
        params["name"] = name
    if department:
        params["department"] = department
    if company:
        params["company"] = company
    if certification:
        params["certification"] = certification
    if city:
        params["city"] = city
    if similar_to:
        params["similar_to"] = similar_to
    if skill_gap_with:
        params["skill_gap_with"] = skill_gap_with

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{API_BASE}/employees", params=params)
            resp.raise_for_status()
            employees = resp.json()
    except httpx.ConnectError:
        return "Error: Cannot connect to API server. Start it with: python -m resume_graph.main"
    except Exception as e:
        return f"Error: {e}"

    if not employees:
        return "No employees found matching the criteria."

    lines = []
    for emp in employees:
        skills = [s["name"] for s in emp.get("skills", []) if s.get("name")]
        parts = [f"**{emp['name']}**"]
        if emp.get("title"):
            parts.append(f"Title: {emp['title']}")
        if emp.get("location"):
            parts.append(f"Location: {emp['location']}")
        if emp.get("companies"):
            parts.append(f"Companies: {', '.join(emp['companies'])}")
        if skills:
            parts.append(f"Skills: {', '.join(skills[:15])}")
        if emp.get("certifications"):
            parts.append(f"Certifications: {', '.join(emp['certifications'])}")
        lines.append("\n".join(parts))

    return f"Found {len(employees)} employee(s):\n\n" + "\n\n---\n\n".join(lines)


@mcp.tool()
def query_graph(question: str) -> str:
    """Ask a natural language question about the employee skill graph.

    The question is converted to a Cypher query and executed against Neo4j.

    Examples:
    - "Who knows both Python and Docker?"
    - "Which employees worked at Canva and know Kubernetes?"
    - "What are the most common skills?"
    - "Find AWS-certified engineers in Melbourne"
    """
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{API_BASE}/query",
                json={"question": question},
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.ConnectError:
        return "Error: Cannot connect to API server. Start it with: python -m resume_graph.main"
    except Exception as e:
        return f"Error: {e}"

    parts = [f"**Question:** {result['question']}"]
    if result.get("cypher"):
        parts.append(f"**Cypher:** `{result['cypher']}`")
    parts.append(f"**Answer:** {result['answer']}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
