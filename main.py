"""Foundry hosted Data Analyst Sandbox agent.

Exposes four tools:
  - run_shell(command, timeout_seconds, workdir): bash -lc inside the container
  - read_file(path, max_bytes): read a text/binary file from /work back into the model
  - save_artifact_as_data_url(path): turn a local file (e.g. PNG chart) into a
    data: URL so the model can return it inline as markdown.
  - fetch_url(url, dest_path): safe HTTP(S) download into /work with a size cap.

The agent is a "senior data analyst" persona: profile -> propose angles ->
execute (pandas/duckdb/matplotlib) -> chart -> explain.
"""

import asyncio
import base64
import logging
import mimetypes
import os
import subprocess
from pathlib import Path
from typing import Annotated

import requests
from dotenv import load_dotenv

load_dotenv()

from agent_framework import Agent
from agent_framework.azure import AzureAIAgentClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity.aio import DefaultAzureCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("data-analyst-agent")

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
WORKDIR = os.getenv("WORKDIR", "/work")
Path(WORKDIR).mkdir(parents=True, exist_ok=True)

MAX_OUTPUT_CHARS = 12_000
MAX_FETCH_BYTES = 500 * 1024 * 1024  # 500 MB hard cap on dataset downloads
MAX_READ_BYTES_DEFAULT = 200_000

SKILLS_ROOT = Path("/opt/skills")
SKILLS_ROOT.mkdir(parents=True, exist_ok=True)


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    keep = limit - 200
    return f"[...truncated {len(text) - keep} chars; showing last {keep}...]\n" + text[-keep:]


