# Data Processing Guidelines

## Library Priority

**polars > pandas** — all new data logic must use polars.

| Scenario | Library |
|----------|---------|
| New data logic | polars (mandatory) |
| Legacy code maintenance | pandas (allowed, migrate when practical) |
| .mat file interop | scipy.io |
| Excel read/write | polars + fastexcel / openpyxl |
| Database | duckdb / pyodbc |
| Graph/network | networkx |

## File I/O Patterns

```python
import polars as pl

# Reading (eager — immediate execution)
df = pl.read_csv("data/input.csv")
df = pl.read_excel("data/台账.xlsx")
df = pl.read_parquet("data/processed.parquet")

# Reading (lazy — builds query plan, preferred for large files)
lf = pl.scan_csv("data/large_input.csv")
lf = pl.scan_parquet("data/processed.parquet")
result = lf.filter(...).select(...).collect()

# Writing
df.write_csv("output/result.csv")
df.write_excel("output/result.xlsx")
df.write_parquet("output/result.parquet")  # preferred for intermediate data
```

## MATLAB Data Exchange

Preferred formats for Python↔MATLAB:
1. **CSV** — simple tabular data
2. **Excel (.xlsx)** — structured data with headers
3. **MAT files** — via `scipy.io.loadmat` / `scipy.io.savemat` for complex arrays

```python
from scipy.io import loadmat, savemat

data = loadmat("MATLAB/result.mat")
savemat("data/output.mat", {"matrix": result_array})
```

## Polars Expressions API

Expressions are the core building blocks. Use `pl.col()` to reference columns, chain methods to build transformations.

### Select — pick and transform columns

```python
df.select("name", "age")
df.select(
    pl.col("name"),
    (pl.col("duration_hours") * 60).alias("duration_minutes"),
)
```

### Filter — row-level conditions

```python
# Single condition
df.filter(pl.col("age") > 25)

# Multiple conditions (AND — pass as separate args)
df.filter(
    pl.col("voltage_level") == 10,
    pl.col("outage_count") > 0,
)

# OR condition
df.filter(
    (pl.col("type") == "cable") | (pl.col("type") == "overhead")
)
```

### With Columns — add/modify columns, preserving existing

```python
df.with_columns(
    duration_minutes=pl.col("duration_hours") * 60,
    name_upper=pl.col("name").str.to_uppercase(),
)
```

### Group By and Aggregations

```python
df.group_by("feeder").agg(
    pl.col("outage_hours").mean().alias("avg_outage"),
    pl.len().alias("event_count"),
)

# Conditional aggregation
df.group_by("district").agg(
    (pl.col("duration_hours") > 4).sum().alias("long_outage_count"),
)
```

### Window Functions (over)

Apply aggregations while keeping row count:

```python
df.with_columns(
    avg_by_feeder=pl.col("duration_hours").mean().over("feeder"),
    rank_in_feeder=pl.col("outage_count").rank().over("feeder"),
)
```

### Conditional Expressions

```python
df.with_columns(
    severity=pl.when(pl.col("duration_hours") > 8)
    .then(pl.lit("high"))
    .when(pl.col("duration_hours") > 2)
    .then(pl.lit("medium"))
    .otherwise(pl.lit("low")),
)
```

### Null Handling

```python
pl.col("x").fill_null(0)
pl.col("x").is_null()
pl.col("x").drop_nulls()
```

## Lazy vs Eager Evaluation

| Mode | API | When to use |
|------|-----|-------------|
| Eager (`DataFrame`) | `pl.read_csv()` | Small data, quick exploration |
| Lazy (`LazyFrame`) | `pl.scan_csv()` | Large data, complex pipelines |

Lazy benefits: automatic query optimization, predicate/projection pushdown, parallel execution.

```python
# Lazy pipeline — polars optimizes the full query before execution
result = (
    pl.scan_csv("data/outages.csv")
    .filter(pl.col("year") == 2024)
    .select("feeder", "duration_hours", "affected_users")
    .group_by("feeder")
    .agg(pl.col("duration_hours").sum())
    .collect()
)
```

For very large data, use streaming:

```python
result = lf.collect(streaming=True)
```

## Joins and Concatenation

```python
# Join
df1.join(df2, on="device_id", how="left")
df1.join(df2, left_on="bus_id", right_on="id", how="inner")

# Vertical concat (same schema)
pl.concat([df1, df2], how="vertical")

# Horizontal concat (same row count)
pl.concat([df1, df2], how="horizontal")
```

## Pandas Migration Quick Reference

When migrating legacy pandas code:

| pandas | polars |
|--------|--------|
| `df["col"]` | `df.select("col")` |
| `df[df["col"] > 10]` | `df.filter(pl.col("col") > 10)` |
| `df.assign(x=...)` | `df.with_columns(x=...)` |
| `df.groupby("col").agg(...)` | `df.group_by("col").agg(...)` |
| `df.groupby("col").transform(...)` | `df.with_columns(...).over("col")` |
| `df.merge(df2, on="col")` | `df.join(df2, on="col")` |
| `pd.concat([df1, df2])` | `pl.concat([df1, df2])` |
| `df.apply(func)` | `df.select(pl.col("x").map_elements(func))` |

Key differences: polars has no index, strict typing, parallel by default.

## Performance Best Practices

1. **Use lazy evaluation** for large datasets — `scan_*` over `read_*`
2. **Select columns early** — reduce data volume before heavy operations
3. **Avoid `.map_elements()`** — stay within expression API for parallelism
4. **Use appropriate types** — `pl.Categorical` for low-cardinality strings
5. **Prefer Parquet** for intermediate files — faster I/O than CSV

## Forbidden Patterns

- Do not mix polars and pandas in the same data pipeline
- Do not use `pd.read_csv` in new code — use `pl.read_csv`
- Avoid in-memory copies of large datasets
- Do not use Python loops over DataFrame rows — use expressions
