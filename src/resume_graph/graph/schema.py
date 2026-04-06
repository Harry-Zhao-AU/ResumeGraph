"""Entity/relation schema for SchemaLLMPathExtractor.

Defines the 6 entity types and 6 relationship types that LlamaIndex will
extract from resume PDFs and store in Neo4j.
"""

from __future__ import annotations

from typing import Literal

# Entity types the LLM should extract from resume text
POSSIBLE_ENTITIES = Literal[
    "Employee",
    "Skill",
    "Company",
    "University",
    "Certification",
    "City",
]

# Entity properties the LLM should extract
POSSIBLE_ENTITY_PROPS = [
    # Employee properties
    ("name", "The person's full name, company name, skill name, etc."),
    ("email", "Email address of the employee"),
    ("title", "Job title, e.g. 'Senior Backend Engineer'"),
    ("department", "Department such as Engineering, Platform, Data, DevOps"),
    ("years_experience", "Total years of professional experience"),
    # Skill properties
    ("category", "Skill category: language, framework, database, cloud, devops, tool, methodology, soft-skill"),
    # City properties
    ("state", "Australian state: NSW, VIC, QLD, WA, SA, ACT, TAS, NT"),
]

# Relationship types between entities
POSSIBLE_RELATIONS = Literal[
    "HAS_SKILL",
    "WORKED_AT",
    "STUDIED_AT",
    "HAS_CERTIFICATION",
    "LOCATED_IN",
    "RELATED_TO",
]

# Relationship properties
POSSIBLE_RELATION_PROPS = [
    ("level", "Skill proficiency: beginner, intermediate, advanced, expert"),
    ("years", "Years of experience with a skill"),
    ("role", "Job role/title at a company"),
    ("start_year", "Year started at a company"),
    ("end_year", "Year left a company, or 'present'"),
    ("degree", "Academic degree, e.g. 'Bachelor of Engineering'"),
    ("field", "Field of study, e.g. 'Software Engineering'"),
]

# Validation schema: which entity types can be connected by which relations
VALIDATION_SCHEMA = [
    ("Employee", "HAS_SKILL", "Skill"),
    ("Employee", "WORKED_AT", "Company"),
    ("Employee", "STUDIED_AT", "University"),
    ("Employee", "HAS_CERTIFICATION", "Certification"),
    ("Employee", "LOCATED_IN", "City"),
    ("Skill", "RELATED_TO", "Skill"),
]
