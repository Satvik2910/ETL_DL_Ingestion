# Driver Insight Agent

A modular, scalable analytics agent for comprehensive driver insights, supporting score analysis, trip summaries, trend detection, rankings, comparisons, and batch operations.

## Overview

The Driver Insight Agent is a deterministic, MCP-based analytics system designed to handle all driver analytics and reporting tasks. It receives structured requests, dynamically selects and orchestrates appropriate tools, and returns comprehensive, token-efficient results optimized for downstream LLM consumption.

## Key Features

- **Modular Architecture**: Clean separation of concerns with pluggable tools
- **MCP Tool Registry**: Dynamic tool discovery and registration
- **Intelligent Orchestration**: Automatic tool selection and execution ordering
- **High Performance**: Concurrent execution, caching, and pagination for large datasets
- **Error Resilience**: Retry mechanism with exponential backoff
- **Deterministic**: Idempotent operations with consistent outputs
- **Token-Efficient**: Optimized summarization for LLM consumption
- **Comprehensive Caching**: TTL-based and persistent caching
- **Flexible Filtering**: Numeric, string, and logical filter operations
- **Rich Aggregations**: Multiple aggregation functions and grouping
- **Trend Analysis**: Time-series analysis with anomaly detection

## Project Structure

```
driver_insight_agent/
│
├── app.py                      # Entry point and CLI
│
├── agent/
│   ├── core.py                 # Core orchestration logic
│   ├── mcp_registry.py         # Tool discovery and invocation
│   ├── abstract_card.py        # Agent metadata and capabilities
│
├── tools/
│   ├── driver_tool.py          # Driver resolution
│   ├── trip_tool.py            # Trip analytics
│   ├── score_tool.py           # Score aggregation and rankings
│   ├── trend_tool.py           # Time-series trend analysis
│
├── cache/
│   ├── cache_manager.py        # TTL and persistent caching
│
├── utils/
│   ├── filter_engine.py        # Filtering operations
│   ├── aggregation_engine.py   # Aggregation logic
│   ├── pagination.py           # Chunking and pagination
│   ├── summarizer.py           # Token-efficient summarization
│   ├── validation.py           # Schema validation
│
├── config/
│   ├── config.yaml             # Configuration settings
│   ├── config.py               # Configuration loader
│
└── requirements.txt            # Dependencies
```

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd driver_insight_agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure settings (optional):**
   Edit `config/config.yaml` to customize cache TTL, batch sizes, concurrency limits, etc.

## Usage

### Command Line Interface

```bash
# Show agent capabilities
python app.py capabilities

# Run example requests
python app.py example

# Process request from JSON file
python app.py request request.json

# Process request from stdin
echo '{"request_id": "req_001", ...}' | python app.py request

# Show statistics
python app.py stats
```

### Request Schema

```json
{
  "request_id": "unique_request_id",
  "report_type": "score_only|trip_only|combined|trend|ranking|comparison",
  "driver_ids": ["D001", "D002"],
  "driver_names": ["John Doe"],
  "driver_emails": ["john@example.com"],
  "driver_phones": ["+1-555-0101"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "filters": [
    {
      "field": "score",
      "operator": "gt",
      "value": 80
    }
  ],
  "aggregations": ["avg", "sum", "min", "max"],
  "limit": 100,
  "offset": 0,
  "sort_by": "score",
  "sort_order": "desc"
}
```

### Response Schema

```json
{
  "request_id": "unique_request_id",
  "success": true,
  "data": {
    "drivers": [...],
    "scores": [...],
    "trips": [...],
    "trends": [...],
    "aggregations": {...},
    "comparison": {...}
  },
  "summary": "Token-efficient summary...",
  "error": null,
  "execution_time_ms": 123.45,
  "tools_executed": ["driver_tool", "score_tool"],
  "cache_hits": 2
}
```

## Report Types

### 1. Score Only
Get driver scores with optional rankings and comparisons.

