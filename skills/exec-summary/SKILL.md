# exec-summary

A formatting policy for any answer that runs longer than 3 sentences or makes
a recommendation. Forces every such response to open with a short executive
summary block, so the reader can decide whether to keep reading.

## When to use

Apply if ANY of the following are true:
- the response will exceed ~3 sentences
- the user asked "should we…?", "is it worth…?", "what do you recommend?"
- the response delivers a finding, a decision, an estimate, or a tradeoff
- the user is reasonably likely to forward this to someone else

If the answer is a one-line factual reply (e.g. "polars 1.17.1"), skip the
block — don't pad short answers.

## Required form

Open the response with EXACTLY this Markdown block, before any other content:

```
**TL;DR** — <one sentence, concrete, no hedging>
**Confidence** — high | medium | low (<one short reason>)
**Recommended action** — <a single imperative the reader can take, OR "no action — informational">
```

Then a blank line, then the rest of the response (details, evidence, code,
caveats, follow-up questions). The reader must be able to stop after the
three lines and still walk away with the right next step.

## Examples

```
**TL;DR** — Yes, switch from cron to a scheduler; estimated 2 engineer-weeks.
**Confidence** — medium (based on similar migrations; team's Airflow experience unverified).
**Recommended action** — Spike Airflow vs. Prefect for one week, then decide.

(detail follows…)
```

```
**TL;DR** — The query is slow because there's no index on `orders.created_at`.
**Confidence** — high (EXPLAIN shows a full table scan; the column is in the WHERE clause).
**Recommended action** — Add `CREATE INDEX idx_orders_created_at ON orders(created_at);` and re-test.

(detail follows…)
```

## Anti-patterns

- Hedging in the TL;DR ("it depends", "possibly", "you might want to consider").
  If you genuinely can't commit, lower the Confidence and write the most
  defensible single recommendation. Never punt with "it depends" alone.
- Padding short factual answers with this block. Use judgement.
- Putting the block at the END. It MUST come first — the whole point is that
  the reader can stop after it.
- More than three lines in the block. Detail goes below.
- Repeating the TL;DR verbatim in the body. Body should add evidence, not echo.
