#!/usr/bin/env python3
"""Test runner script for the Multi-Touch Attribution API."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run tests for Multi-Touch Attribution API")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test selection
    if args.unit:
        cmd.extend(["tests/unit/", "-m", "unit"])
    elif args.integration:
        cmd.extend(["tests/integration/", "-m", "integration"])
    elif args.performance:
        cmd.extend(["tests/performance/", "-m", "performance"])
    else:
        cmd.append("tests/")
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])
    
    # Add performance options
    if args.performance:
        cmd.extend(["--benchmark-only", "--benchmark-sort=mean"])
    
    # Skip slow tests
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    # Parallel execution
    if args.parallel > 1:
        cmd.extend(["-n", str(args.parallel)])
    
    # Verbose output
    if args.verbose:
        cmd.append("-vv")
    
    # Run tests
    success = run_command(cmd, "Test Suite")
    
    # Run linting if tests pass
    if success and not args.performance:
        lint_cmd = ["python", "-m", "flake8", "src/", "tests/"]
        lint_success = run_command(lint_cmd, "Code Linting")
        
        if lint_success:
            type_cmd = ["python", "-m", "mypy", "src/"]
            type_success = run_command(type_cmd, "Type Checking")
            success = type_success
    
    # Run formatting check if all tests pass
    if success and not args.performance:
        format_cmd = ["python", "-m", "black", "--check", "src/", "tests/"]
        format_success = run_command(format_cmd, "Code Formatting Check")
        success = format_success
    
    if success:
        print(f"\n{'='*60}")
        print("🎉 All tests passed successfully!")
        print("="*60)
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print("❌ Some tests failed. Please check the output above.")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
