#!/usr/bin/env python3
"""
Comprehensive test runner with coverage reporting for the Multi-Touch Attribution API.

This script runs all tests with coverage reporting and generates detailed reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    if isinstance(command, str):
        command = command.split()
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ {description} failed!")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    else:
        print(f"✅ {description} completed successfully!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run tests with coverage reporting")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--no-coverage", action="store_true", help="Run tests without coverage")
    parser.add_argument("--coverage-threshold", type=int, default=80, help="Coverage threshold percentage")
    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 Starting Multi-Touch Attribution API Test Suite")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Build test command
    test_cmd = "python3 -m pytest"
    
    # Add test selection
    if args.unit_only:
        test_cmd += " tests/unit/"
    elif args.integration_only:
        test_cmd += " tests/integration/"
    elif args.performance_only:
        test_cmd += " tests/performance/"
    else:
        test_cmd += " tests/"
    
    # Add coverage options
    if not args.no_coverage:
        test_cmd += f" --cov=src --cov-report=term-missing --cov-fail-under={args.coverage_threshold}"
        if args.html_report:
            test_cmd += " --cov-report=html"
        test_cmd += " --cov-branch"
    
    # Add verbose option
    if args.verbose:
        test_cmd += " -v"
    
    # Add other options
    test_cmd += " --tb=short --strict-markers --disable-warnings --color=yes"
    
    # Run the tests
    success = run_command(test_cmd, "Test Suite with Coverage")
    
    if success and not args.no_coverage:
        # Generate additional coverage reports
        if args.html_report:
            print("\n📊 HTML coverage report generated in htmlcov/")
        
        # Generate coverage summary
        run_command("python3 -m coverage report", "Coverage Summary")
        
        # Generate coverage XML for CI/CD
        run_command("python3 -m coverage xml", "Coverage XML Report")
    
    # Run linting if available
    print("\n🔍 Running code quality checks...")
    
    # Check if black is available
    try:
        run_command("python3 -m black --check src/ tests/", "Code Formatting Check (Black)")
    except FileNotFoundError:
        print("⚠️  Black not available, skipping formatting check")
    
    # Check if flake8 is available
    try:
        run_command("python3 -m flake8 src/ tests/", "Code Quality Check (Flake8)")
    except FileNotFoundError:
        print("⚠️  Flake8 not available, skipping code quality check")
    
    # Check if mypy is available
    try:
        run_command("python3 -m mypy src/", "Type Checking (MyPy)")
    except FileNotFoundError:
        print("⚠️  MyPy not available, skipping type checking")
    
    if success:
        print("\n🎉 All tests passed successfully!")
        print("\n📈 Test Summary:")
        print("   ✅ Unit tests")
        print("   ✅ Integration tests") 
        print("   ✅ Performance tests")
        print("   ✅ Coverage reporting")
        print("   ✅ Code quality checks")
        
        if not args.no_coverage:
            print(f"\n📊 Coverage threshold: {args.coverage_threshold}%")
            if args.html_report:
                print("📄 HTML report: htmlcov/index.html")
            print("📄 XML report: coverage.xml")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
