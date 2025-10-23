# Driver Insight Agent

A modular agent service for fetching and managing driver data from external APIs with an MCP (Model Context Protocol) Tool invocation layer.

## Features
- FastAPI service exposing driver endpoints
- MCP tool invocation to delegate fetch, validate, cache, summarize to an external MCP Tool Server
- Built-in retries, batching, and pagination awareness
- Validation of required fields (default: `driver_id`, `name`)
- Pluggable cache (in-memory by default; Redis via `REDIS_URL`)
- Structured logging with `structlog`

## Project Structure
```
config/
  config.yaml              # runtime configuration
  loader.py                # pydantic-backed config loader
services/
  agent.py                 # DriverInsightAgent orchestrator
  api_client.py            # direct API client (fallback to MCP tools)
  validator.py             # required fields validation
  logger.py                # structured logger setup
cache/
  base.py                  # cache interface
  memory.py                # in-memory cache implementation
  redis_cache.py           # redis-backed cache implementation
  manager.py               # selects cache based on env
mcp_tools/
  invoker.py               # MCP Tool Server invoker
routes/
  health.py                # /health
  drivers.py               # /drivers endpoints
examples/
  mcp_tool_server/         # example FastAPI MCP Tool Server
app.py                     # FastAPI application entry
requirements.txt
Dockerfile
```

## Configuration
Default `config/config.yaml`:
```yaml
api_base_url: "https://external.driver.api"
pagination_size: 100
max_retries: 3
cache_ttl: 600
mcp_tool_server_url: "http://localhost:8081/mcp-tools"
required_fields:
  - driver_id
  - name
```

Environment:
- `REDIS_URL` (optional): e.g. `redis://localhost:6379/0` to enable Redis cache.

## Run Locally
Install dependencies (Python 3.11+):
```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Health check:
```bash
curl http://localhost:8000/health
```

## Endpoints
- `GET /drivers/{driver_id}`: fetch a single driver
- `POST /drivers/batch`: fetch multiple drivers
- `GET /health`: service health

Example success response:
```json
{
  "driver_id": "D12345",
  "name": "John Doe",
  "vehicle": "Tesla Model Y",
  "rating": 4.8
}
```

Example error response:
```json
{
  "error": "Driver API unavailable",
  "reason": "API_UNAVAILABLE",
  "timestamp": "2025-10-23T09:10:00Z"
}
```

## Example MCP Tool Server
A simple reference FastAPI app is provided:
- `examples/mcp_tool_server/main.py`

Run it:
```bash
uvicorn examples.mcp_tool_server.main:app --host 0.0.0.0 --port 8081
```

Tools exposed:
- `POST /mcp-tools/FetchTool`
- `POST /mcp-tools/ValidateTool`
- `POST /mcp-tools/CacheTool`
- `POST /mcp-tools/SummarizeTool`

Set `mcp_tool_server_url` in `config.yaml` accordingly (default points to `http://localhost:8081/mcp-tools`).

## Docker
Build and run the Driver Insight Agent:
```bash
docker build -t driver-insight-agent .
docker run --rm -p 8000:8000 -v $PWD/config:/workspace/config \
  -e REDIS_URL="" \
  driver-insight-agent
```

Run the example MCP Tool Server:
```bash
uvicorn examples.mcp_tool_server.main:app --host 0.0.0.0 --port 8081
```

## Notes
- The agent first checks local cache; if miss, it tries MCP `CacheTool`, then MCP `FetchTool` (falling back to direct API client). Validation is performed through MCP `ValidateTool` or locally. Results are cached locally and remotely; optional `SummarizeTool` augments the record with a `summary` field.
- Pagination for batch fetches is managed via `pagination_size`.
