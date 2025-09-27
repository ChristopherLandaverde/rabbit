#!/usr/bin/env python3
"""
Update project status based on completed tasks
"""
import os
import re
from pathlib import Path

def count_completed_tests():
    """Count completed test functions"""
    test_dir = Path("tests")
    total_tests = 0
    completed_tests = 0
    
    if test_dir.exists():
        for test_file in test_dir.rglob("test_*.py"):
            with open(test_file) as f:
                content = f.read()
                # Count test functions
                test_functions = re.findall(r'def test_\w+', content)
                total_tests += len(test_functions)
                # Count implemented tests (not just pass)
                non_trivial_tests = [t for t in test_functions 
                                   if not re.search(r'def test_\w+.*:\s*pass', content)]
                completed_tests += len(non_trivial_tests)
    
    return completed_tests, total_tests

def update_status_file():
    """Update PROJECT_STATUS.md with current progress"""
    completed_tests, total_tests = count_completed_tests()
    
    # Calculate percentages for each phase
    phase_progress = {
        "Phase 1": 100,  # Foundation complete
        "Phase 2": (completed_tests / max(total_tests, 1)) * 100 if total_tests > 0 else 0,
        "Phase 3": 0,    # To be calculated based on integration tests
        "Phase 4": 0     # To be calculated based on production features
    }
    
    # Update status file
    status_content = generate_status_content(phase_progress)
    with open("STATUS_FILES/PROJECT_STATUS.md", "w") as f:
        f.write(status_content)
    
    print(f"Status updated: {completed_tests}/{total_tests} tests completed")

if __name__ == "__main__":
    update_status_file()