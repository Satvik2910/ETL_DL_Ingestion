#!/usr/bin/env python3
"""Example script demonstrating Driver Insight Agent usage."""

import asyncio
import json
import sys
import os

# Add parent directory to path to import the agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driver_insight_agent.app import DriverInsightAgentApp


async def run_examples():
    """Run example requests to demonstrate agent capabilities."""
    
    print("Driver Insight Agent - Examples")
    print("=" * 50)
    
    # Initialize the agent
    app = DriverInsightAgentApp()
    await app.initialize()
    
    # Load sample requests
    examples_dir = os.path.dirname(__file__)
    requests_file = os.path.join(examples_dir, "sample_requests.json")
    
    try:
        with open(requests_file, 'r') as f:
            sample_requests = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {requests_file}")
        return
    
    # Process each example request
    for i, request_data in enumerate(sample_requests, 1):
        print(f"\n{'-' * 50}")
        print(f"Example {i}: {request_data.get('request_id', 'Unknown')}")
        print(f"Report Type: {request_data.get('report_type', 'Unknown')}")
        print(f"{'-' * 50}")
        
        try:
            # Process the request
            result = await app.process_request(request_data)
            
            # Display results summary
            if result.get('success'):
                print("✓ Request processed successfully")
                
                # Show execution info
                exec_info = result.get('execution_info', {})
                print(f"  Execution time: {exec_info.get('execution_time_ms', 0):.2f}ms")
                print(f"  Tools executed: {len(exec_info.get('tools_executed', []))}")
                print(f"  Cache used: {exec_info.get('cache_used', False)}")
                
                # Show data summary
                data = result.get('data', {})
                data_sections = [k for k, v in data.items() if v and k != 'execution_summary']
                print(f"  Data sections: {', '.join(data_sections)}")
                
                # Show summary insights if available
                summary = result.get('summary', {})
                if summary and 'insights' in summary:
                    insights = summary['insights']
                    if insights:
                        print(f"  Key insights: {len(insights)} insights generated")
                        for insight in insights[:2]:  # Show first 2 insights
                            print(f"    • {insight}")
                
                # Show warnings if any
                warnings = exec_info.get('warnings', [])
                if warnings:
                    print(f"  Warnings: {len(warnings)}")
                    for warning in warnings[:2]:  # Show first 2 warnings
                        print(f"    ⚠ {warning}")
            
            else:
                print("✗ Request failed")
                print(f"  Error: {result.get('error', 'Unknown error')}")
                errors = result.get('errors', [])
                for error in errors[:3]:  # Show first 3 errors
                    print(f"    • {error}")
        
        except Exception as e:
            print(f"✗ Exception occurred: {str(e)}")
        
        # Pause between examples (except for the last one)
        if i < len(sample_requests):
            print("\nPress Enter to continue to next example...")
            input()
    
    print(f"\n{'=' * 50}")
    print("All examples completed!")
    
    # Show final agent status
    print("\nFinal Agent Status:")
    status = await app.get_status()
    exec_stats = status.get('execution_stats', {})
    print(f"  Total requests processed: {exec_stats.get('total_requests', 0)}")
    print(f"  Successful requests: {exec_stats.get('successful_requests', 0)}")
    print(f"  Failed requests: {exec_stats.get('failed_requests', 0)}")
    print(f"  Average execution time: {exec_stats.get('average_execution_time_ms', 0):.2f}ms")
    
    # Shutdown
    await app.shutdown()


async def run_single_example():
    """Run a single example request."""
    
    print("Driver Insight Agent - Single Example")
    print("=" * 50)
    
    # Initialize the agent
    app = DriverInsightAgentApp()
    await app.initialize()
    
    # Simple score analysis request
    request_data = {
        "request_id": "demo_request",
        "drivers": [
            {"driver_id": "DRV001"}
        ],
        "report_type": "score",
        "time_range": {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z"
        }
    }
    
    print("Processing demo request...")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("\nProcessing...\n")
    
    try:
        result = await app.process_request(request_data)
        
        print("Result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        await app.shutdown()


async def show_agent_capabilities():
    """Show agent capabilities and status."""
    
    print("Driver Insight Agent - Capabilities")
    print("=" * 50)
    
    # Initialize the agent
    app = DriverInsightAgentApp()
    await app.initialize()
    
    try:
        # Get capabilities
        capabilities = await app.get_capabilities()
        print("Agent Capabilities:")
        print(json.dumps(capabilities, indent=2))
        
        print("\n" + "=" * 50)
        
        # Get status
        status = await app.get_status()
        print("Agent Status:")
        print(json.dumps(status, indent=2))
        
        print("\n" + "=" * 50)
        
        # Get health check
        health = await app.health_check()
        print("Health Check:")
        print(json.dumps(health, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        await app.shutdown()


def main():
    """Main function to run examples."""
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("Usage: python run_examples.py [mode]")
        print("Modes:")
        print("  all        - Run all example requests")
        print("  single     - Run a single demo request")
        print("  capabilities - Show agent capabilities and status")
        print()
        mode = input("Enter mode (all/single/capabilities): ").strip().lower()
    
    if mode == "all":
        asyncio.run(run_examples())
    elif mode == "single":
        asyncio.run(run_single_example())
    elif mode == "capabilities":
        asyncio.run(show_agent_capabilities())
    else:
        print("Invalid mode. Use 'all', 'single', or 'capabilities'")


if __name__ == "__main__":
    main()