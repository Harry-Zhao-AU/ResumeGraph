"""CLI entry point: python -m resume_graph.generate"""

import asyncio

from resume_graph.generate.profiles import generate_all_profiles, save_profiles
from resume_graph.generate.resumes import generate_all_resumes
from resume_graph.generate.pdf_builder import render_all


async def main() -> None:
    # Step 1: Generate profiles
    print("=" * 60)
    print("STEP 1: Generating employee profiles...")
    print("=" * 60)
    profiles = await generate_all_profiles()
    save_profiles(profiles)
    print(f"\nDone: {len(profiles)} profiles saved to data/profiles/\n")

    # Step 2: Generate resume markdown + PDFs
    print("=" * 60)
    print("STEP 2: Generating resume markdown from profiles...")
    print("=" * 60)
    resumes = await generate_all_resumes()
    print(f"\nDone: {len(resumes)} resume texts generated\n")

    # Step 3: Render PDFs
    print("=" * 60)
    print("STEP 3: Rendering PDFs...")
    print("=" * 60)
    render_all(resumes)
    print(f"\nDone: {len(resumes)} PDFs saved to data/resumes/")


if __name__ == "__main__":
    asyncio.run(main())
