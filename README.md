# Foundry Data Analyst Sandbox + Skills

Same data analyst sandbox as
[`foundry-data-analyst-agent`](https://github.com/cenyuzhangms/foundry-data-analyst-agent),
but layered with **Foundry Skills**: at startup the agent discovers all skills
registered on its Foundry project, unzips each into `/opt/skills/<name>/`,
prepends `bin/` to `$PATH`, and appends every `SKILL.md` to the system prompt.

Result: the LLM both **knows** which playbooks exist (Pattern A — system-prompt
injection) and can **execute** them (Pattern C — bin/ on PATH, invoked via
`run_shell`).

## Skills shipped in this repo

Two flavors:

**Binary-backed** (`SKILL.md` + `bin/<exe>` baked into the image, on `$PATH`):

| Skill | Command | Purpose |
|---|---|---|
| `eda-quick-look` | `eda <path-or-url>` | one-shot dataset profile + correlation heatmap |
| `ab-test` | `abtest --control c.csv --variant v.csv --metric m` | two-arm A/B with the right test, CI, p, power, MDE |
| `time-series-decompose` | `tsdecomp --data x.csv --date d --value v` | STL decomposition + ADF + ACF/PACF |

**Prose-only** (`SKILL.md` only — agent-behavior policies, no executable):

| Skill | Purpose |
|---|---|
| `long-running-jobs` | background commands >30s with `nohup`, return control, poll later |
| `explain-before-running` | one-line "what / what could go wrong" before each non-readonly `run_shell` |
| `stop-when-stuck` | after 2 same-approach failures, stop and ask for direction instead of brute-forcing |

The prose-only skills demonstrate that a Foundry Skill is fundamentally a
**playbook**, not a tool — they ship zero new code and still change agent
behavior because their text is appended to the system prompt at startup.

See [`skills/`](./skills).

## Tools (same as base agent)

`run_shell`, `read_file`, `save_artifact_as_data_url`, `fetch_url`.

## Repo layout

```
main.py                 # agent entrypoint: 4 tools + load_skills()
agent.yaml              # hosted-agent manifest (kind, cpu/mem, env)
azure.yaml              # azd service definition
Dockerfile              # bakes skills/<name>/bin/ into /opt/skills/<name>/bin/ on $PATH
requirements.txt        # python deps
skills/<name>/
  SKILL.md              # what + when + how (registered on Foundry)
  bin/<exe>             # optional executable (binary-backed skills only)
scripts/
  register_skills.py    # host-side: POST /skills?api-version=v1 for each SKILL.md
infra/                  # bicep (project, ACR, RBAC)
```

## Deploy

```pwsh
azd ai agent init -p <foundry-project-arm-id> -d gpt-4.1-mini --src .
azd deploy foundry-data-analyst-with-skills

# register the skills with the Foundry project (one-time):
pip install azure-ai-projects==2.1.0
python scripts/register_skills.py --endpoint <project-endpoint>
```

After first deploy, grant the instance MI:
- `AcrPull` on the project ACR
- `Cognitive Services OpenAI User` + `Cognitive Services User` on the Foundry account

Then ask the agent something like:

> "Run an A/B test on `/work/exp.csv` (group column `arm`, metric `converted`) and tell me if variant beats control."

It will look at its playbooks list, decide `abtest` is the right tool, and call
it via `run_shell`.
