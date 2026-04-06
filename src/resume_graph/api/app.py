"""FastAPI app: 2 endpoints — GET /employees and POST /query."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from resume_graph.graph.retrievers import query_with_cypher, query_natural_language
from resume_graph.models import EmployeeResponse, QueryRequest, QueryResponse, SkillEntry

app = FastAPI(
    title="ResumeGraph API",
    description="HR Skill Graph — query employee skills, companies, and relationships",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/employees", response_model=list[EmployeeResponse])
def get_employees(
    skill: str | None = Query(None, description="Filter by skill name"),
    name: str | None = Query(None, description="Search by employee name"),
    department: str | None = Query(None, description="Filter by department"),
    company: str | None = Query(None, description="Filter by company worked at"),
    certification: str | None = Query(None, description="Filter by certification"),
    city: str | None = Query(None, description="Filter by city"),
    similar_to: str | None = Query(None, description="Find employees with overlapping skills"),
    skill_gap_with: str | None = Query(None, description="Show skills this employee lacks vs target (requires name)"),
) -> list[EmployeeResponse]:
    """List/search employees with optional filters."""

    # Skill gap analysis: what skills does `name` lack that `skill_gap_with` has?
    if skill_gap_with and name:
        return _skill_gap(name, skill_gap_with)

    # Find similar employees by shared skills
    if similar_to:
        return _similar_employees(similar_to)

    # Build dynamic Cypher query based on filters
    match_clauses = []
    where_parts = []
    params: dict = {}

    if skill:
        # Semantic skill search: find the skill + any RELATED_TO skills, then match employees
        related_skills = _get_related_skills(skill)
        match_clauses.append("MATCH (e)-[:HAS_SKILL]->(s_filter)")
        where_parts.append("s_filter.name IN $skill_names")
        params["skill_names"] = related_skills
    else:
        # Ensure we only get entities that have HAS_SKILL (i.e., employees)
        match_clauses.append("MATCH (e)-[:HAS_SKILL]->()")

    if company:
        match_clauses.append("MATCH (e)-[:WORKED_AT]->(c_filter {name: $company})")
        params["company"] = company
    if certification:
        match_clauses.append("MATCH (e)-[:HAS_CERTIFICATION]->(cert_filter {name: $certification})")
        params["certification"] = certification
    if city:
        match_clauses.append("MATCH (e)-[:LOCATED_IN]->(city_filter {name: $city})")
        params["city"] = city
    if name:
        where_parts.append("e.name CONTAINS $name")
        params["name"] = name
    if department:
        where_parts.append("e.department CONTAINS $department")
        params["department"] = department

    cypher = "\n".join(match_clauses)
    if where_parts:
        cypher += "\nWHERE " + " AND ".join(where_parts)

    cypher += """
WITH DISTINCT e
OPTIONAL MATCH (e)-[:HAS_SKILL]->(s)
OPTIONAL MATCH (e)-[:WORKED_AT]->(c)
OPTIONAL MATCH (e)-[:HAS_CERTIFICATION]->(cert)
OPTIONAL MATCH (e)-[:LOCATED_IN]->(loc)
OPTIONAL MATCH (e)-[:STUDIED_AT]->(uni)
RETURN e.name AS name, e.email AS email, e.title AS title,
       e.department AS department, e.years_experience AS years_experience,
       COLLECT(DISTINCT s.name) AS skills,
       COLLECT(DISTINCT c.name) AS companies,
       COLLECT(DISTINCT cert.name) AS certifications,
       loc.name AS location,
       uni.name AS university
ORDER BY e.name
LIMIT 50
"""

    results = query_with_cypher(cypher, params)
    return [
        EmployeeResponse(
            name=r["name"] or "Unknown",
            email=r.get("email"),
            title=r.get("title"),
            department=r.get("department"),
            years_experience=_safe_int(r.get("years_experience")),
            skills=[SkillEntry(name=s, category="", level="", years=0) for s in (r.get("skills") or []) if s],
            companies=[c for c in (r.get("companies") or []) if c],
            certifications=[c for c in (r.get("certifications") or []) if c],
            location=r.get("location"),
            university=r.get("university"),
        )
        for r in results
        if r.get("name")
    ]


@app.post("/query", response_model=QueryResponse)
def post_query(body: QueryRequest) -> QueryResponse:
    """Natural language graph query via LlamaIndex TextToCypherRetriever."""
    result = query_natural_language(body.question)
    return QueryResponse(
        question=body.question,
        answer=result["answer"],
        cypher=result.get("cypher"),
    )


def _similar_employees(employee_name: str) -> list[EmployeeResponse]:
    """Find employees with the most overlapping skills."""
    cypher = """
MATCH (target)-[:HAS_SKILL]->(s)<-[:HAS_SKILL]-(other)
WHERE target.name CONTAINS $name AND target <> other
WITH other, COUNT(DISTINCT s) AS shared, COLLECT(DISTINCT s.name) AS shared_skills
ORDER BY shared DESC LIMIT 10
OPTIONAL MATCH (other)-[:LOCATED_IN]->(loc)
RETURN other.name AS name, other.title AS title,
       shared AS years_experience, shared_skills AS skills,
       loc.name AS location
"""
    results = query_with_cypher(cypher, {"name": employee_name})
    return [
        EmployeeResponse(
            name=r["name"] or "Unknown",
            title=r.get("title"),
            years_experience=r.get("years_experience"),
            skills=[SkillEntry(name=s, category="", level="", years=0) for s in (r.get("skills") or []) if s],
            location=r.get("location"),
        )
        for r in results
        if r.get("name")
    ]


def _skill_gap(source_name: str, target_name: str) -> list[EmployeeResponse]:
    """Skills the target has that the source lacks."""
    cypher = """
MATCH (target)-[:HAS_SKILL]->(s)
WHERE target.name CONTAINS $target
AND NOT EXISTS {
    MATCH (source)-[:HAS_SKILL]->(s)
    WHERE source.name CONTAINS $source
}
RETURN $source AS name, COLLECT(DISTINCT s.name) AS skills
"""
    results = query_with_cypher(cypher, {"source": source_name, "target": target_name})
    if not results:
        return []
    r = results[0]
    return [
        EmployeeResponse(
            name=f"Skill gap: {source_name} vs {target_name}",
            skills=[SkillEntry(name=s, category="", level="", years=0) for s in (r.get("skills") or []) if s],
        )
    ]


def _get_related_skills(skill: str) -> list[str]:
    """Get a skill name + all semantically related skill names via RELATED_TO edges."""
    result = query_with_cypher(
        "MATCH (a {name: $skill})-[:RELATED_TO]-(b) RETURN COLLECT(DISTINCT b.name) AS related",
        {"skill": skill},
    )
    related = result[0]["related"] if result and result[0].get("related") else []
    # Always include the original skill
    all_skills = [skill] + [r for r in related if r]
    return list(set(all_skills))


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
