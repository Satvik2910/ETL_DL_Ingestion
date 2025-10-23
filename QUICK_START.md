# Quick Start Guide - Driver Insight Agent

Get up and running with the Driver Insight Agent in under 5 minutes.

## 🚀 Fastest Way to Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and enter directory
cd driver-insight-agent

# Start all services (Agent + MCP Server + Redis)
docker-compose up --build

# Access the API
open http://localhost:8080/docs
```

That's it! All services are running.

### Option 2: Local Development

```bash
# Run setup script
bash setup.sh

# Activate virtual environment
source venv/bin/activate

# Terminal 1: Start MCP Tool Server
cd mcp_tool_server
python app.py

# Terminal 2: Start Driver Insight Agent
python app.py

# Access the API
open http://localhost:8080/docs
```

## 🎯 First API Calls

### 1. Check Health
```bash
curl http://localhost:8080/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "mcp_tool_server": {"status": "healthy"},
    "cache": {"status": "healthy"}
  }
}
```

### 2. Get Single Driver
```bash
curl "http://localhost:8080/drivers/D12345?use_cache=true" | jq
```

Expected response:
```json
{
  "driver_id": "D12345",
  "name": "Driver D12345",
  "vehicle": "Tesla Model Y",
  "rating": 4.8
}
```

### 3. Get Multiple Drivers
```bash
curl -X POST http://localhost:8080/drivers/batch \
  -H "Content-Type: application/json" \
  -d '{
    "driver_ids": ["D12345", "D12346", "D12347"],
    "use_cache": true,
    "use_mcp": false
  }' | jq
```

### 4. Interactive API Documentation
Visit: http://localhost:8080/docs

- Try all endpoints
- See request/response schemas
- Execute requests directly from browser

## 📁 Project Structure (Simplified)

```
driver-insight-agent/
├── app.py                    # ← Start here
├── config.yaml               # ← Configuration
├── requirements.txt          # ← Dependencies
│
├── services/                 # Core business logic
│   ├── driver_insight_agent.py
│   ├── api_client.py
│   └── validator.py
│
├── cache/                    # Caching layer
├── mcp_tools/                # MCP integration
├── routes/                   # API endpoints
├── utils/                    # Utilities
│
└── mcp_tool_server/          # Example MCP server
    └── app.py
```

## ⚙️ Basic Configuration

### config.yaml
```yaml
api:
  base_url: "https://external.driver.api"
  max_retries: 3

cache:
  enabled: true
  ttl: 600
  type: "memory"  # or "redis"

mcp_tool_server:
  url: "http://localhost:8081/mcp-tools"
  enabled: true
```

### Environment Variables (.env)
```bash
API_BASE_URL=https://external.driver.api
CACHE_TYPE=memory
LOG_LEVEL=INFO
```

## 🧪 Run Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port
SERVICE_PORT=8888 python app.py
```

### MCP Server Not Running
```bash
# Check if MCP server is running
curl http://localhost:8081/health

# If not, start it
cd mcp_tool_server && python app.py
```

### Cache Issues
```bash
# Clear cache (if using Redis)
redis-cli FLUSHALL

# Or restart with memory cache
CACHE_TYPE=memory python app.py
```

### Import Errors
```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## 📚 Next Steps

1. **Read the Full README**: See [README.md](README.md)
2. **Explore API Examples**: See [examples/api_examples.md](examples/api_examples.md)
3. **Run Example Code**: `python examples/usage_example.py`
4. **Review Architecture**: See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
5. **Deploy with Docker**: `docker-compose up`

## 🎓 Common Use Cases

### Use Case 1: Fetch Single Driver with Caching
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8080/drivers/D12345",
        params={"use_cache": True}
    )
    driver = response.json()
    print(f"Driver: {driver['name']}")
```

### Use Case 2: Batch Fetch Multiple Drivers
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8080/drivers/batch",
        json={
            "driver_ids": ["D1", "D2", "D3"],
            "use_cache": True
        }
    )
    result = response.json()
    print(f"Fetched {result['successful']} drivers")
```

### Use Case 3: Get All Drivers (Paginated)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8080/drivers",
        params={"limit": 100, "use_cache": True}
    )
    result = response.json()
    print(f"Total: {result['total']}")
```

## 🔧 Development Commands

```bash
# Run in development mode with auto-reload
make dev

# Run tests
make test

# Format code
make format

# Check code quality
make lint

# Clean up generated files
make clean
```

## 📊 Monitoring

### View Logs
```bash
# Follow logs in JSON format
tail -f logs/app.log | jq

# Filter by level
tail -f logs/app.log | jq 'select(.level == "ERROR")'

# Docker logs
docker-compose logs -f driver-insight-agent
```

### Check Service Status
```bash
# Health check
curl http://localhost:8080/health

# Service info
curl http://localhost:8080/

# MCP server status
curl http://localhost:8081/health
```

## 🎉 Success!

You now have:
- ✅ Driver Insight Agent running
- ✅ MCP Tool Server running
- ✅ Cache enabled
- ✅ API accessible at http://localhost:8080
- ✅ Interactive docs at http://localhost:8080/docs

## 💬 Need Help?

- Check [README.md](README.md) for detailed documentation
- Review [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for architecture
- See [examples/](examples/) for code samples
- Create an issue on GitHub

---

**Happy Coding! 🚀**
