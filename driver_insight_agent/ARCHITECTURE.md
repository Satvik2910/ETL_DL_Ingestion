# Driver Insight Agent - Architecture Documentation

## System Architecture

### Overview

The Driver Insight Agent is a modular, event-driven analytics system built on the Model Context Protocol (MCP) pattern. It provides a unified interface for driver analytics while maintaining clean separation of concerns through tool-based architecture.

### Core Components

#### 1. Agent Core (`agent/core.py`)

The orchestrator that coordinates the entire workflow:

- **Request Processing**: Validates and processes incoming requests
- **Tool Orchestration**: Selects, orders, and executes tools
- **Caching Strategy**: Manages result caching for performance
- **Error Handling**: Implements retry logic and graceful degradation
- **Response Generation**: Combines results and generates summaries

**Key Responsibilities:**
- Validate request schema
- Discover required tools based on request type
- Determine execution order (parallel vs sequential)
- Manage tool-to-tool data passing
- Apply post-processing (filters, aggregations, sorting)
- Generate token-efficient summaries

#### 2. MCP Registry (`agent/mcp_registry.py`)

Tool management and discovery system:

- **Tool Registration**: Registers tools and their capabilities
- **Discovery**: Maps request types to required tools
- **Invocation**: Executes tools with parameters
- **Parallel Execution**: Manages concurrent tool execution
- **Validation**: Validates tool parameters against schemas

**Tool Dependencies:**
```
driver_tool (Priority 1)
    ↓
trip_tool, score_tool (Priority 2)
    ↓
trend_tool (Priority 3)
```

#### 3. Tools (`tools/`)

Independent, pluggable analytics modules:

##### Driver Tool
- Resolves drivers by ID, name, email, or phone
- Returns driver information and metadata
- Always executed first in the workflow

##### Trip Tool
- Retrieves trip data with time range filtering
- Calculates trip summaries and statistics
- Supports pagination for large datasets

##### Score Tool
- Aggregates driver performance scores
- Supports rankings and comparisons
- Calculates multiple score metrics

##### Trend Tool
- Analyzes time-series data
- Detects trends and anomalies
- Requires data from other tools (dependent execution)

#### 4. Cache Manager (`cache/cache_manager.py`)

Two-tier caching system:

**In-Memory Cache (TTL-based):**
- Fast access for recent queries
- Automatic expiration
- Configurable size and TTL

**Persistent Cache:**
- Disk-based storage for long-term caching
- Survives application restarts
- JSON-based serialization

**Caching Strategy:**
1. Check in-memory cache
2. If miss, check persistent cache
3. If miss, execute tool and cache result
4. Return cached result with metadata

#### 5. Utilities (`utils/`)

##### Filter Engine
- Supports 11 filter operators
- Handles numeric, string, and logical operations
- Nested field access via dot notation
- Time range filtering

##### Aggregation Engine
- 9 aggregation functions (sum, avg, min, max, count, median, std, variance)
- Group-by operations
- Ranking and comparison
- Percentile calculations

##### Pagination
- Chunk-based processing
- Offset-limit pagination
- Batch processing for concurrent operations
- Sliding window support

##### Summarizer
- Token-efficient output generation
- Component-specific summarization
- Compression for large datasets
- Configurable token limits

##### Validation
- Pydantic-based schema validation
- Request/response validation
- Filter condition validation
- Date format validation (ISO 8601)

### Data Flow

```
┌─────────────────┐
│ Planner Agent   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Request        │
│  Validation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cache Check    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tool Discovery │
│  & Ordering     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Driver         │
│  Resolution     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Parallel/Sequential    │
│  Tool Execution         │
│  (with Retry)           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│  Result         │
│  Combination    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Post-          │
│  Processing     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summarization  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Response       │
│  Generation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cache Storage  │
└─────────────────┘
```

### Execution Strategies

#### Parallel Execution
Used when tools are independent (e.g., trip_tool and score_tool):

```python
async def _execute_parallel(self, tools, driver_ids, request):
    tasks = [execute_tool(tool) for tool in tools]
    results = await asyncio.gather(*tasks)
    return results
```

**Benefits:**
- Reduced total execution time
- Efficient resource utilization
- Scalable for multiple drivers

#### Sequential Execution
Used when tools have dependencies (e.g., trend_tool needs score data):

```python
async def _execute_sequential(self, tools, driver_ids, request):
    results = []
    intermediate_data = {}
    
    for tool in tools:
        result = await execute_tool(tool, intermediate_data)
        intermediate_data[tool] = result['data']
        results.append(result)
    
    return results
```

**Benefits:**
- Proper data dependency handling
- Tool-to-tool communication
- Reference-based data passing

### Retry Mechanism

Exponential backoff with configurable parameters:

```python
for attempt in range(max_attempts):
    try:
        result = await execute_tool(tool, params)
        return result
    except Exception as e:
        if attempt < max_attempts - 1:
            delay = backoff_base ** attempt
            await asyncio.sleep(delay)
        else:
            return error_response
```

**Configuration:**
- Max Attempts: 3 (default)
- Backoff Base: 2 (default)
- Max Backoff: 60 seconds

