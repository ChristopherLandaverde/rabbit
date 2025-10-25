#!/usr/bin/env python3
"""
Simple test to validate our test infrastructure without external dependencies.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestBasicFunctionality(unittest.TestCase):
    """Basic tests that don't require external dependencies."""
    
    def test_python_version(self):
        """Test that we have a compatible Python version."""
        self.assertGreaterEqual(sys.version_info, (3, 8), "Python 3.8+ required")
        print(f"✅ Python version: {sys.version}")
    
    def test_project_structure(self):
        """Test that our project structure is correct."""
        # Check main directories exist
        self.assertTrue(os.path.exists('src'), "src directory should exist")
        self.assertTrue(os.path.exists('tests'), "tests directory should exist")
        self.assertTrue(os.path.exists('docs'), "docs directory should exist")
        print("✅ Project structure is correct")
    
    def test_test_files_exist(self):
        """Test that our test files exist."""
        test_files = [
            'tests/unit/test_attribution_models.py',
            'tests/unit/test_data_validation.py',
            'tests/unit/test_csv_processing.py',
            'tests/integration/test_api_endpoints.py',
            'tests/performance/test_benchmarks.py',
            'tests/fixtures/data.py',
            'tests/fixtures/app.py'
        ]
        
        for test_file in test_files:
            self.assertTrue(os.path.exists(test_file), f"Test file {test_file} should exist")
        
        print("✅ All test files exist")
    
    def test_configuration_files(self):
        """Test that configuration files exist."""
        config_files = [
            'pytest.ini',
            '.coveragerc',
            'requirements.txt',
            'requirements-test.txt'
        ]
        
        for config_file in config_files:
            self.assertTrue(os.path.exists(config_file), f"Config file {config_file} should exist")
        
        print("✅ All configuration files exist")
    
    def test_src_structure(self):
        """Test that src directory structure is correct."""
        src_dirs = [
            'src/core',
            'src/core/attribution',
            'src/models',
            'src/api',
            'src/config',
            'src/utils'
        ]
        
        for src_dir in src_dirs:
            self.assertTrue(os.path.exists(src_dir), f"Source directory {src_dir} should exist")
        
        print("✅ Source directory structure is correct")
    
    def test_test_runner_script(self):
        """Test that our test runner script exists and is executable."""
        script_path = 'scripts/run_tests_with_coverage.py'
        self.assertTrue(os.path.exists(script_path), f"Test runner script {script_path} should exist")
        
        # Check if it's executable
        if os.access(script_path, os.X_OK):
            print("✅ Test runner script is executable")
        else:
            print("⚠️  Test runner script exists but may not be executable")
    
    def test_documentation_structure(self):
        """Test that documentation structure is correct."""
        doc_files = [
            'docs/STATUS_FILES/PROJECT_STATUS.MD',
            'docs/STATUS_FILES/PHASE_2_COMPLETION_SUMMARY.md',
            'README.md'
        ]
        
        for doc_file in doc_files:
            self.assertTrue(os.path.exists(doc_file), f"Documentation file {doc_file} should exist")
        
        print("✅ Documentation structure is correct")

class TestDataGeneration(unittest.TestCase):
    """Test data generation without external dependencies."""
    
    def test_simple_data_generation(self):
        """Test that we can generate simple test data."""
        # Generate simple test data
        data = []
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for i in range(10):
            data.append({
                'timestamp': base_time + timedelta(hours=i),
                'channel': f'channel_{i % 3}',
                'event_type': 'click' if i % 2 == 0 else 'conversion',
                'customer_id': f'cust_{i % 3}',
                'conversion_value': 100.0 if i % 2 == 1 else None
            })
        
        self.assertEqual(len(data), 10, "Should generate 10 data points")
        self.assertEqual(len([d for d in data if d['event_type'] == 'conversion']), 5, "Should have 5 conversions")
        print("✅ Simple data generation works")
    
    def test_attribution_logic_simulation(self):
        """Test basic attribution logic without external dependencies."""
        # Simulate linear attribution logic
        touchpoints = [
            {'channel': 'email', 'timestamp': datetime(2024, 1, 1, 10, 0, 0)},
            {'channel': 'social', 'timestamp': datetime(2024, 1, 1, 11, 0, 0)},
            {'channel': 'paid_search', 'timestamp': datetime(2024, 1, 1, 12, 0, 0)}
        ]
        
        # Linear attribution: equal credit to all touchpoints
        total_touchpoints = len(touchpoints)
        expected_credit = 1.0 / total_touchpoints
        
        attribution = {}
        for tp in touchpoints:
            channel = tp['channel']
            attribution[channel] = attribution.get(channel, 0) + expected_credit
        
        # Verify attribution logic
        self.assertAlmostEqual(sum(attribution.values()), 1.0, places=10, msg="Total attribution should equal 1.0")
        self.assertEqual(len(attribution), 3, "Should have 3 channels")
        
        for channel, credit in attribution.items():
            self.assertAlmostEqual(credit, expected_credit, places=10, msg=f"Channel {channel} should get equal credit")
        
        print("✅ Attribution logic simulation works")

def run_tests():
    """Run all tests."""
    print("🧪 Running Basic Test Infrastructure Validation")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestBasicFunctionality))
    suite.addTests(loader.loadTestsFromTestCase(TestDataGeneration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All basic tests passed! Test infrastructure is ready.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
