# eda-quick-look

A one-shot exploratory data analysis (EDA) profiler. Given any CSV/Parquet/JSON
file, prints schema, null/cardinality/basic stats, and saves a correlation
heatmap PNG.

## When to use

Use this **first** whenever the user hands you a new dataset and you don't
already know its schema. It is faster and more thorough than writing the
profile by hand.

## Command

```
eda <path-or-url> [--out /work/eda_<name>.png]
```

Accepts local paths under `/work` or http(s) URLs (DuckDB reads remote files
directly). Output:

- shape, dtypes, % null per column
- top-5 most frequent values for each non-numeric column (cardinality)
- numeric describe() (mean / std / min / 25 / 50 / 75 / max)
- correlation matrix heatmap → PNG path (embed it via `save_artifact_as_data_url`)

## Example

```
eda https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
```
