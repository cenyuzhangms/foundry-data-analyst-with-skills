# five-whys

Runs the classic 5-Whys root-cause analysis on a stated problem and emits a
structured Markdown chain ending with the proposed corrective action. Useful
for incident retros, deploy failures, recurring bugs, customer-impact
post-mortems, and process problems.

## When to use

Use when the user describes:
- a recurring failure ("the deploy broke again")
- an incident or outage
- a customer-reported issue with unclear root cause
- a process pain point ("our standups always run long")
- any "why does X keep happening?" question

Do NOT use for:
- one-off questions with an obvious cause already named
- speculation with no evidence (5-Whys needs a real symptom)

## Executable

`whys "<symptom>"`

The script prints a 5-row Markdown table to stdout with `<TODO: …>` slots for
each "Why?" answer and a final corrective-action row, plus saves a copy to
`/work/whys/<slug>-<date>.md`.

## CRITICAL invocation rule

Do NOT emit any assistant text in the same turn that calls `run_shell` to run
`whys`. The Foundry response builder crashes with
`can only concatenate str (not "NoneType") to str` when a turn contains both
assistant prose and a tool call. Instead:

- Turn 1: call `run_shell` with the `whys` command ONLY (no chat text).
  Surface the explanation by prepending an echo banner inside the shell:
  `echo '>>> Running 5-Whys on: <symptom>' && whys "<symptom>"`
- Turn 2: emit the filled chain as assistant prose, no tool call.

## What the agent does after invoking it

1. Run `whys "<symptom>"` to get the scaffold.
2. Fill each `<TODO: answer>` with the most plausible cause given the user's
   description and your own engineering judgement. Each "Why?" should drill
   one layer DEEPER than the row above — not restate it. **Do NOT ask the
   user clarifying questions before filling in the chain.** Make plausible
   assumptions, fill it in, and call them out at the end if needed.
3. For the final row (Corrective action), propose ONE concrete change that
   addresses the root cause, not the symptom.
4. Re-save the filled version to the path the script printed.
5. Show the table inline in chat, then end with one sentence naming the root
   cause and the action.

## Quality bar for the chain

- Each "Why?" answer must be testable / falsifiable, not a vibe ("the system
  is fragile" is bad; "we have no integration tests for the payment path" is
  good).
- The chain should move from symptom → process → root cause, not stay at the
  symptom layer.
- Stop drilling if you hit "human nature" or "physics" — that's not actionable.
- The corrective action must address the LAST why, not an earlier one. If
  it would address an earlier why, the chain is too long; trim it.

## Anti-patterns

- "Why? Because the team didn't catch it." (blame, not cause — go deeper)
- All five whys at the same layer of abstraction
- Corrective action is "be more careful" / "add training" — those rarely
  fix systems. Prefer process or tooling changes.
- Skipping straight to the answer without the chain — the chain IS the value.