def run_shell(
    command: Annotated[str, "Bash command line to execute (run via `bash -lc`)."],
    timeout_seconds: Annotated[int, "Hard wall-clock timeout in seconds. Default 120."] = 120,
    workdir: Annotated[str, "Working directory; defaults to /work."] = "",
) -> str:
    """Execute a shell command inside the agent container.

    Use this for: pip install, running python scripts, duckdb CLI, file
    inspection, curl/wget, git, jq, etc. /work is persistent within a session.
    """
    cwd = workdir or WORKDIR
    try:
        result = subprocess.run(
            ["/bin/bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return f"exit_code=124\n[command timed out after {timeout_seconds}s]"
    except Exception as exc:  # pragma: no cover - surface raw error to the model
        return f"exit_code=-1\n[python error invoking shell: {exc!r}]"

    body = ""
    if result.stdout:
        body += "STDOUT:\n" + result.stdout
    if result.stderr:
        body += ("\n" if body else "") + "STDERR:\n" + result.stderr
    if not body:
        body = "(no output)"
    return _truncate(f"exit_code={result.returncode}\ncwd={cwd}\n{body}")


def read_file(
    path: Annotated[str, "Absolute or /work-relative path to read."],
    max_bytes: Annotated[int, "Max bytes to read; default 200_000."] = MAX_READ_BYTES_DEFAULT,
) -> str:
    """Read a small text file from disk and return its contents (truncated)."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(WORKDIR) / path
    if not p.exists():
        return f"error: {p} not found"
    try:
        data = p.read_bytes()[: max(1, min(max_bytes, 2_000_000))]
        try:
            return f"path={p}\nsize_bytes={p.stat().st_size}\n---\n" + data.decode("utf-8")
        except UnicodeDecodeError:
            return f"path={p}\nsize_bytes={p.stat().st_size}\n[binary file; {len(data)} bytes shown as repr]\n{data!r}"
    except Exception as exc:
        return f"error reading {p}: {exc!r}"


def save_artifact_as_data_url(
    path: Annotated[str, "Path to a chart/image/file to embed as a data: URL."],
) -> str:
    """Turn a local file (e.g. matplotlib PNG) into a data: URL.

    Use this to surface charts inline in your response. After calling, include
    the returned data URL in markdown like: `![chart](DATA_URL_HERE)`.
    """
    p = Path(path)
    if not p.is_absolute():
        p = Path(WORKDIR) / path
    if not p.exists():
        return f"error: {p} not found"
    size = p.stat().st_size
    if size > 5 * 1024 * 1024:
        return f"error: {p} is {size} bytes; refuse to embed files >5MB inline"
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def fetch_url(
    url: Annotated[str, "HTTP or HTTPS URL of the dataset/file to download."],
    dest_path: Annotated[str, "Destination filename (relative to /work) or absolute path."] = "",
) -> str:
    """Download a remote file into /work with a 500MB cap. Returns the local path and size."""
    if not (url.startswith("http://") or url.startswith("https://")):
        return "error: only http(s) URLs are supported"
    if not dest_path:
        dest_path = url.rstrip("/").split("/")[-1] or "download.bin"
    p = Path(dest_path)
    if not p.is_absolute():
        p = Path(WORKDIR) / dest_path
    p.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total = 0
            with open(p, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_FETCH_BYTES:
                        f.close()
                        p.unlink(missing_ok=True)
                        return f"error: download exceeded {MAX_FETCH_BYTES} bytes; aborted"
                    f.write(chunk)
        return f"saved={p}\nsize_bytes={total}"
    except Exception as exc:
        return f"error downloading {url}: {exc!r}"


INSTRUCTIONS = """You are a senior data analyst working inside a sandboxed Linux container.

Available tools:
- run_shell: bash -lc inside /work. Use for pip install (any package), python scripts, duckdb CLI, curl, git, jq.
- fetch_url: download a remote dataset into /work with a 500MB cap.
- read_file: read a small text file from /work back into context.
- save_artifact_as_data_url: turn a chart PNG into a data: URL for inline display.

Container facts:
- /work is your persistent scratch directory across turns within a session.
- Pre-installed: pandas, numpy, pyarrow, polars, duckdb, matplotlib, seaborn, scipy, scikit-learn, requests.
- Apt + pip work as root; install whatever else you need.
- Use `python3 - <<'PY' ... PY` heredocs from run_shell for ad-hoc analysis.
- DuckDB can query Parquet/CSV/JSON directly from URLs; prefer it for >100MB datasets.
- Skill executables (when registered) live under /opt/skills/<name>/bin/ and are on $PATH.
  Run `which <command>` from run_shell to confirm availability before using one.

Workflow for a new dataset:
1. Profile: shape, dtypes, null counts, sample rows, basic statistics.
2. Propose 2-3 interesting angles to investigate based on what the user asked.
3. Execute analyses; save charts as PNG to /work/<descriptive-name>.png.
4. Embed each chart inline: call save_artifact_as_data_url then return markdown
   `![title](data:...)`.
5. End with a 'Findings' section: 3-5 concrete bullet points with numbers.

Style:
- Always show the code/command you ran (in a fenced block).
- Numbers > adjectives. Cite counts, percentages, p-values.
- If a tool output is truncated, re-run with a tighter slice rather than guessing.
- If a request is ambiguous, make ONE reasonable assumption and proceed; mention it.
"""


async def load_skills(project_endpoint: str, credential: DefaultAzureCredential) -> str:
    """Load skill instructions for the system-prompt appendix.

    Primary source: local SKILL.md files under ./skills/<name>/SKILL.md (baked
    into the image). This avoids a runtime REST round-trip and works regardless
    of network/RBAC for the Foundry skills endpoint. Server-side registration
    (via scripts/register_skills.py) stays as the governance-facing surface.

    Pattern C is handled at image build time: skills/<name>/bin/ is COPYed into
    /opt/skills/<name>/bin/ and added to PATH by the Dockerfile.
    """
    skills_src = Path(__file__).parent / "skills"
    if not skills_src.is_dir():
        log.warning("local skills directory not found: %s", skills_src)
        return ""

    policy_chunks: list[str] = []     # no bin/ → behavior rules
    playbook_chunks: list[str] = []   # has bin/ → invokable tools
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding="utf-8").strip()
        except Exception as exc:
            log.warning("could not read %s: %r", skill_md, exc)
            continue
        if not text:
            continue
        name = skill_dir.name
        bin_path = SKILLS_ROOT / name / "bin"
        if bin_path.is_dir():
            playbook_chunks.append(
                f"### Playbook: {name}\n_executables: `{bin_path}` (on $PATH, invoke via `run_shell`)_\n\n{text}\n"
            )
        else:
            policy_chunks.append(f"### Policy: {name}\n\n{text}\n")
        log.info("loaded skill %s (bin_present=%s, chars=%d)", name, bin_path.is_dir(), len(text))

    if not policy_chunks and not playbook_chunks:
        return ""

    parts: list[str] = []
    if policy_chunks:
        parts.append(
            "\n\n## MANDATORY behavior policies (Foundry Skills)\n\n"
            "The following are RULES governing how you operate. They are not optional\n"
            "reference material. Apply each one continuously, on every turn, BEFORE the\n"
            "task-specific workflow described above. If a policy conflicts with the\n"
            "default workflow, the policy wins. Do not summarize, restate, or quote the\n"
            "policy text back to the user — just follow it.\n\n"
            + "\n---\n\n".join(policy_chunks)
        )
    if playbook_chunks:
        parts.append(
            "\n\n## Available playbooks (Foundry Skills)\n\n"
            "The following skill packages ship executables under `/opt/skills/<name>/bin/`\n"
            "(on $PATH). Invoke them via `run_shell`. Each playbook's instructions\n"
            "describe when and how to use it; prefer them over hand-rolled equivalents.\n\n"
            + "\n---\n\n".join(playbook_chunks)
        )
    return "\n".join(parts)


async def main() -> None:
    if not PROJECT_ENDPOINT:
        raise RuntimeError("PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT) must be set")

    log.info("data analyst agent starting; project=%s model=%s", PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME)

    async with (
        DefaultAzureCredential() as credential,
        AzureAIAgentClient(
            project_endpoint=PROJECT_ENDPOINT,
            model_deployment_name=MODEL_DEPLOYMENT_NAME,
            credential=credential,
        ) as client,
    ):
        skills_appendix = await load_skills(PROJECT_ENDPOINT, credential)
        instructions = INSTRUCTIONS + skills_appendix
        agent = Agent(
            client,
            name="DataAnalystWithSkillsAgent",
            instructions=instructions,
            tools=[run_shell, fetch_url, read_file, save_artifact_as_data_url],
        )
        log.info("agent listening on http://0.0.0.0:8088 (skills_chars=%d)", len(skills_appendix))
        await from_agent_framework(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