```json
{
  "request_id": "req_001",
  "report_type": "score_only",
  "driver_ids": ["D001", "D002", "D003"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

### 2. Trip Only
Retrieve trip analytics with filtering and summaries.

```json
{
  "request_id": "req_002",
  "report_type": "trip_only",
  "driver_ids": ["D001"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "filters": [
    {"field": "distance", "operator": "gt", "value": 50}
  ]
}
```

### 3. Combined
Get both score and trip data together.

```json
{
  "request_id": "req_003",
  "report_type": "combined",
  "driver_ids": ["D001", "D002"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

### 4. Ranking
Rank drivers by performance metrics.

```json
{
  "request_id": "req_004",
  "report_type": "ranking",
  "driver_ids": ["D001", "D002", "D003", "D004", "D005"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "sort_order": "desc"
}
```

### 5. Comparison
Side-by-side driver comparisons.

```json
{
  "request_id": "req_005",
  "report_type": "comparison",
  "driver_ids": ["D001", "D002"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

### 6. Trend
Time-series trend analysis.

```json
{
  "request_id": "req_006",
  "report_type": "trend",
  "driver_ids": ["D001"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

## Filter Operators

The agent supports the following filter operators:

- `eq`: Equal
- `ne`: Not equal
- `gt`: Greater than
- `gte`: Greater than or equal
- `lt`: Less than
- `lte`: Less than or equal
- `in`: In list
- `not_in`: Not in list
- `contains`: Contains substring
- `starts_with`: Starts with string
- `ends_with`: Ends with string

## Aggregation Functions

- `sum`: Sum of values
- `avg` / `mean`: Average
- `min`: Minimum value
- `max`: Maximum value
- `count`: Count of items
- `median`: Median value
- `std`: Standard deviation
- `variance`: Variance

## Advanced Scenarios

### Batch Aggregations
```json
{
  "request_id": "batch_001",
  "report_type": "score_only",
  "driver_ids": ["D001", "D002", "D003", "D004", "D005"],
  "aggregations": ["avg", "min", "max"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

### Cross-Driver Filtering
```json
{
  "request_id": "filter_001",
  "report_type": "ranking",
  "driver_ids": ["D001", "D002", "D003", "D004", "D005"],
  "filters": [
    {"field": "score", "operator": "gt", "value": 90}
  ]
}
```

### Complex Trip Filtering
```json
{
  "request_id": "trip_filter_001",
  "report_type": "trip_only",
  "driver_ids": ["D001", "D002", "D003"],
  "filters": [
    {"field": "distance", "operator": "gte", "value": 100},
    {"field": "status", "operator": "eq", "value": "completed"}
  ]
}
```

## Configuration

Edit `config/config.yaml` to customize:

- **Cache TTL**: Default 3600 seconds (1 hour)
- **Cache Size**: Maximum 1000 entries
- **Batch Size**: Default 50 items per batch
- **Max Workers**: Default 10 concurrent workers
- **Retry Attempts**: Default 3 attempts with exponential backoff
- **Page Size**: Default 100 items per page
- **Summarization**: Max 500 tokens

## Programmatic Usage

```python
from agent.core import DriverInsightAgent
import asyncio

async def main():
    # Initialize agent
    agent = DriverInsightAgent()
    
    # Prepare request
    request = {
        "request_id": "prog_001",
        "report_type": "score_only",
        "driver_ids": ["D001", "D002"],
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-03-31T23:59:59Z"
    }
    
    # Process request
    response = await agent.process_request(request)
    
    # Handle response
    if response['success']:
        print(f"Summary: {response['summary']}")
        print(f"Execution time: {response['execution_time_ms']}ms")
    else:
        print(f"Error: {response['error']}")

# Run
asyncio.run(main())
```

## Tool Development

To add a new tool:

1. Create a new file in `tools/` directory
2. Implement the tool with `execute()` and `get_capabilities()` methods
3. Register in `agent/mcp_registry.py`

Example:

```python
class CustomTool:
    def __init__(self):
        self.name = "custom_tool"
        self.description = "Custom analytics tool"
        self.version = "1.0.0"
    
    async def execute(self, parameters):
        # Tool logic here
        return {
            "success": True,
            "data": result,
            "execution_time_ms": time_ms
        }
    
    def get_capabilities(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {...},
            "output_schema": {...}
        }
```

## Performance Optimization

- **Caching**: Results are cached with configurable TTL
- **Concurrent Execution**: Independent tools run in parallel
- **Pagination**: Large datasets are chunked for efficient processing
- **Streaming**: Support for streaming data processing
- **Token Efficiency**: Summaries optimized for LLM token consumption

## Error Handling

The agent implements comprehensive error handling:

- **Validation Errors**: Caught at request validation stage
- **Tool Failures**: Individual tool failures don't stop entire workflow
- **Retry Logic**: Automatic retry with exponential backoff
- **Structured Logging**: All errors logged with context
- **Graceful Degradation**: Partial results returned when possible

## Testing

Run example requests to test functionality:

```bash
python app.py example
```

This will execute several example requests demonstrating different report types and features.

## Architecture

### Data Flow

1. **Request Reception**: Planner Agent sends structured request
2. **Validation**: Schema and field validation
3. **Cache Check**: Look for cached results
4. **Tool Discovery**: Determine required tools based on report type
5. **Execution Planning**: Order tools by dependencies
6. **Parallel/Sequential Execution**: Execute tools with retry logic
7. **Result Combination**: Merge tool outputs
8. **Post-Processing**: Apply filters, aggregations, sorting
9. **Summarization**: Generate token-efficient summary
10. **Response**: Return structured response with metadata

### Design Principles

- **Modularity**: Each component has single responsibility
- **Determinism**: Same input always produces same output
- **Scalability**: Handles large datasets efficiently
- **Observability**: Comprehensive logging and statistics
- **Configurability**: YAML-based configuration
- **Extensibility**: Easy to add new tools and features

## Acceptance Criteria ✓

- ✅ Handles Planner-Agent requests successfully
- ✅ Dynamically selects and executes appropriate tools
- ✅ Supports batching, pagination, and concurrency
- ✅ Validates input and output schemas
- ✅ Caches raw and summarized results efficiently
- ✅ Gracefully handles tool failures with retry logic
- ✅ Produces deterministic, idempotent, token-efficient outputs
- ✅ Fully modular, scalable, and maintainable

## License

MIT License

## Support

For issues or questions, please refer to the project documentation or contact the development team.
