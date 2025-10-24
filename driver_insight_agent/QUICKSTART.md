# Quick Start Guide - Driver Insight Agent

## 5-Minute Setup

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Installation

```bash
cd driver_insight_agent
pip install -r requirements.txt
```

### Verify Installation

```bash
python app.py capabilities
```

You should see the agent capabilities card displayed.

## Your First Request

### 1. View Example Requests

Run the built-in examples:

```bash
python app.py example
```

This will execute three example requests:
- Score Rankings
- Trip Summary
- Driver Comparison

### 2. Process a Custom Request

Create a file `my_request.json`:

```json
{
  "request_id": "my_first_request",
  "report_type": "score_only",
  "driver_ids": ["D001", "D002", "D003"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

Process it:

```bash
python app.py request my_request.json
```

### 3. View Statistics

```bash
python app.py stats
```

## Common Use Cases

### Get Top Performers

```json
{
  "request_id": "top_performers",
  "report_type": "ranking",
  "driver_ids": ["D001", "D002", "D003", "D004", "D005"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "sort_order": "desc"
}
```

### Filter High-Distance Trips

```json
{
  "request_id": "long_trips",
  "report_type": "trip_only",
  "driver_ids": ["D001"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z",
  "filters": [
    {
      "field": "distance",
      "operator": "gte",
      "value": 100
    }
  ]
}
```

### Compare Two Drivers

```json
{
  "request_id": "driver_comparison",
  "report_type": "comparison",
  "driver_ids": ["D001", "D002"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

### Analyze Score Trends

```json
{
  "request_id": "score_trends",
  "report_type": "trend",
  "driver_ids": ["D001"],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T23:59:59Z"
}
```

## Understanding Responses

### Successful Response

```json
{
  "request_id": "my_first_request",
  "success": true,
  "data": {
    "drivers": [...],
    "scores": [...]
  },
  "summary": "Report Type: score_only\nDrivers: 3\nScores: Driver D001: 85.23 (rank 1) | ...",
  "error": null,
  "execution_time_ms": 45.67,
  "tools_executed": ["driver_tool", "score_tool"],
  "cache_hits": 0
}
```

**Key Fields:**
- `success`: Boolean indicating request success
- `data`: Complete result data
- `summary`: Token-efficient summary
- `execution_time_ms`: Total execution time
- `tools_executed`: List of tools used
- `cache_hits`: Number of cache hits

### Error Response

```json
{
  "request_id": "my_first_request",
  "success": false,
  "data": null,
  "summary": null,
  "error": "Validation error: At least one driver identifier required",
  "execution_time_ms": 2.34,
  "tools_executed": [],
  "cache_hits": 0
}
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
cache:
  ttl_seconds: 3600
  max_size: 1000

concurrency:
  max_workers: 10
  batch_size: 50

pagination:
  default_page_size: 100
  max_page_size: 1000
```

## Programmatic Usage

```python
from agent.core import DriverInsightAgent
import asyncio
import json

async def main():
    # Initialize agent
    agent = DriverInsightAgent()
    
    # Create request
    request = {
        "request_id": "prog_001",
        "report_type": "score_only",
        "driver_ids": ["D001", "D002"],
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-03-31T23:59:59Z"
    }
    
    # Process request
    response = await agent.process_request(request)
    
    # Print results
    print(json.dumps(response, indent=2))

# Run
asyncio.run(main())
```

## Tips & Best Practices

### 1. Use Caching
- Repeated queries benefit from caching
- Check `cache_hits` in response
- Clear cache by deleting `cache_storage/` directory

### 2. Batch Requests
- Process multiple drivers in single request
- More efficient than individual requests
- Automatic parallel processing

### 3. Filter Early
- Apply filters to reduce data volume
- Improves performance for large datasets
- Reduces token usage in summaries

### 4. Choose Appropriate Report Types
- `score_only`: Fastest for score data
- `combined`: Use when you need both scores and trips
- `trend`: More expensive, use when trend analysis needed

### 5. Pagination
- Use `limit` and `offset` for large result sets
- Default page size: 100 items
- Maximum page size: 1000 items

## Troubleshooting

### Module Not Found Error

```bash
# Make sure you're in the project directory
cd driver_insight_agent

# Install dependencies
pip install -r requirements.txt
```

### Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH=/workspace/driver_insight_agent:$PYTHONPATH

# Or run from project root
cd /workspace/driver_insight_agent
python app.py example
```

### Cache Issues

```bash
# Clear cache
rm -rf cache_storage/

# Or disable caching in config.yaml
cache:
  enable_persistent: false
```

### Validation Errors

Check that:
- At least one driver identifier is provided
- Dates are in ISO 8601 format
- Report type is valid
- Filter operators are supported

## Next Steps

1. **Explore Examples**: Run `python app.py example` and review outputs
2. **Read Architecture**: See `ARCHITECTURE.md` for system design
3. **Customize Configuration**: Edit `config/config.yaml`
4. **Add Custom Tools**: Create new tools in `tools/` directory
5. **Integrate with Systems**: Use programmatic API in your applications

## Support

- **Documentation**: See `README.md` for comprehensive guide
- **Architecture**: See `ARCHITECTURE.md` for system design
- **Examples**: See `example_request.json` for request samples

## Performance Metrics

Expected performance on standard hardware:

- **Simple Query** (single driver, score only): ~50ms
- **Batch Query** (5 drivers, combined data): ~150ms
- **Trend Analysis** (90 days, single driver): ~300ms
- **Cached Query**: ~5ms

*Note: Times include mock data generation and processing.*
