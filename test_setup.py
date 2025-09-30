#!/usr/bin/env python3
"""Simple test to verify the project setup works."""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that we can import our modules."""
    try:
        # Add src to path
        src_path = Path(__file__).parent / "src"
        sys.path.insert(0, str(src_path))
        
        # Test core imports
        from src.models.enums import AttributionModelType, LinkingMethod
        from src.models.touchpoint import Touchpoint, CustomerJourney
        from src.models.attribution import AttributionResponse
        from src.core.attribution.linear import LinearAttributionModel
        from src.core.validation.validators import validate_required_columns
        
        print("✅ All core imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    try:
        from src.models.enums import AttributionModelType
        
        # Test enum values
        assert AttributionModelType.LINEAR == "linear"
        assert AttributionModelType.TIME_DECAY == "time_decay"
        assert AttributionModelType.FIRST_TOUCH == "first_touch"
        assert AttributionModelType.LAST_TOUCH == "last_touch"
        assert AttributionModelType.POSITION_BASED == "position_based"
        
        print("✅ Basic functionality tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

def test_file_structure():
    """Test that required files exist."""
    required_files = [
        "src/main.py",
        "src/config/settings.py",
        "src/models/__init__.py",
        "src/core/attribution/__init__.py",
        "requirements.txt",
        "README.md",
        "pytest.ini"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def main():
    """Run basic setup tests."""
    print("🧪 Testing Multi-Touch Attribution API Setup")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Import Tests", test_imports),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All setup tests passed! The project is ready.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run tests: python3 scripts/run_tests.py")
        print("3. Start the API: python3 run.py")
        return 0
    else:
        print("❌ Some setup tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
