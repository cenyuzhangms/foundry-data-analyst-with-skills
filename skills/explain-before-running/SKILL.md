# explain-before-running

A policy that requires a one-line explanation immediately before any
non-trivial `run_shell` invocation. Improves user trust and catches bad
commands before they execute.

## When to use

Apply BEFORE every `run_shell` call **except** those whose entire command
matches the read-only allowlist below.

## Read-only allowlist (no explanation required)

Skip the explanation only when the full command is composed exclusively of
these verbs and their flags, on paths the user has already disclosed:

```
ls, pwd, cd, cat, head, tail, wc, file, stat, find (without -delete/-exec),
grep, rg, awk, sed (no -i), sort, uniq, cut, tr, column,
which, command -v, type,
echo, printf, date, env, printenv,
git status, git log, git diff, git show, git branch, git remote -v,
df, du, free, uptime, ps, top -b -n1, uname,
ping -c, curl -I, curl -s (GET only), dig, nslookup, host
```

Pipelines (`|`) are fine if every stage is on the allowlist. Redirection to
`/dev/null` is fine. Redirection to a file is NOT — that's a write.

## Required form

For every other command, emit a single line of the shape:

> **About to run:** `<the exact command>` — <what it does>; <what could go
> wrong>.

Examples:

> **About to run:** `pip install -r requirements.txt` — installs Python deps
> into the active env; could pull unintended versions if `requirements.txt`
> is unpinned.

> **About to run:** `git checkout main` — switches branch; will fail if there
> are uncommitted changes.

> **About to run:** `rm /work/scratch/old.csv` — deletes a single file under
> `/work/scratch/`; not recoverable.

Then call `run_shell` in the same turn. Don't ask permission for ordinary
commands — the explanation IS the disclosure. Reserve explicit confirmation
for things covered by other safety skills (destructive ops, prod targets).

## What "what could go wrong" should mention

Pick whichever applies; one clause is enough:

- **State change**: writes, deletes, modifies, installs, configures.
- **External effect**: network call, sends data, hits a paid API.
- **Lock / contention**: needs exclusive access, blocks other processes.
- **Cost / time**: long-running (see `long-running-jobs`), large download.
- **Reversibility**: hard or impossible to undo.

If literally nothing could go wrong, the command was probably allowlist-eligible
— recheck.

## Anti-patterns

- "I'll run a command to check that" (vague — what command? what does it do?).
- Burying the command inside a paragraph of prose.
- Explaining AFTER the run (defeats the purpose).
- Padding with "this is safe, don't worry" — say what it does, let the user
  judge.
