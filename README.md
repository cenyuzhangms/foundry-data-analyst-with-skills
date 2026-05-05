# Foundry Hosted Agent + Skills demo

A hosted Foundry agent that demonstrates **Foundry Skills**: at startup the
agent reads every `skills/<name>/SKILL.md` in this repo and appends them to
its system prompt. Skills with a `bin/` directory also have their executable
baked into the container image at `/opt/skills/<name>/bin/` on `$PATH`, so
the agent can invoke them via the `run_shell` tool.

Result: the LLM both **knows** which playbooks/policies exist (Pattern A —
system-prompt injection) and, when applicable, can **execute** them
(Pattern C — `bin/` on `$PATH`).

## Skills shipped in this repo

**Prose-only policy** (`SKILL.md` only — shapes how the agent responds):

| Skill | Purpose |
|---|---|
| `exec-summary` | every recommendation/decision opens with TL;DR / Confidence / Recommended-action |

**Binary-backed playbooks** (`SKILL.md` + `bin/<exe>` baked into the image):

| Skill | Command | Purpose |
|---|---|---|
| `prd` | `prd "<feature title>"` | generate a one-page PRD scaffold (Problem / Users / Goals / Non-goals / Solution / Metrics / Open questions); save to `/work/prd/<slug>-<date>.md` |
| `five-whys` | `whys "<symptom>"` | run a 5-Whys root-cause chain; save to `/work/whys/<slug>-<date>.md` |

Each binary prints a Markdown scaffold with `<TODO: …>` slots; the agent then
fills them in using model knowledge and the user's description, and re-saves
the filled version.

The prose-only `exec-summary` skill demonstrates that a Foundry Skill is
fundamentally a **playbook**, not a tool — it ships zero new code and still
changes agent behavior because its text is appended to the system prompt.

See [`skills/`](./skills).

## Tools

`run_shell`, `read_file`, `save_artifact_as_data_url`, `fetch_url`.

## Repo layout

```
main.py                 # agent entrypoint: 4 tools + load_skills()
agent.yaml              # hosted-agent manifest (kind, cpu/mem, env)
azure.yaml              # azd service definition
Dockerfile              # bakes skills/<name>/bin/ into /opt/skills/<name>/bin/ on $PATH
requirements.txt        # python deps
skills/<name>/
  SKILL.md              # what + when + how (read locally at startup; also registered on Foundry)
  bin/<exe>             # optional executable (binary-backed skills only)
scripts/
  register_skills.py    # host-side: registers each SKILL.md on the Foundry project,
                        #   and deletes stale server-side skills not present locally
infra/                  # bicep (project, ACR, RBAC)
```

## Deploy

```pwsh
azd ai agent init -p <foundry-project-arm-id> -d gpt-4.1-mini --src .
azd deploy foundry-data-analyst-with-skills

# register the skills with the Foundry project (one-time, also re-run after edits):
pip install azure-ai-projects==2.1.0
python scripts/register_skills.py --endpoint <project-endpoint>
```

After first deploy, grant the instance MI:
- `AcrPull` on the project ACR
- `Cognitive Services OpenAI User` + `Cognitive Services User` on the Foundry account

## Try it

- **exec-summary**: "Should we move our metrics pipeline from cron to Airflow?"
  → answer opens with the TL;DR / Confidence / Recommended-action block.
- **prd**: "Draft a PRD for adding SSO to our admin portal."
  → agent runs `prd "SSO for admin portal"`, fills the `<TODO>` slots, saves to `/work/prd/...`.
- **five-whys**: "Our deploys have failed twice this week — help me figure out why."
  → agent runs `whys "deploys failing"`, fills the 5-row chain, ends with root cause + corrective action.
