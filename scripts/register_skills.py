"""Register each skills/<name>/SKILL.md on the Foundry project (Pattern A).

Uses the SDK's JSON `create()` endpoint (instructions=SKILL.md body). The
executable bin/ files are baked into the agent's container image at build
time, so the binary-package upload path is not needed.
"""
import argparse
import asyncio
import sys
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--skills-root", default="skills")
    args = ap.parse_args()

    root = Path(args.skills_root)
    if not root.is_dir():
        print(f"no skills dir at {root}", file=sys.stderr)
        return 2

    async with DefaultAzureCredential() as cred, AIProjectClient(
        endpoint=args.endpoint, credential=cred, allow_preview=True
    ) as project:
        existing = []
        async for sk in project.beta.skills.list():
            existing.append(getattr(sk, "name", None))
        print(f"existing skills on project: {existing}")

        local_names = {p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").exists()}
        stale = [n for n in existing if n and n not in local_names]
        for n in stale:
            print(f"deleting stale server-side skill {n}...")
            try:
                await project.beta.skills.delete(name=n)
            except Exception as exc:
                print(f"  delete failed: {exc!r}")

        for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            name = skill_dir.name
            md = skill_dir / "SKILL.md"
            if not md.exists():
                print(f"skip {name}: no SKILL.md at root")
                continue
            instructions = md.read_text(encoding="utf-8")
            description = ""
            for line in instructions.splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    description = s[:512]
                    break

            if name in existing:
                print(f"deleting existing skill {name}...")
                try:
                    await project.beta.skills.delete(name=name)
                except Exception as exc:
                    print(f"  delete failed: {exc!r}")

            print(f"registering {name} (instructions={len(instructions)} chars)...")
            try:
                await project.beta.skills.create(
                    name=name, description=description, instructions=instructions
                )
                print("  ok")
            except Exception as exc:
                print(f"  FAILED: {exc!r}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
