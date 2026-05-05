# ab-test

Rigorous A/B test analysis for two groups. Picks the right test (z-test for
proportions vs Welch's t for continuous), reports effect size, 95% CI, p-value,
and observed power.

## When to use

When the user asks "is variant B better than control?", "is this difference
significant?", or has two CSVs/columns and wants statistical analysis. Don't
hand-roll a t-test — this skill enforces the correct test choice and reports
all the things reviewers will ask for.

## Command

Two modes.

**Mode 1 — two CSVs, one numeric metric column each:**
```
abtest --control control.csv --variant variant.csv --metric revenue
```

**Mode 2 — single CSV with a group column:**
```
abtest --data results.csv --group arm --metric converted
```
For binary metrics (0/1), uses two-proportion z-test; otherwise Welch's t.

## Output

- n per arm, mean, std, conversion rate (binary)
- absolute and relative lift
- 95% CI on the difference
- p-value (two-sided)
- observed power at alpha=0.05
- minimum detectable effect for current sample size
