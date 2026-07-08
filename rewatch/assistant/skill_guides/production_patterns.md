# Production instance patterns (read-only reference)

These patterns were distilled from a live Rewatch deployment with 500+ active
queries. The assistant exposes them via `list_instance_examples` and
`get_instance_example` tools.

## When to use

- Building analytics dashboards with derived SQL on cached queries
- Chaining Python queries with `get_query_result`
- EVM log scans or state balance tracking
- GraphQL subgraph pagination
- KPI counter rows from wide summary queries
- Dola Health-style dashboard layouts (KPI row + table + chart pairs)

## Workflow

```
list_instance_examples(category="query_results")
  → get_instance_example("results_derived_cte")
  → list_data_sources (resolve IDs in target org)
  → run_query (validate columns)
  → create_query / build_dashboard_from_spec
```

## Key stats from source instance

| Data source type | Active queries |
|------------------|----------------|
| Query Results    | 252            |
| Postgres         | 63             |
| EVM Logs         | 52             |
| Python           | 42             |
| EVM State        | 38             |
| GraphQL          | 32             |

| Chart type | Count |
|------------|-------|
| area       | 148   |
| line       | 140   |
| column     | 64    |
| pie        | 35    |

## Derived SQL (most common)

Base query caches subgraph/EVM data. Derived Query Results SQL references
`query_{child_id}`:

```sql
WITH data AS (
    SELECT "erc20Transfers_timestamp" AS block_time,
           SUM("erc20Transfers_value") AS amount
    FROM query_1130
    GROUP BY 1
)
SELECT DATE(block_time) AS day, MAX(amount) AS total
FROM data GROUP BY 1 ORDER BY 1
```

## Python chaining

```python
import pandas as pd
raw = get_query_result(347)
df = pd.DataFrame(raw['rows'])
# merge, aggregate...
return summary.to_dict('records')
```

## EVM logs

```yaml
contract_address: "0x..."
event_name: Transfer
start_block: -1000
end_block: 'latest'
```

## COUNTER from wide row

One query row with `total_debt_usd_all_users`, `total_collateral_usd_all_users`.
Each COUNTER uses `counterColName` matching the exact column name.
Use `create_multi_visualization_query` for several KPIs from one query.

## Dashboard layout (Dola Health pattern)

- Row 1: 4× COUNTER (sizeX 1-2, sizeY 4)
- Row 2: TABLE (sizeX 2) + 2× CHART side by side (sizeX 2, sizeY 8)
- Repeat blocks per section (Lending, AMM) with markdown headers between
