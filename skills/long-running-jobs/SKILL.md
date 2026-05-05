# long-running-jobs

A policy for keeping the agent loop responsive when a shell command may take
longer than ~30 seconds (training runs, large downloads, full-table scans,
package installs, builds, simulations).

## When to use

Apply BEFORE invoking `run_shell` if ANY of the following are true. When in
doubt, background — the cost of being wrong (a one-line poll on the next
turn) is far smaller than the cost of a stalled UI.

- **Always background, no exceptions** — these are slow enough that even the
  "fast path" is too slow for a foreground tool call:
  - `pip install`, `pip3 install`, `python -m pip install`, `uv pip install`
  - `apt-get install`, `apt install`, `apk add`, `yum install`, `brew install`
  - `npm install`, `npm ci`, `yarn install`, `pnpm install`
  - `docker build`, `docker pull`, `docker push`
  - `git clone` of any non-trivial repo
  - `terraform apply`, `terraform plan` against real cloud
  - any `curl`/`wget`/download where the file is >10MB or size unknown
- the user said "this might take a while" or "let it run"
- the previous run of a similar command exceeded 20s
- the command pulls or processes >100MB
- model training, full dataset scan, `find /`, `du /`

If you can't classify the command in <2 seconds of thought, assume slow and
background. Foreground `run_shell` is for instant commands only (`ls`,
`cat`, `wc`, `grep`, `python -c "<short snippet>"`, etc).

## Procedure

1. **Background it.** Wrap the command so it survives and is non-blocking:

   ```bash
   nohup <cmd> > /work/jobs/<slug>.log 2>&1 &
   echo $! > /work/jobs/<slug>.pid
   ```

   Create `/work/jobs/` first with `mkdir -p`. `<slug>` is a short kebab-case
   name derived from the task (e.g. `train-rf`, `download-tripdata`).

2. **Return control immediately.** Tell the user the job is running, give them
   the slug, the PID, and the log path. Do NOT block waiting for completion in
   the same turn.

3. **Poll on the next turn (or when the user asks).** Check liveness and tail
   recent output:

   ```bash
   kill -0 $(cat /work/jobs/<slug>.pid) 2>/dev/null && echo RUNNING || echo DONE
   tail -n 30 /work/jobs/<slug>.log
   ```

4. **Report cleanly when done.** Summarize exit status (last log line / grep
   for ERROR), elapsed time, and any output artifacts. Don't paste the full
   log — link to it.

## Anti-patterns

- Running `sleep 120` or any other busy-wait inside the agent loop.
- Re-running the same long command because you forgot you already started it
  (always check `/work/jobs/<slug>.pid` first).
- Killing a job the user didn't ask you to kill.
- Backgrounding interactive commands that need stdin (won't work — those need
  a different pattern).

## Cleanup

When a job is confirmed complete and the user has seen the result, the PID
file can be removed. Keep the log file under `/work/jobs/` so it can be
referenced later.
