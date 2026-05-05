# time-series-decompose

STL decomposition of a univariate time series + ACF/PACF diagnostics. Tells you
trend, seasonality, residual, stationarity (ADF test), and saves a 4-panel PNG.

## When to use

When the user has a time-indexed metric (daily revenue, hourly traffic, weekly
signups) and asks "is there a trend?", "what's the seasonality?", "is there a
weekly cycle?", or wants to forecast (do this BEFORE choosing a model).

## Command

```
tsdecomp --data <csv-or-parquet> --date <date_col> --value <metric_col> \
         [--period 7] [--out /work/ts_<metric>.png]
```

`--period` is the seasonality length (7 for daily-with-weekly, 24 for
hourly-with-daily, 12 for monthly-with-yearly). If omitted, the skill picks
based on inferred frequency.

## Output

- inferred frequency, range, missing-date count
- ADF stationarity p-value (raw + first-difference)
- 4-panel PNG: observed, trend, seasonal, residual
- ACF / PACF top lags
