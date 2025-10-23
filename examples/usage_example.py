"""
Example usage of Driver Insight Agent programmatically.
Demonstrates how to use the agent in your own Python code.
"""

import asyncio

from cache.cache_manager import CacheManager
from mcp_tools.mcp_invoker import MCPInvoker
from services.api_client import APIClient
from services.driver_insight_agent import DriverInsightAgent
from services.validator import Validator


async def main():
    """Main example function."""
    
    print("🚀 Driver Insight Agent - Usage Example\n")
    
    # Initialize components
    api_client = APIClient(base_url="https://external.driver.api")
    validator = Validator(required_fields=["driver_id", "name"])
    cache_manager = CacheManager()
    mcp_invoker = MCPInvoker(server_url="http://localhost:8081/mcp-tools")
    
    # Create agent
    agent = DriverInsightAgent(
        api_client=api_client,
        validator=validator,
        cache_manager=cache_manager,
        mcp_invoker=mcp_invoker,
    )
    
    try:
        # Example 1: Health Check
        print("1️⃣  Performing health check...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Components: {list(health['components'].keys())}\n")
        
        # Example 2: Fetch Single Driver
        print("2️⃣  Fetching single driver (D12345)...")
        try:
            driver = await agent.get_driver(
                driver_id="D12345",
                use_cache=True,
                use_mcp=False,
            )
            print(f"   Driver: {driver['name']}")
            print(f"   Vehicle: {driver.get('vehicle', 'N/A')}")
            print(f"   Rating: {driver.get('rating', 'N/A')}\n")
        except Exception as e:
            print(f"   Error: {str(e)}\n")
        
        # Example 3: Batch Fetch
        print("3️⃣  Fetching batch drivers...")
        driver_ids = ["D12345", "D12346", "D12347"]
        try:
            result = await agent.get_drivers_batch(
                driver_ids=driver_ids,
                use_cache=True,
                use_mcp=False,
            )
            print(f"   Total requested: {result['total_requested']}")
            print(f"   Successful: {result['successful']}")
            print(f"   Failed: {result['failed']}")
            print(f"   Valid drivers: {result['validation']['valid_count']}\n")
        except Exception as e:
            print(f"   Error: {str(e)}\n")
        
        # Example 4: Fetch All Drivers (limited)
        print("4️⃣  Fetching all drivers (limit 10)...")
        try:
            result = await agent.get_all_drivers(
                limit=10,
                use_cache=False,
                use_mcp=False,
            )
            print(f"   Total fetched: {result['total']}")
            print(f"   Valid: {result['validation']['valid_count']}")
            print(f"   Invalid: {result['validation']['invalid_count']}\n")
        except Exception as e:
            print(f"   Error: {str(e)}\n")
        
        # Example 5: Generate Summary
        print("5️⃣  Generating driver summary...")
        try:
            # First get some drivers
            result = await agent.get_all_drivers(limit=5, use_cache=True)
            drivers = result['drivers']
            
            # Generate summary
            summary = await agent.summarize_drivers(
                drivers=drivers,
                use_mcp=False,
            )
            print(f"   Total drivers: {summary['total_drivers']}")
            if 'average_rating' in summary and summary['average_rating']:
                print(f"   Average rating: {summary['average_rating']:.2f}")
            print()
        except Exception as e:
            print(f"   Error: {str(e)}\n")
        
        # Example 6: Cache Operations
        print("6️⃣  Testing cache operations...")
        cache_key = cache_manager.generate_key("test", "example")
        
        # Set cache
        await cache_manager.set(cache_key, {"test": "data"}, ttl=300)
        print(f"   ✅ Set cache: {cache_key}")
        
        # Get cache
        cached_value = await cache_manager.get(cache_key)
        print(f"   ✅ Get cache: {cached_value}")
        
        # Check exists
        exists = await cache_manager.exists(cache_key)
        print(f"   ✅ Cache exists: {exists}")
        
        # Delete cache
        await cache_manager.delete(cache_key)
        print(f"   ✅ Deleted cache\n")
        
        # Example 7: Validation
        print("7️⃣  Testing validation...")
        valid_driver = {"driver_id": "D001", "name": "John Doe", "rating": 4.5}
        invalid_driver = {"driver_id": "D002"}  # Missing name
        
        is_valid = validator.validate_driver(valid_driver)
        print(f"   Valid driver: {is_valid}")
        
        is_valid = validator.validate_driver(invalid_driver)
        print(f"   Invalid driver: {is_valid}")
        
        # Batch validation
        drivers = [valid_driver, invalid_driver]
        result = validator.validate_drivers(drivers)
        print(f"   Batch validation - Valid: {result['valid_count']}, Invalid: {result['invalid_count']}\n")
        
        print("✅ All examples completed successfully!")
        
    finally:
        # Always close the agent
        await agent.close()
        print("\n🔒 Agent closed")


if __name__ == "__main__":
    asyncio.run(main())
