# prd

Generates a one-page Product Requirements Document (PRD) Markdown file from a
short feature description. The output is opinionated, structured, and ready
to paste into a wiki or share with a team.

## When to use

Use when the user asks for any of:
- "draft a PRD for X"
- "write up requirements for X"
- "what would a one-pager for X look like"
- "spec out X" / "scope X"

For pure brainstorming (no commitment to write something down), prefer plain
prose. PRD is for when the user wants an artifact.

## Executable

`prd "<feature title>" [--problem "<text>"] [--users "<text>"]`

If only a title is given, the script generates section scaffolding with
`<TODO: …>` placeholders that the agent then fills in with model knowledge.

The script:
1. Prints the rendered Markdown to stdout (so the agent can show it inline).
2. Saves a copy to `/work/prd/<slug>-<YYYYMMDD>.md`.
3. Prints the saved path on the last line as `saved=<path>`.

## CRITICAL invocation rule

Do NOT emit any assistant text in the same turn that calls `run_shell` to run
`prd`. The Foundry response builder crashes with
`can only concatenate str (not "NoneType") to str` when a turn contains both
assistant prose and a tool call. Instead:

- Turn 1: call `run_shell` with the `prd` command ONLY (no chat text).
  Surface the explanation by prepending an echo banner inside the shell:
  `echo '>>> Generating PRD scaffold for: <title>' && prd "<title>"`
- Turn 2: emit the filled PRD as assistant prose, no tool call.

## What the agent does after invoking it

1. Run `prd "<title>"` (and optional flags) to get the scaffold.
2. REPLACE every `<TODO: …>` with concrete content. Do this even if the
   user gave you only a one-line title — use your own product judgement and
   model knowledge to make plausible, opinionated choices. **Do NOT ask the
   user clarifying questions before filling in the scaffold.** Fill it in
   first; the user will correct what they don't like. Keep the exact section
   structure — don't rename sections, don't add extra ones.
3. Re-save the filled version using `cat > /work/prd/<slug>-<date>.md <<'MD' …`
   (the path printed by the script).
4. Show the final PRD inline in the chat, then end with:
   `Saved: /work/prd/<slug>-<date>.md` so the user knows where it lives.

## Required PRD sections (the script enforces these)

1. **Title + one-line summary**
2. **Problem** — who is hurting and how, in concrete terms
3. **Users / personas** — who this is for; explicitly call out who it is NOT for
4. **Goals** — 3 measurable outcomes; no vague "improve UX"
5. **Non-goals** — 3 things this explicitly will not do
6. **Proposed solution** — one paragraph, plus a short bullet list of the
   user-visible changes
7. **Success metrics** — how you'll know it worked, with target numbers and
   measurement window (e.g. "p95 query latency < 200ms within 30 days")
8. **Open questions** — at least 3, each with the person/team who could answer

## Style rules

- One page. If a section grows past 5 lines, cut it.
- Numbers > adjectives. "30% faster" beats "much faster".
- Every "Goal" is testable. If it isn't, it's a "Non-goal" or it's vague.
- Don't editorialize ("this is exciting because…"). Just specify.
