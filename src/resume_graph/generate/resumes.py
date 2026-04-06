"""Step 2a: Convert structured profiles to varied resume markdown text via LLM."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openai import AsyncAzureOpenAI

from resume_graph.config import settings
from resume_graph.models import Profile

PROFILES_DIR = Path("data/profiles")

RESUME_STYLES = [
    "concise and bullet-heavy, minimal prose",
    "narrative style with paragraph summaries for each role",
    "technical with project highlights and measurable outcomes",
    "traditional chronological format with formal tone",
]

SYSTEM_PROMPT = """\
You are a resume writer. Given a structured employee profile as JSON, write a realistic resume in markdown format.

Rules:
- Include: name, email, location at the top
- Professional summary (2-3 sentences)
- Work experience (2-3 roles with bullet points describing achievements)
- Technical skills section grouped by category
- Education section
- Certifications section (if any)
- Make it read like a real person wrote it — not robotic
- Include specific technologies and tools mentioned in the skills
- Add realistic achievement bullet points (e.g. "Reduced API latency by 40%")
- DO NOT include the word "fake" or indicate this is generated
"""


async def profile_to_resume_markdown(
    client: AsyncAzureOpenAI, profile: Profile, style_index: int
) -> str:
    """Generate a resume markdown from a structured profile."""
    style = RESUME_STYLES[style_index % len(RESUME_STYLES)]

    user_prompt = f"""Write a resume for this person using this style: {style}

Profile:
{profile.model_dump_json(indent=2)}"""

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.85,
        max_completion_tokens=2048,
    )

    return response.choices[0].message.content or ""


def load_profiles() -> list[tuple[str, Profile]]:
    """Load all profiles from data/profiles/."""
    profiles = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = Profile.model_validate(data)
        profiles.append((path.stem, profile))
    return profiles


async def generate_all_resumes() -> list[tuple[str, str]]:
    """Generate resume markdown for all profiles. Returns (filename_stem, markdown) pairs."""
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    profiles = load_profiles()
    if not profiles:
        print("No profiles found in data/profiles/. Run profile generation first.")
        return []

    results: list[tuple[str, str]] = []

    # Process in batches of 5 to avoid rate limits
    batch_size = 5
    for i in range(0, len(profiles), batch_size):
        batch = profiles[i : i + batch_size]
        tasks = [
            profile_to_resume_markdown(client, profile, i + j)
            for j, (_, profile) in enumerate(batch)
        ]
        markdowns = await asyncio.gather(*tasks)

        for (stem, profile), md in zip(batch, markdowns):
            results.append((stem, md))
            print(f"  Generated resume for: {profile.name}")

    return results


async def main() -> None:
    print("Generating resume markdown from profiles...")
    resumes = await generate_all_resumes()
    print(f"\nGenerated {len(resumes)} resumes.")
    return resumes


if __name__ == "__main__":
    asyncio.run(main())
