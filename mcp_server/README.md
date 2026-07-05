# Rewatch MCP Server

A local [MCP](https://modelcontextprotocol.io) (stdio) server that exposes the Rewatch REST API to MCP clients such as Cursor or Claude Desktop.

## Tools

**Full API coverage** (driven by the live OpenAPI spec at `/api/spec`):

- `list_endpoints(tag?, search?)` — browse every registered endpoint
- `describe_endpoint(method, path)` — parameter/body/response details for one operation
- `call_api(method, path, query_params?, body?)` — invoke any endpoint

**Curated tools** for common workflows:

- **Read:** `run_query`, `search_queries`, `get_query`, `list_data_sources`, `get_data_source_schema`, `list_dashboards`, `get_dashboard`, `list_alerts`, `get_alert`, `list_ml_models`, `get_ml_model`, `get_predictions`, `list_destinations`, `list_indexers`
- **Write:** `create_query`, `update_query`, `archive_query`, `create_alert`, `update_alert`, `delete_alert`, `create_dashboard`, `update_dashboard`, `create_visualization`, `update_visualization`, `add_widget_to_dashboard`, `update_widget`, `delete_widget`, `create_destination`, `update_destination`, `create_ml_model`, `update_ml_model`, `train_ml_model`, `predict_ml_model`, `create_indexer`, `update_indexer`

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `REWATCH_API_KEY` | yes | — | Your user API key (Rewatch UI → profile → API Key) |
| `REWATCH_BASE_URL` | no | `http://localhost:5001` | Base URL of the Rewatch instance |
| `REWATCH_MCP_READ_ONLY` | no | unset | When `true`, `call_api` only allows GET requests |

The server automatically loads `${workspace}/.env` when present, so you can keep the API key there instead of in `mcp.json`.

## Running

With [uv](https://docs.astral.sh/uv/) (no install step needed):

```bash
REWATCH_API_KEY=... uv run --directory mcp_server rewatch-mcp
```

Or with pip:

```bash
pip install -e mcp_server
REWATCH_API_KEY=... rewatch-mcp
```

## Client configuration

Example `mcp.json` entry (Cursor: `.cursor/mcp.json`, already included in this repo).
Put `REWATCH_API_KEY` in the workspace `.env` file (recommended) or in the `env` block:

```json
{
  "mcpServers": {
    "rewatch": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rewatch/mcp_server", "rewatch-mcp"],
      "env": {
        "REWATCH_BASE_URL": "http://localhost:5001",
        "REWATCH_API_KEY": "<your api key>"
      }
    }
  }
}
```
