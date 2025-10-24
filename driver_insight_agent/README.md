# Driver Insight Agent

A comprehensive, modular Driver Insight Agent capable of handling all driver analytics and reporting tasks. The agent receives requests from a Planner Agent and dynamically selects and orchestrates MCP-registered tools to provide deterministic, scalable analytics optimized for large datasets.

## Features

### Core Capabilities
- **Driver Resolution**: Resolve drivers by ID, name, email, or phone
- **Trip Analytics**: Comprehensive trip analysis with filtering and time range support
- **Score Analysis**: Driver scoring with rankings, comparisons, and trend analysis
- **Trend Analysis**: Time-series analysis and forecasting for driver metrics
- **Comparative Analysis**: Multi-driver performance comparisons
- **Anomaly Detection**: Statistical anomaly detection in driver performance data
- **Batch Processing**: Concurrent processing with pagination support
- **Data Summarization**: Token-efficient summaries for downstream LLM consumption

### Technical Features
- **Modular Architecture**: MCP-based tool registry for dynamic tool discovery
- **Caching System**: TTL and persistent caching for performance optimization
- **Concurrent Execution**: Parallel tool execution for batch requests
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Configuration Management**: Flexible YAML-based configuration
- **Structured Logging**: Comprehensive logging with structured output

## Project Structure

```
driver_insight_agent/
│
├── app.py                      # Entry point; initializes Driver Insight Agent
│
├── agent/
│   ├── core.py                 # Orchestrates tool selection, execution, caching, and summarization
│   ├── mcp_registry.py         # MCP tool discovery, registration, and invocation
│   ├── abstract_card.py        # Agent metadata, capabilities, and description
│
├── tools/
│   ├── driver_tool.py          # Driver resolution (ID, name, email, phone)
│   ├── trip_tool.py            # Trip analytics with filtering and time range support
│   ├── score_tool.py           # Score aggregation, rankings, and comparisons
│   ├── trend_tool.py           # Time-series and trend analysis
│
├── cache/
│   ├── cache_manager.py        # TTL caching, batch results storage, chunking
│
├── utils/
│   ├── filter_engine.py        # Numeric and string filtering
│   ├── aggregation_engine.py   # Aggregation logic (avg, totals, min/max, counts, comparisons)
│   ├── pagination.py           # Chunking and batch processing
│   ├── summarizer.py           # Token-efficient summarization
│   ├── validation.py           # Field validation and schema enforcement
│
├── config/
│   ├── config.yaml             # Cache TTLs, batch sizes, concurrency limits
│   ├── config.py               # Configuration loader and parser
│
└── requirements.txt
```

## Installation

1. **Clone or create the project directory**:
```bash
mkdir driver_insight_agent
cd driver_insight_agent
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Optional: Install Redis for persistent caching**:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

## Configuration

The agent uses a YAML configuration file (`config/config.yaml`) for settings:

```yaml
# Cache Configuration
cache:
  ttl_seconds: 3600  # 1 hour default TTL
  persistent_cache: true
  redis_url: "redis://localhost:6379/0"
  max_cache_size: 10000

# Execution Configuration
execution:
  max_concurrent_requests: 10
  request_timeout_seconds: 30
  retry_attempts: 3

# Data Processing Configuration
data:
  default_batch_size: 1000
  max_batch_size: 10000
  chunk_size: 500

# Summarization Configuration
summarization:
  max_summary_tokens: 2000
  include_metadata: true
  compression_ratio: 0.3
