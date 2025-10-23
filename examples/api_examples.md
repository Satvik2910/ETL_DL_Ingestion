# API Usage Examples

This document provides practical examples of using the Driver Insight Agent API.

## Prerequisites

Ensure the service is running:
```bash
# Terminal 1: Start MCP Tool Server
cd mcp_tool_server && python app.py

# Terminal 2: Start Driver Insight Agent
python app.py
```

## Using curl

### Health Check
```bash
curl -X GET http://localhost:8080/health | jq
```

### Get Single Driver
```bash
curl -X GET "http://localhost:8080/drivers/D12345?use_cache=true&use_mcp=false" | jq
```

### Get Driver with MCP
```bash
curl -X GET "http://localhost:8080/drivers/D12345?use_cache=false&use_mcp=true" | jq
```

### Batch Driver Fetch
```bash
curl -X POST http://localhost:8080/drivers/batch \
  -H "Content-Type: application/json" \
  -d '{
    "driver_ids": ["D12345", "D12346", "D12347"],
    "use_cache": true,
    "use_mcp": false
  }' | jq
```

### Get All Drivers (with limit)
```bash
curl -X GET "http://localhost:8080/drivers?limit=10&use_cache=true&use_mcp=false" | jq
```

### Get Driver Summary
```bash
curl -X POST "http://localhost:8080/drivers/summary?use_mcp=true" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_ids": ["D12345", "D12346"]
  }' | jq
```

## Using Python requests

```python
import requests

BASE_URL = "http://localhost:8080"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Get single driver
response = requests.get(
    f"{BASE_URL}/drivers/D12345",
    params={"use_cache": True, "use_mcp": False}
)
driver = response.json()
print(f"Driver: {driver['name']}")

# Batch fetch
response = requests.post(
    f"{BASE_URL}/drivers/batch",
    json={
        "driver_ids": ["D12345", "D12346", "D12347"],
        "use_cache": True,
        "use_mcp": False
    }
)
result = response.json()
print(f"Fetched {result['successful']} drivers")

# Get all drivers
response = requests.get(
    f"{BASE_URL}/drivers",
    params={"limit": 50, "use_cache": True}
)
result = response.json()
print(f"Total drivers: {result['total']}")
```

## Using httpx (async)

```python
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Health check
        response = await client.get("http://localhost:8080/health")
        print(response.json())
        
        # Get driver
        response = await client.get(
            "http://localhost:8080/drivers/D12345",
            params={"use_cache": True}
        )
        driver = response.json()
        print(f"Driver: {driver['name']}")

asyncio.run(main())
```

## Using JavaScript/TypeScript (fetch)

```javascript
// Health check
fetch('http://localhost:8080/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Get single driver
fetch('http://localhost:8080/drivers/D12345?use_cache=true&use_mcp=false')
  .then(response => response.json())
  .then(driver => console.log(`Driver: ${driver.name}`));

// Batch fetch
fetch('http://localhost:8080/drivers/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    driver_ids: ['D12345', 'D12346', 'D12347'],
    use_cache: true,
    use_mcp: false
  })
})
  .then(response => response.json())
  .then(result => console.log(`Fetched ${result.successful} drivers`));
```

## Error Handling Examples

### Handle 404 (Driver Not Found)
```bash
curl -X GET http://localhost:8080/drivers/INVALID_ID | jq
```

Response:
```json
{
  "detail": {
    "error": "Driver not found: INVALID_ID",
    "status": "not_found",
    "timestamp": "2025-10-23T09:10:00Z"
  }
}
```

### Handle 503 (Service Unavailable)
When the external API is down:
```json
{
  "detail": {
    "error": "Driver API unavailable",
    "status": "retrying",
    "timestamp": "2025-10-23T09:10:00Z",
    "details": {
      "driver_id": "D12345",
      "reason": "API request failed after 3 attempts"
    }
  }
}
```

### Handle Validation Errors
```bash
# This would return validation error if strict mode enabled
curl -X GET http://localhost:8080/drivers/D12345 | jq
```

## Testing MCP Tool Server Directly

### List Available Tools
```bash
curl -X GET http://localhost:8081/mcp-tools/list | jq
```

### Invoke FetchTool
```bash
curl -X POST http://localhost:8081/mcp-tools/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "FetchTool",
    "parameters": {
      "endpoint": "/drivers/D12345",
      "method": "GET",
      "params": {},
      "data": {}
    }
  }' | jq
```

### Invoke ValidateTool
```bash
curl -X POST http://localhost:8081/mcp-tools/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "ValidateTool",
    "parameters": {
      "data": {"driver_id": "D12345", "name": "John Doe"},
      "required_fields": ["driver_id", "name"],
      "strict": false
    }
  }' | jq
```

## Load Testing Example

Using Apache Bench:
```bash
# Test single driver endpoint
ab -n 1000 -c 10 http://localhost:8080/drivers/D12345

# Test with caching
ab -n 10000 -c 50 http://localhost:8080/drivers/D12345?use_cache=true
```

Using Python locust:
```python
from locust import HttpUser, task, between

class DriverInsightUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_driver(self):
        self.client.get("/drivers/D12345?use_cache=true")
    
    @task(2)
    def health_check(self):
        self.client.get("/health")
```

## Monitoring Examples

### Check Service Health Periodically
```bash
watch -n 5 'curl -s http://localhost:8080/health | jq ".status"'
```

### Log All Requests
```bash
tail -f logs/app.log | jq 'select(.logger == "services.api_client")'
```

## Integration Examples

### With CI/CD Pipeline
```yaml
# .github/workflows/test.yml
- name: Test API
  run: |
    curl -f http://localhost:8080/health || exit 1
    curl -f http://localhost:8080/drivers/D12345 || exit 1
```

### With Monitoring System
```python
import time
from prometheus_client import Counter, Histogram

request_counter = Counter('driver_requests_total', 'Total driver requests')
request_duration = Histogram('driver_request_duration_seconds', 'Request duration')

@request_duration.time()
def fetch_driver(driver_id):
    request_counter.inc()
    # Make request...
```
