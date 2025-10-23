# Driver Insight Agent

A modular, production-ready Python service for fetching and managing driver data efficiently from external APIs. Built with FastAPI and integrating Model Context Protocol (MCP) tools for extensible, modular execution.

## 🎯 Purpose

The Driver Insight Agent is designed to:
- Fetch driver data from external APIs (single, batch, or paginated requests)
- Validate data integrity with configurable field requirements
- Implement intelligent caching with configurable TTL
- Integrate with external MCP Tool Server for modular operations
- Handle API unavailability gracefully with structured logging
- Provide a scalable, extensible architecture for future enhancements

## ✨ Key Features

- ✅ **Single & Batch Operations**: Fetch one driver or hundreds simultaneously
- ✅ **Smart Pagination**: Automatic handling of paginated API responses
- ✅ **Data Validation**: Ensures minimum required fields (driver_id, name)
- ✅ **Caching Layer**: In-memory or Redis caching with configurable TTL
- ✅ **MCP Integration**: Dynamic invocation of external MCP tools
- ✅ **Graceful Degradation**: Handles API failures with retry logic
- ✅ **Structured Logging**: JSON or text logging with contextual information
- ✅ **Health Checks**: Monitor service and component health
- ✅ **Production-Ready**: Docker support, async operations, comprehensive error handling

## 📁 Project Structure

```
driver-insight-agent/
├── app.py                      # Main FastAPI application
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Production Docker image
├── docker-compose.yml          # Multi-service orchestration
├── .env.example                # Environment variables template
│
├── config/                     # Configuration management
│   └── __init__.py            # Config loader with Pydantic models
│
├── services/                   # Core business logic
│   ├── __init__.py
│   ├── api_client.py          # API client with retry & pagination
│   ├── driver_insight_agent.py # Main orchestrator
│   └── validator.py           # Data validation logic
│
├── cache/                      # Caching layer
│   ├── __init__.py
│   └── cache_manager.py       # In-memory & Redis cache backends
│
├── mcp_tools/                  # MCP tool integration
│   ├── __init__.py
│   └── mcp_invoker.py         # MCP tool invocation client
│
├── routes/                     # FastAPI routes
│   ├── __init__.py
│   └── driver_routes.py       # Driver-related endpoints
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   └── logger.py              # Structured logging
│
└── mcp_tool_server/            # Example MCP Tool Server
    ├── app.py                 # MCP tools implementation
    ├── requirements.txt
    └── Dockerfile
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional, for containerized deployment)
- Redis (optional, for distributed caching)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd driver-insight-agent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run the MCP Tool Server** (in a separate terminal)
```bash
cd mcp_tool_server
pip install -r requirements.txt
python app.py
# Server runs on http://localhost:8081
```

6. **Run the Driver Insight Agent**
```bash
python app.py
# Service runs on http://localhost:8080
```

7. **Access the API documentation**
```
http://localhost:8080/docs
```

### Docker Deployment

1. **Using Docker Compose** (Recommended)
```bash
docker-compose up --build
```

This starts:
- Driver Insight Agent on port 8080
- MCP Tool Server on port 8081
- Redis on port 6379

2. **Using Docker directly**
```bash
# Build image
docker build -t driver-insight-agent .

# Run container
docker run -p 8080:8080 \
  -e API_BASE_URL=https://external.driver.api \
  -e CACHE_TYPE=memory \
  driver-insight-agent
```

## 📋 Configuration

### Configuration File (config.yaml)

```yaml
api:
  base_url: "https://external.driver.api"
  timeout: 30
  max_retries: 3

pagination:
  page_size: 100
  max_pages: 50

cache:
  enabled: true
  ttl: 600  # seconds
  type: "memory"  # or "redis"

mcp_tool_server:
  url: "http://localhost:8081/mcp-tools"
  timeout: 10
  enabled: true

validation:
  required_fields:
    - driver_id
    - name
```

### Environment Variables

Override configuration with environment variables:

```bash
# API Configuration
API_BASE_URL=https://external.driver.api
API_TIMEOUT=30
API_MAX_RETRIES=3

# Cache Configuration
CACHE_ENABLED=true
CACHE_TTL=600
CACHE_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MCP Configuration
MCP_TOOL_SERVER_URL=http://localhost:8081/mcp-tools
MCP_ENABLED=true

# Service Configuration
SERVICE_PORT=8080
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 🔌 API Endpoints

### Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "mcp_tool_server": {"status": "healthy"},
    "cache": {"status": "healthy"}
  }
}
```

### Get Single Driver
```bash
GET /drivers/{driver_id}?use_cache=true&use_mcp=false
```

**Response:**
```json
{
  "driver_id": "D12345",
  "name": "John Doe",
  "vehicle": "Tesla Model Y",
  "rating": 4.8
}
```

### Get Batch Drivers
```bash
POST /drivers/batch
Content-Type: application/json