```

## Usage

### Command Line Interface

The agent supports multiple execution modes:

#### Interactive Mode (Default)
```bash
python app.py --mode interactive
```

#### Single Request Mode
```bash
python app.py --mode single --request '{"drivers": [{"driver_id": "DRV001"}], "report_type": "score"}'
```

#### File Processing Mode
```bash
python app.py --mode file --file requests.json
```

### Request Format

All requests follow a standard JSON format:

```json
{
  "request_id": "optional_unique_id",
  "drivers": [
    {"driver_id": "DRV001"},
    {"name": "John Smith"},
    {"email": "john@example.com"},
    {"phone": "+1-555-0101"}
  ],
  "report_type": "score|trip|combined|trend|comparison|ranking",
  "time_range": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z"
  },
  "filters": [
    {
      "field": "score_value",
      "operator": "gte",
      "value": 80
    }
  ],
  "aggregations": [
    {
      "operation": "avg",
      "field": "score_value",
      "alias": "average_score"
    }
  ],
  "options": {
    "include_metadata": true,
    "pagination": {
      "page_size": 100,
      "offset": 0
    }
  }
}
```

### Report Types

1. **Score Analysis** (`"report_type": "score"`):
   - Driver score analysis with rankings and comparisons
   - Supports multiple score types (overall, safety, efficiency, etc.)

2. **Trip Analysis** (`"report_type": "trip"`):
   - Comprehensive trip analytics with filtering
   - Distance, duration, efficiency metrics

3. **Combined Analysis** (`"report_type": "combined"`):
   - Both score and trip analysis in a single request
   - Cross-metric correlations and insights

4. **Trend Analysis** (`"report_type": "trend"`):
   - Time-series analysis and forecasting
   - Pattern recognition and anomaly detection

5. **Comparison** (`"report_type": "comparison"`):
   - Side-by-side driver performance comparisons
   - Relative performance rankings

6. **Rankings** (`"report_type": "ranking"`):
   - Driver rankings based on various criteria
   - Performance tiers and percentiles

## Example Requests

### 1. Driver Score Analysis
```json
{
  "drivers": [{"driver_id": "DRV001"}],
  "report_type": "score",
  "time_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "aggregations": [
    {"operation": "avg", "field": "score_value", "alias": "average_score"}
  ]
}
```

### 2. Multi-Driver Trip Comparison
```json
{
  "drivers": [
    {"driver_id": "DRV001"},
    {"driver_id": "DRV002"},
    {"driver_id": "DRV003"}
  ],
  "report_type": "comparison",
  "time_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

### 3. Top Performer Rankings
```json
{
  "report_type": "ranking",
  "time_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "options": {
    "limit": 10,
    "score_type": "overall"
  }
}
```

### 4. Trend Analysis with Forecasting
```json
{
  "drivers": [{"driver_id": "DRV001"}],
  "report_type": "trend",
  "time_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "options": {
    "metrics": ["overall_score", "safety_score", "efficiency_score"],
    "forecast_days": 30
  }
}
```

## Response Format

All responses follow a consistent structure:

```json
{
  "success": true,
  "request_id": "req_1234567890",
  "data": {
    "driver_resolution": { /* resolved driver data */ },
    "score_analysis": { /* score analysis results */ },
    "trip_analysis": { /* trip analysis results */ },
    "trend_analysis": { /* trend analysis results */ }
  },
  "summary": {
    "overview": { /* high-level summary */ },
    "key_metrics": { /* important metrics */ },
    "insights": [ /* actionable insights */ ]
  },
  "execution_info": {
    "execution_time_ms": 1250,
    "tools_executed": ["driver_tool", "score_tool"],
    "cache_used": false,
    "warnings": []
  },
  "metadata": {
    "agent_name": "Driver Insight Agent",
    "agent_version": "1.0.0",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Advanced Features

### Filtering
Support for complex filtering operations:
- Numeric comparisons: `eq`, `ne`, `gt`, `lt`, `gte`, `lte`
- String operations: `contains`, `startswith`, `endswith`, `regex`
- List operations: `in`, `not_in`
- Range operations: `between`
- Null checks: `is_null`, `is_not_null`

### Aggregations
Comprehensive aggregation support:
- Statistical: `count`, `sum`, `avg`, `median`, `mode`, `std`, `var`
- Range: `min`, `max`, `range`, `percentile`
- Advanced: `distinct_count`, `first`, `last`

### Caching
Multi-level caching system:
- **In-Memory Cache**: Fast access for recent results
- **Persistent Cache**: Redis-based storage for larger datasets
- **TTL Management**: Configurable expiration times
- **Cache Invalidation**: Tag-based cache clearing

### Batch Processing
Efficient handling of large datasets:
- **Concurrent Execution**: Parallel tool invocation
- **Pagination**: Chunked data processing
- **Memory Management**: Configurable batch sizes
- **Progress Tracking**: Execution monitoring

## API Reference

### Agent Status
```bash
# In interactive mode
> status
```

### Agent Capabilities
```bash
# In interactive mode
> capabilities
```

### Health Check
```bash
# In interactive mode
> health
```

## Performance Optimization

### Caching Strategy
- Cache frequently requested data with appropriate TTL
- Use persistent cache for expensive computations
- Implement cache warming for common queries

### Batch Processing
- Process multiple drivers concurrently
- Use pagination for large result sets
- Implement chunking for memory efficiency

### Tool Selection
- Dynamic tool selection based on request type
- Parallel execution where possible
- Graceful degradation on tool failures

## Error Handling

The agent implements comprehensive error handling:

1. **Request Validation**: Schema validation and compatibility checks
2. **Tool Failures**: Graceful degradation with partial results
3. **Timeout Handling**: Configurable timeouts with retries
4. **Cache Failures**: Fallback to direct computation
5. **Resource Limits**: Memory and processing limits

## Monitoring and Logging

### Structured Logging
- JSON-formatted logs for easy parsing
- Request tracing with unique IDs
- Performance metrics and timing
- Error categorization and severity

### Metrics
- Request success/failure rates
- Tool execution times
- Cache hit rates
- Resource utilization

## Development

### Running Tests
```bash
# Install development dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=driver_insight_agent
```

### Code Quality
```bash
# Format code
black driver_insight_agent/

# Lint code
flake8 driver_insight_agent/

# Type checking
mypy driver_insight_agent/
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY driver_insight_agent/ ./driver_insight_agent/
COPY config/ ./config/

CMD ["python", "-m", "driver_insight_agent.app"]
```

### Environment Variables
```bash
export REDIS_URL="redis://localhost:6379/0"
export LOG_LEVEL="INFO"
export MAX_CONCURRENT_REQUESTS="10"
export DEFAULT_BATCH_SIZE="1000"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For questions, issues, or feature requests, please contact the Driver Analytics Team or create an issue in the project repository.