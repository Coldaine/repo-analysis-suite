#!/usr/bin/env python3
"""Test automated fixes (use with caution!)"""
import sys
import os

# Add parent directory to path to import fixes
sys.path.insert(0, os.path.dirname(__file__))

from fixes import FIX_REGISTRY, get_fix_for_issue

def test_fix_registry():
    """Test that all fixes are callable"""
    print("Testing fix registry...")
    print(f"Found {len(FIX_REGISTRY)} registered fixes:")

    for issue_type, fix_func in FIX_REGISTRY.items():
        print(f"  - {issue_type}: {fix_func.__name__}")

    # Test getting a fix
    fix = get_fix_for_issue("container_down")
    if fix:
        print(f"\nFound fix for 'container_down': {fix.__name__}")
    else:
        print("\nERROR: Could not find fix for 'container_down'")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        print("WARNING: Running actual fixes can modify your system!")
        # Add specific test cases here if needed
    else:
        test_fix_registry()
        print("\nUse --run to execute actual fixes (dangerous!)")