### Report Type Mapping

| Report Type | Tools Required | Execution Mode |
|------------|----------------|----------------|
| score_only | driver_tool, score_tool | Parallel |
| trip_only | driver_tool, trip_tool | Parallel |
| combined | driver_tool, trip_tool, score_tool | Parallel |
| ranking | driver_tool, score_tool | Parallel |
| comparison | driver_tool, score_tool, trip_tool | Parallel |
| trend | driver_tool, score_tool, trend_tool | Sequential |

### Performance Optimization

#### 1. Caching Strategy
- **Tool-level**: Cache individual tool results
- **Batch-level**: Cache complete request results
- **Hit Rate Target**: >70% for repeated queries

#### 2. Concurrent Execution
- **Max Workers**: Configurable (default 10)
- **Batch Size**: Configurable (default 50)
- **Timeout**: Per-tool timeout configuration

#### 3. Data Processing
- **Chunking**: Large datasets split into manageable chunks
- **Streaming**: Support for streaming data processing
- **Lazy Loading**: Data loaded on-demand when possible

#### 4. Token Efficiency
- **Summarization**: Compressed summaries for LLM consumption
- **Field Selection**: Only essential fields in responses
- **Compression**: Remove verbose fields while preserving key data

### Error Handling Strategy

#### 1. Validation Errors
- Caught at request entry point
- Immediate failure with descriptive error
- No tool execution

#### 2. Tool Failures
- Individual tool failures logged
- Partial results returned when possible
- Workflow continues with available data

#### 3. System Errors
- Structured logging with context
- Graceful degradation
- Error response with execution metadata

### Extensibility

#### Adding New Tools

1. **Create Tool Class:**
```python
class NewTool:
    def __init__(self):
        self.name = "new_tool"
        self.description = "Description"
        self.version = "1.0.0"
    
    async def execute(self, parameters):
        # Implementation
        return result
    
    def get_capabilities(self):
        return metadata
```

2. **Register in MCP Registry:**
```python
# In mcp_registry.py _initialize_tools()
self.register_tool(NewTool())
```

3. **Update Discovery Logic:**
```python
# In mcp_registry.py discover_tools_for_request()
if report_type == 'new_report':
    tools.append('new_tool')
```

#### Adding New Report Types

1. Update `ReportType` enum in `validation.py`
2. Add mapping in `discover_tools_for_request()`
3. Update abstract card with new capability
4. Add usage example in documentation

### Configuration Management

Configuration hierarchy:
1. **Default Values**: Hardcoded in `config.py`
2. **YAML Configuration**: `config/config.yaml`
3. **Environment Variables**: Override via environment
4. **Runtime Configuration**: Programmatic updates

### Observability

#### Logging
- **Structured Logging**: JSON-formatted logs via structlog
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context**: Request ID, tool name, execution time

#### Metrics
- **Request Statistics**: Total, successful, failed requests
- **Cache Performance**: Hit rate, cache size, hits/misses
- **Tool Performance**: Execution times per tool
- **Error Tracking**: Error counts by type

#### Tracing
- **Request ID**: Unique ID for request tracking
- **Tool Chain**: List of executed tools
- **Execution Times**: Per-tool and total execution time

### Security Considerations

1. **Input Validation**: All inputs validated against schemas
2. **SQL Injection Prevention**: Parameterized queries (in production DB)
3. **Data Isolation**: Driver data access control
4. **Rate Limiting**: Configurable request limits
5. **Authentication**: Integration point for auth systems

### Scalability

#### Horizontal Scaling
- Stateless design enables multiple instances
- Shared persistent cache across instances
- Load balancer compatibility

#### Vertical Scaling
- Configurable worker pools
- Adjustable batch sizes
- Dynamic resource allocation

#### Data Scaling
- Pagination for large result sets
- Chunked processing for big datasets
- Streaming support for real-time data

### Testing Strategy

#### Unit Tests
- Individual tool testing
- Utility function testing
- Validation logic testing

#### Integration Tests
- End-to-end workflow testing
- Tool chaining validation
- Error handling verification

#### Performance Tests
- Load testing with concurrent requests
- Large dataset processing
- Cache performance validation

### Deployment

#### Production Checklist
- [ ] Configure production database connections
- [ ] Set appropriate cache TTLs
- [ ] Configure concurrency limits
- [ ] Enable persistent caching
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set authentication/authorization
- [ ] Enable rate limiting
- [ ] Configure backup strategy
- [ ] Document API endpoints

### Future Enhancements

1. **Real-time Data**: WebSocket support for live updates
2. **ML Integration**: Predictive analytics and anomaly detection
3. **Advanced Caching**: Redis/Memcached integration
4. **Database Integration**: Production database connectors
5. **API Gateway**: REST/GraphQL API layer
6. **Authentication**: OAuth2/JWT integration
7. **Rate Limiting**: Advanced rate limiting strategies
8. **Monitoring**: Prometheus/Grafana integration
9. **Alerting**: PagerDuty/Slack notifications
10. **Documentation**: Auto-generated API documentation
