# stop-when-stuck

A policy that prevents the agent from spinning on the same problem with
cosmetic variations. Trades persistence for honesty when an approach isn't
working.

## When to use

Continuously, in the background of every multi-step task. The trigger is
**two consecutive failures of the same approach**, where "same approach"
means:

- same tool / same command family (e.g. two flavors of `pip install <pkg>`)
- same target (same file, same URL, same resource)
- similar error class (both are auth errors, both are "not found", both are
  syntax errors in the same file)

Cosmetic differences — flag tweaks, retries with backoff, different quoting,
adding `sudo` — count as the same approach, not a new one.

## Procedure when triggered

**Stop. Do not try a third variant.** Instead, in one message:

1. **State plainly that you're stuck.** "I've tried twice and hit the same
   issue."

2. **Summarize what was tried.** Two or three bullets, each with the exact
   command and the failure mode:

   - Tried `<cmd 1>` → `<error 1>`
   - Tried `<cmd 2>` → `<error 2>`

3. **Name the most likely root cause** based on those signals, in one
   sentence. ("Looks like the package isn't published to the configured
   index" / "Token doesn't have the right scope" / "File is locked by
   another process".)

4. **Offer 1–3 distinct next directions** that would represent a real change
   of approach. Examples:

   - "Try a different tool" (e.g. `curl` instead of `wget`).
   - "Change the assumption" (e.g. maybe the file isn't where I thought).
   - "Need info I don't have" (ask the user for credentials, path, intent).
   - "Escalate" (this needs a human admin / out-of-band action).

5. **Wait for direction.** Do not start executing one of the options on your
   own.

## Counting failures correctly

A failure resets when you make a **substantive** change of approach. Examples:

| Did this count as a new approach? | |
|---|---|
| `pip install foo` then `pip3 install foo` | NO |
| `pip install foo` then `pip install foo --user` | NO |
| `pip install foo` then `apt-get install python3-foo` | YES |
| `cat /var/log/app.log` then `cat /var/log/app.log.1` | NO (same file family) |
| `cat /var/log/app.log` then `journalctl -u app` | YES (different log source) |

When in doubt, treat it as the same approach and stop sooner rather than
later.

## What this skill is NOT

- Not a ban on retries. One retry is fine. Retries with **bounded, principled
  backoff** for transient errors (network, 429, lock contention) are fine —
  they're a single approach with a built-in retry, not multiple approaches.
- Not a ban on creative problem solving. After the user picks a direction,
  pursue it confidently.
- Not a license to give up on the first failure. The trigger is **two**.

## Anti-patterns

- "Let me try one more thing…" (third variant of the same idea).
- Trying ever-more-elaborate quoting / escaping when the real problem is the
  command itself.
- Silent looping where each turn looks like progress but no new information
  was gained.
- Asking the user "should I try X?" and then trying X+ε before they answer.
