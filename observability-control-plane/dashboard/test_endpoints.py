#!/usr/bin/env python3
"""
Test script for dashboard API endpoints.
Requires the dashboard to be running on localhost:5555
"""

import httpx
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:5555"


def test_health():
    """Test /health endpoint"""
    print("=" * 60)
    print("Testing /health...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.status_code in [200, 503]
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_telemetry_report():
    """Test /api/telemetry-report endpoint"""
    print("=" * 60)
    print("Testing /api/telemetry-report...")
    print("=" * 60)
    telemetry_data = {
        "service_name": "test-service",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "langsmith_configured": True,
        "logfire_configured": False,
        "otel_exporter_otlp_endpoint": "NOT_SET",
        "deployment_environment": "test"
    }
    try:
        print(f"Request:\n{json.dumps(telemetry_data, indent=2)}")
        response = httpx.post(
            f"{BASE_URL}/api/telemetry-report",
            json=telemetry_data,
            timeout=5.0
        )
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_register_agent():
    """Test /api/register-agent endpoint"""
    print("=" * 60)
    print("Testing /api/register-agent...")
    print("=" * 60)
    agent_data = {
        "name": "test-agent",
        "server": "test-server"
    }
    try:
        print(f"Request:\n{json.dumps(agent_data, indent=2)}")
        response = httpx.post(
            f"{BASE_URL}/api/register-agent",
            json=agent_data,
            timeout=5.0
        )
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_get_agents():
    """Test /api/agents endpoint"""
    print("=" * 60)
    print("Testing /api/agents...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/api/agents", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
        print(f"\nTotal agents: {len(data.get('agents', []))}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_get_fixes():
    """Test /api/fixes endpoint"""
    print("=" * 60)
    print("Testing /api/fixes...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/api/fixes?limit=5", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
        print(f"\nTotal fixes: {data.get('count', 0)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_get_metrics():
    """Test /api/metrics endpoint"""
    print("=" * 60)
    print("Testing /api/metrics...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/api/metrics", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"\nResponse (first 500 chars):\n{response.text[:500]}...")
        lines = response.text.splitlines()
        print(f"\nTotal lines: {len(lines)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_api_state():
    """Test /api/state endpoint (original endpoint)"""
    print("=" * 60)
    print("Testing /api/state...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/api/state", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}\n")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def test_not_found():
    """Test 404 error handling"""
    print("=" * 60)
    print("Testing 404 error handling...")
    print("=" * 60)
    try:
        response = httpx.get(f"{BASE_URL}/api/nonexistent", timeout=5.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}\n")
        return response.status_code == 404
    except Exception as e:
        print(f"ERROR: {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("DASHBOARD API ENDPOINT TESTS")
    print(f"Target: {BASE_URL}")
    print("=" * 60 + "\n")

    # Check if dashboard is reachable
    try:
        httpx.get(BASE_URL, timeout=2.0)
    except Exception as e:
        print(f"ERROR: Cannot reach dashboard at {BASE_URL}")
        print(f"Make sure the dashboard is running: python dashboard/app.py")
        print(f"Error: {e}")
        sys.exit(1)

    tests = [
        ("Health Check", test_health),
        ("Telemetry Report", test_telemetry_report),
        ("Register Agent", test_register_agent),
        ("Get Agents", test_get_agents),
        ("Get Fixes", test_get_fixes),
        ("Get Metrics", test_get_metrics),
        ("API State", test_api_state),
        ("404 Error Handling", test_not_found),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"EXCEPTION in {test_name}: {e}\n")
            results[test_name] = False

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")

    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60 + "\n")

    # Exit with error code if any tests failed
    if passed < total:
        sys.exit(1)
    else:
        print("All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
