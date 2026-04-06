"""Step 1: Generate structured employee profiles via Azure OpenAI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openai import AsyncAzureOpenAI

from resume_graph.config import settings
from resume_graph.models import Profile

PROFILES_DIR = Path("data/profiles")

BATCH_PROMPTS = [
    {
        "archetype": "backend",
        "count": 6,
        "guidance": (
            "Backend-heavy engineers. Skills should include combinations of: "
            "Java, Spring Boot, Kafka, PostgreSQL, Redis, gRPC, Python, Go, "
            "Microservices, REST APIs, SQL, Docker. "
            "Some should also know Python or TypeScript (overlap with other archetypes)."
        ),
    },
    {
        "archetype": "cloud",
        "count": 6,
        "guidance": (
            "Cloud/infrastructure engineers. Skills should include combinations of: "
            "AWS, Azure, GCP, Terraform, Kubernetes, Docker, CloudFormation, Lambda, "
            "EC2, S3, IAM, Networking. "
            "Some should also know Python or Go (overlap with backend/devops)."
        ),
    },
    {
        "archetype": "fullstack",
        "count": 6,
        "guidance": (
            "Full-stack engineers. Skills should include combinations of: "
            "React, TypeScript, Node.js, GraphQL, Next.js, CSS, HTML, Vue.js, "
            "PostgreSQL, MongoDB, REST APIs, Docker. "
            "Some should also know Python or AWS (overlap with other archetypes)."
        ),
    },
    {
        "archetype": "data_ml",
        "count": 5,
        "guidance": (
            "Data/ML engineers and data scientists. Skills should include combinations of: "
            "Python, PyTorch, TensorFlow, Spark, Airflow, Pandas, SQL, Jupyter, "
            "Scikit-learn, MLflow, Databricks, AWS/GCP. "
            "Some should also know Docker or Kubernetes (overlap with cloud/devops)."
        ),
    },
    {
        "archetype": "devops",
        "count": 4,
        "guidance": (
            "DevOps/SRE engineers. Skills should include combinations of: "
            "GitHub Actions, ArgoCD, Helm, Jenkins, Ansible, Terraform, "
            "Kubernetes, Docker, Prometheus, Grafana, Linux, Python, Bash. "
            "These profiles should share many skills with cloud and backend archetypes."
        ),
    },
    {
        "archetype": "mobile_other",
        "count": 3,
        "guidance": (
            "Mobile and specialist engineers. Skills should include combinations of: "
            "Swift, Kotlin, Flutter, React Native, iOS, Android, Firebase, "
            "TypeScript, CI/CD, REST APIs. "
            "Some should also know React or Node.js (overlap with full-stack)."
        ),
    },
]

SYSTEM_PROMPT = """\
You are a data generator that creates realistic fake employee profiles for an Australian tech company.
Return ONLY a valid JSON array of profile objects. No markdown, no explanation, just JSON.

Each profile must have exactly these fields:
{
  "name": "string (diverse backgrounds — Australian, Asian, European, Indian, etc.)",
  "email": "string (firstname.lastname@example.com)",
  "location": "string (Australian city: Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Hobart, Darwin)",
  "state": "string (NSW, VIC, QLD, WA, SA, ACT, TAS, NT)",
  "years_experience": "int (2-20)",
  "current_role": "string (junior/mid/senior/staff/principal)",
  "title": "string (e.g. 'Senior Backend Engineer')",
  "department": "string (Engineering, Platform, Data, DevOps, Mobile, Security, QA)",
  "companies": [
    {"name": "string (real or realistic AU/global tech companies)", "role": "string", "start_year": int, "end_year": int or null}
  ],
  "skills": [
    {"name": "string", "category": "string (language/framework/database/cloud/devops/soft-skill/methodology/tool)", "level": "string (beginner/intermediate/advanced/expert)", "years": int}
  ],
  "certifications": ["string (e.g. 'AWS Solutions Architect Associate')"],
  "education": {"university": "string (real Australian university)", "degree": "string", "field": "string", "graduation_year": int}
}

Rules:
- 5-10 skills per person, realistic for their role and experience level
- 2-3 companies per person, with realistic role progression
- Certifications: 0-2 per person, not everyone has them
- Make years_experience consistent with graduation_year and company history
- Use real Australian universities (UNSW, University of Melbourne, Monash, ANU, UQ, USyd, UTS, RMIT, etc.)
- Use real or realistic companies (Atlassian, Canva, REA Group, Xero, Commonwealth Bank, Afterpay, WiseTech Global, Google, AWS, Microsoft, etc.)
"""


async def generate_batch(
    client: AsyncAzureOpenAI, archetype: str, count: int, guidance: str, max_retries: int = 3
) -> list[Profile]:
    """Generate a batch of profiles for a given archetype."""
    user_prompt = (
        f"Generate exactly {count} {archetype} engineer profiles as a JSON object "
        f'with key "profiles" containing an array of {count} profile objects.\n\n{guidance}'
    )

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
                max_completion_tokens=8000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            # Extract the profiles list from the response
            profiles_list = _extract_profiles(data)
            profiles = [Profile.model_validate(p) for p in profiles_list]
            print(f"  Generated {len(profiles)} {archetype} profiles")
            return profiles
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed for {archetype}: {e}")
            if attempt == max_retries - 1:
                raise

    return []  # unreachable


def _extract_profiles(data: dict | list) -> list[dict]:
    """Extract profile dicts from various LLM response formats."""
    # Already a list
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict) and ("email" in d or "skills" in d)]

    # Single profile as a dict
    if isinstance(data, dict) and "email" in data and "skills" in data:
        return [data]

    # Wrapped: {"profiles": [...]} or {"employees": [...]} etc.
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                # Check it looks like profiles, not companies/skills
                if "email" in v[0] or "skills" in v[0] or "title" in v[0]:
                    return v

    raise ValueError(f"Cannot extract profiles. Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")


async def generate_all_profiles() -> list[Profile]:
    """Generate all 30 profiles across archetypes."""
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    all_profiles: list[Profile] = []
    for batch in BATCH_PROMPTS:
        profiles = await generate_batch(
            client, batch["archetype"], batch["count"], batch["guidance"]
        )
        all_profiles.extend(profiles)

    return all_profiles


def save_profiles(profiles: list[Profile]) -> None:
    """Save profiles as individual JSON files."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    for i, profile in enumerate(profiles, 1):
        path = PROFILES_DIR / f"{i:02d}_{profile.name.lower().replace(' ', '_')}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        print(f"  Saved: {path.name}")


async def main() -> None:
    print("Generating employee profiles...")
    profiles = await generate_all_profiles()
    print(f"\nGenerated {len(profiles)} profiles total. Saving...")
    save_profiles(profiles)
    print(f"\nDone! Profiles saved to {PROFILES_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
