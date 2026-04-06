from __future__ import annotations

from pydantic import BaseModel


class SkillEntry(BaseModel):
    name: str
    category: str  # language/framework/database/cloud/devops/soft-skill/methodology
    level: str  # beginner/intermediate/advanced/expert
    years: int


class Company(BaseModel):
    name: str
    role: str
    start_year: int
    end_year: int | None = None  # None = current


class Education(BaseModel):
    university: str
    degree: str
    field: str
    graduation_year: int


class Profile(BaseModel):
    name: str
    email: str
    location: str  # Australian city
    state: str  # Australian state
    years_experience: int
    current_role: str  # junior/mid/senior/staff/principal
    title: str
    department: str
    companies: list[Company]
    skills: list[SkillEntry]
    certifications: list[str]
    education: Education


# API response models

class EmployeeResponse(BaseModel):
    name: str
    email: str | None = None
    title: str | None = None
    department: str | None = None
    years_experience: int | None = None
    skills: list[SkillEntry] = []
    companies: list[str] = []
    certifications: list[str] = []
    location: str | None = None
    university: str | None = None


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    cypher: str | None = None