{
  "driver_ids": ["D12345", "D12346", "D12347"],
  "use_cache": true,
  "use_mcp": false
}
```

**Response:**
```json
{
  "total_requested": 3,
  "successful": 3,
  "failed": 0,
  "drivers": [...],
  "errors": [],
  "validation": {
    "total": 3,
    "valid_count": 3,
    "invalid_count": 0
  }
}
```

### Get All Drivers
```bash
GET /drivers?limit=100&use_cache=true&use_mcp=false
```

**Response:**
```json
{
  "total": 100,
  "drivers": [...],
  "validation": {
    "total": 100,
    "valid_count": 98,
    "invalid_count": 2
  }
}
```

### Get Driver Summary
```bash
POST /drivers/summary?use_mcp=true

{
  "driver_ids": ["D12345", "D12346"]
}
```

**Response:**
```json
{
  "total_drivers": 2,
  "summary": {
    "average_rating": 4.7,
    "drivers_with_ratings": 2,
    "top_rated_drivers": [...]
  }
}
```

## 🛠️ MCP Tool Server

The Driver Insight Agent integrates with an external MCP Tool Server that provides modular tools:

### Available MCP Tools

1. **FetchTool**: Fetch data from external APIs
2. **ValidateTool**: Validate data fields
3. **CacheTool**: Handle cache operations
4. **SummarizeTool**: Summarize data for quick views

### Example MCP Tool Invocation

```python
# Internal usage by Driver Insight Agent
result = await mcp_invoker.fetch_data(
    endpoint="/drivers/D12345",
    method="GET"
)
```

### Running Standalone MCP Tool Server

```bash
cd mcp_tool_server
python app.py

# Access at http://localhost:8081
# API docs at http://localhost:8081/docs
```

## 📊 Error Handling

The service implements comprehensive error handling:

### Error Response Format
```json
{
  "error": "Driver API unavailable",
  "status": "retrying",
  "timestamp": "2025-10-23T09:10:00Z",
  "details": {
    "reason": "Connection timeout"
  }
}
```

### HTTP Status Codes
- `200`: Success
- `404`: Driver not found
- `422`: Validation error
- `500`: Internal server error
- `503`: Service unavailable (API down, retrying)

## 📝 Logging

Structured logging with JSON or text format:

```json
{
  "timestamp": "2025-10-23T09:10:00Z",
  "service": "driver-insight-agent",
  "logger": "services.api_client",
  "level": "INFO",
  "message": "Fetching driver data",
  "context": {
    "driver_id": "D12345"
  }
}
```

Configure log level via:
- `config.yaml`: `logging.level`
- Environment: `LOG_LEVEL=DEBUG`

## 🧪 Testing

Run tests with pytest:

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api_client.py -v
```

## 🏗️ Architecture

### Component Interaction Flow

```
┌─────────────────┐
│   FastAPI App   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ DriverInsightAgent      │
│ (Orchestrator)          │
└──┬──────┬──────┬────────┘
   │      │      │
   ▼      ▼      ▼
┌─────┐┌──────┐┌────────┐
│ API ││Cache ││Validator│
│Client││Mgr   ││         │
└─────┘└──────┘└────────┘
   │      │
   ▼      ▼
┌──────────────────┐
│  MCP Invoker     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ MCP Tool Server  │
│ (External)       │
└──────────────────┘
```

### Design Patterns

- **Orchestrator Pattern**: `DriverInsightAgent` coordinates all operations
- **Repository Pattern**: `APIClient` abstracts data fetching
- **Strategy Pattern**: Pluggable cache backends (memory/Redis)
- **Adapter Pattern**: `MCPInvoker` adapts to external tool server
- **Dependency Injection**: Components accept injected dependencies

## 🔒 Security Considerations

For production deployment:

1. **Environment Variables**: Use secrets management (AWS Secrets Manager, HashiCorp Vault)
2. **API Authentication**: Add authentication middleware to FastAPI
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **CORS**: Configure appropriate CORS settings
5. **HTTPS**: Use TLS/SSL certificates
6. **Input Validation**: All inputs are validated with Pydantic
7. **Non-root User**: Docker container runs as non-root user

## 🚀 Performance

- **Async Operations**: All I/O operations are asynchronous
- **Connection Pooling**: httpx client reuses connections
- **Caching**: Reduces API calls and improves response time
- **Batch Operations**: Concurrent fetching of multiple drivers
- **Pagination**: Efficient handling of large datasets

## 🔄 Extensibility

### Adding New MCP Tools

1. Create tool class in `mcp_tool_server/app.py`
2. Register in `TOOL_REGISTRY`
3. Add method in `mcp_invoker.py`

### Adding New Endpoints

1. Create route in `routes/` directory
2. Register router in `app.py`
3. Update API documentation

### Custom Cache Backend

1. Implement `CacheBackend` interface
2. Update `CacheManager._create_backend()`

## 📈 Monitoring

### Health Check Endpoints

- **Service Health**: `GET /health`
- **MCP Tool Server**: `GET http://localhost:8081/health`

### Metrics to Monitor

- Request latency
- Cache hit rate
- API error rate
- MCP tool invocation time

### Recommended Tools

- **Logging**: ELK Stack, Datadog, CloudWatch
- **Metrics**: Prometheus + Grafana
- **Tracing**: Jaeger, OpenTelemetry
- **APM**: New Relic, DataDog

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License.

## 📞 Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation

## 🎉 Acknowledgments

Built with:
- FastAPI
- Pydantic
- httpx
- Redis
- uvicorn

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-23
