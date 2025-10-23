# Driver Insight Agent

A modular agent service responsible for fetching and managing driver data efficiently from external APIs. The system integrates Model Context Protocol (MCP) tools for enhanced processing capabilities including data retrieval, validation, caching, and summarization.

## 🚀 Features

- **Single & Batch Operations**: Fetch individual drivers or multiple drivers in batch
- **Smart Caching**: Configurable caching layer with TTL support (in-memory or Redis)
- **Data Validation**: Comprehensive validation with detailed error reporting
- **MCP Tool Integration**: Leverages external MCP Tool Server for enhanced processing
- **Graceful Error Handling**: Robust error handling with fallback mechanisms
- **Health Monitoring**: Comprehensive health checks for all system components
- **Async/Await**: Modern async Python with FastAPI
- **Production Ready**: Docker support, structured logging, and monitoring

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │ Driver Insight   │    │  External APIs  │
│                 │────│     Agent        │────│                 │
│  /drivers/*     │    │                  │    │  Driver Data    │
│  /health        │    │  ┌─────────────┐ │    │                 │
└─────────────────┘    │  │   Services  │ │    └─────────────────┘
                       │  │             │ │
┌─────────────────┐    │  │ • APIClient │ │    ┌─────────────────┐
│  MCP Tool       │    │  │ • Validator │ │    │     Cache       │
│    Server       │────│  │ • Logger    │ │────│                 │
│                 │    │  └─────────────┘ │    │ Memory / Redis  │
│ • FetchTool     │    │                  │    │                 │
│ • ValidateTool  │    │  ┌─────────────┐ │    └─────────────────┘
│ • CacheTool     │    │  │ MCP Tools   │ │
│ • SummarizeTool │    │  │             │ │
└─────────────────┘    │  │ • Invoker   │ │
                       │  │ • Handlers  │ │
                       │  └─────────────┘ │
                       └──────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized deployment)
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
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the service**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the service**
   ```bash
   python -m driver_insight_agent.app
   ```

### Docker Deployment

1. **Using Docker Compose (Recommended)**
   ```bash
   docker-compose up -d
   ```
   This starts:
   - Driver Insight Agent (port 8080)
   - Redis cache (port 6379)
   - MCP Tool Server (port 8081)
   - Mock Driver API (port 8082)

2. **Using Docker only**
   ```bash
   docker build -t driver-insight-agent .
   docker run -p 8080:8080 driver-insight-agent
   ```

## ⚙️ Configuration

The service can be configured via environment variables or YAML file. Environment variables take precedence and use the format `DIA_SECTION__KEY`.

### Configuration File (`config.yaml`)

```yaml
api:
  base_url: "https://external.driver.api"
  pagination_size: 100
  max_retries: 3
  timeout: 30

cache:
  ttl: 600  # 10 minutes
  type: "memory"  # or "redis"
  redis_url: "redis://localhost:6379/0"
  max_size: 1000

mcp_tools:
  server_url: "http://localhost:8081/mcp-tools"
  timeout: 10
  max_retries: 2

validation:
  required_fields: ["driver_id", "name"]

logging:
  level: "INFO"
  format: "json"

server:
  host: "0.0.0.0"
  port: 8080
  debug: false
  workers: 1
```

### Environment Variables

```bash
# API Configuration
DIA_API__BASE_URL=https://external.driver.api
DIA_API__MAX_RETRIES=3

# Cache Configuration
DIA_CACHE__TYPE=redis
DIA_CACHE__REDIS_URL=redis://localhost:6379/0
DIA_CACHE__TTL=600

# MCP Tools Configuration
DIA_MCP_TOOLS__SERVER_URL=http://localhost:8081/mcp-tools

# Logging Configuration
DIA_LOGGING__LEVEL=INFO
DIA_LOGGING__FORMAT=json
```

## 🔌 API Endpoints

### Driver Operations

#### Get Single Driver
```http
GET /drivers/{driver_id}?use_cache=true&use_mcp_tools=true
```

**Response:**
```json
{
  "driver_id": "D12345",
  "data": {
    "driver_id": "D12345",
    "name": "John Doe",
    "vehicle": "Tesla Model Y",
    "rating": 4.8,
    "status": "active"
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "metadata": {
    "source": "api",
    "cached": false,
    "processed_with_mcp": true,
    "timestamp": 1698056400.123
  }
}
```

#### Get Multiple Drivers (Batch)
```http
POST /drivers/batch
Content-Type: application/json

{
  "driver_ids": ["D12345", "D12346", "D12347"],
  "use_cache": true,
  "use_mcp_tools": true
}
```

**Response:**
```json
{
  "drivers": [
    {
      "driver_id": "D12345",
      "data": { ... },
      "validation": { ... },
      "metadata": { ... }
    }
  ],
  "total_count": 3,
  "valid_count": 3,
  "cached_count": 1
}
```

#### Get Driver Summary
```http
POST /drivers/summary
Content-Type: application/json

{
  "driver_ids": ["D12345", "D12346", "D12347"]
}
```

**Response:**
```json
{
  "summary": {
    "total_drivers": 3,
    "active_drivers": 2,
    "inactive_drivers": 1,
    "average_rating": 4.6
  },
  "total_requested": 3,
  "valid_drivers": 3,
  "invalid_drivers": 0
}
```

### Health & Monitoring

#### Health Check
```http
GET /health
```

#### Simple Health Check
```http
GET /health/simple
```

#### Service Status
```http
GET /status
```

#### Cache Statistics
```http
GET /drivers/cache/stats
```

#### Clear Cache
```http
DELETE /drivers/cache
```

## 🛠️ MCP Tool Integration

The Driver Insight Agent integrates with an external MCP Tool Server that provides enhanced processing capabilities:

### Available MCP Tools

1. **FetchTool**: Enhanced data retrieval with advanced filtering
2. **ValidateTool**: Advanced validation with custom business rules
3. **CacheTool**: Distributed caching operations
4. **SummarizeTool**: Data summarization and analytics

### MCP Tool Server Setup

The repository includes an example MCP Tool Server implementation:

```bash
# Run the example MCP Tool Server
python driver_insight_agent/examples/mcp_tool_server.py
```

Or using Docker:
```bash
docker-compose up mcp-tool-server
```

### MCP Tool Server API

```http
# List available tools
GET http://localhost:8081/tools

# Invoke a tool
POST http://localhost:8081/invoke
Content-Type: application/json

{
  "tool": "FetchTool",
  "parameters": {
    "driver_id": "D12345"
  }
}
```

## 🧪 Usage Examples

### Python Client Example

```python
import httpx
import asyncio

async def fetch_driver_example():
    async with httpx.AsyncClient() as client:
        # Fetch single driver
        response = await client.get("http://localhost:8080/drivers/D12345")
        driver = response.json()
        print(f"Driver: {driver['data']['name']}")
        
        # Fetch multiple drivers
        batch_response = await client.post(
            "http://localhost:8080/drivers/batch",
            json={"driver_ids": ["D12345", "D12346"]}
        )
        batch = batch_response.json()
        print(f"Fetched {batch['total_count']} drivers")

# Run the example
asyncio.run(fetch_driver_example())
```

### cURL Examples

```bash
# Fetch single driver
curl -X GET "http://localhost:8080/drivers/D12345?use_cache=true"

# Fetch multiple drivers
curl -X POST "http://localhost:8080/drivers/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_ids": ["D12345", "D12346"],
    "use_cache": true,
    "use_mcp_tools": true
  }'

# Get driver summary
curl -X POST "http://localhost:8080/drivers/summary" \
  -H "Content-Type: application/json" \
  -d '{"driver_ids": ["D12345", "D12346", "D12347"]}'

# Health check
curl -X GET "http://localhost:8080/health"

# Clear cache
curl -X DELETE "http://localhost:8080/drivers/cache"
```

## 📊 Monitoring & Observability

### Structured Logging

The service uses structured JSON logging with contextual information:

```json
{
  "timestamp": "2025-10-23T09:10:00.123Z",
  "level": "INFO",
  "logger": "driver_insight_agent",
  "message": "Driver fetched successfully",
  "event_type": "api_request",
  "driver_id": "D12345",
  "duration_seconds": 0.245,
  "cached": false
}
```

### Health Checks

Multiple health check endpoints for different use cases:

- `/health` - Comprehensive health check (all dependencies)
- `/health/simple` - Basic health check (service only)
- `/ready` - Readiness probe (Kubernetes)
- `/live` - Liveness probe (Kubernetes)

### Metrics & Statistics

- Cache hit rates and performance
- API response times and error rates
- MCP tool execution statistics
- Validation success/failure rates

## 🔧 Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=driver_insight_agent

# Run specific test types
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black driver_insight_agent/
isort driver_insight_agent/

# Lint code
flake8 driver_insight_agent/
mypy driver_insight_agent/
```

### Development with Docker

```bash
# Build development image
docker-compose -f docker-compose.yml up --build

# Run with live reload
docker-compose up driver-insight-agent
```

## 🚀 Production Deployment

### Environment Setup

1. **Configure external dependencies**
   - Set up Redis cluster for caching
   - Deploy MCP Tool Server
   - Configure external driver API access

2. **Set production environment variables**
   ```bash
   DIA_SERVER__DEBUG=false
   DIA_SERVER__WORKERS=4
   DIA_CACHE__TYPE=redis
   DIA_CACHE__REDIS_URL=redis://redis-cluster:6379/0
   DIA_LOGGING__LEVEL=INFO
   ```

3. **Deploy with container orchestration**
   ```yaml
   # Kubernetes deployment example
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: driver-insight-agent
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: driver-insight-agent
     template:
       metadata:
         labels:
           app: driver-insight-agent
       spec:
         containers:
         - name: driver-insight-agent
           image: driver-insight-agent:1.0.0
           ports:
           - containerPort: 8080
           env:
           - name: DIA_CACHE__TYPE
             value: "redis"
           - name: DIA_CACHE__REDIS_URL
             value: "redis://redis-service:6379/0"
           livenessProbe:
             httpGet:
               path: /live
               port: 8080
           readinessProbe:
             httpGet:
               path: /ready
               port: 8080
   ```

### Performance Tuning

- **Caching**: Use Redis for distributed caching in multi-instance deployments
- **Connection Pooling**: Configure HTTP client connection limits
- **Worker Processes**: Scale workers based on CPU cores
- **Resource Limits**: Set appropriate memory and CPU limits

## 🐛 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check configuration
   python -c "from driver_insight_agent.config import load_config; load_config()"
   
   # Check dependencies
   curl http://localhost:8081/health  # MCP Tool Server
   redis-cli ping  # Redis (if using)
   ```

2. **High response times**
   ```bash
   # Check cache hit rates
   curl http://localhost:8080/drivers/cache/stats
   
   # Monitor external API performance
   curl http://localhost:8080/health
   ```

3. **Validation errors**
   ```bash
   # Check validation configuration
   curl "http://localhost:8080/drivers/D12345?use_mcp_tools=false"
   ```

### Debug Mode

Enable debug mode for development:

```bash
DIA_SERVER__DEBUG=true
DIA_LOGGING__LEVEL=DEBUG
```

### Log Analysis

```bash
# Filter logs by event type
docker logs driver-insight-agent | jq 'select(.event_type == "api_request")'

# Monitor error rates
docker logs driver-insight-agent | jq 'select(.level == "ERROR")'
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support and questions:

- Create an issue in the GitHub repository
- Check the [troubleshooting section](#-troubleshooting)
- Review the [API documentation](http://localhost:8080/docs) when running locally

## 🗺️ Roadmap

- [ ] GraphQL API support
- [ ] WebSocket real-time updates
- [ ] Advanced analytics and reporting
- [ ] Multi-tenant support
- [ ] Rate limiting and throttling
- [ ] Distributed tracing integration