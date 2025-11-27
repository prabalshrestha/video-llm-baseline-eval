"""
Test script to verify the environment setup.
"""

import sys

def test_python_version():
    """Check Python version."""
    print("Testing Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("  ✓ Python version is compatible")
        return True
    else:
        print("  ✗ Python 3.8+ required")
        return False

def test_packages():
    """Test if required packages are installed."""
    print("\nTesting required packages...")
    
    packages = {
        'pandas': 'pandas',
        'requests': 'requests',
        'pathlib': 'pathlib (built-in)',
    }
    
    all_ok = True
    for package, display_name in packages.items():
        try:
            __import__(package)
            print(f"  ✓ {display_name}")
        except ImportError:
            print(f"  ✗ {display_name} - NOT INSTALLED")
            all_ok = False
    
    return all_ok

def test_directory_structure():
    """Check if data directories exist or can be created."""
    print("\nTesting directory structure...")
    
    from pathlib import Path
    
    base_dir = Path('.')
    required_dirs = ['data', 'data/raw', 'data/filtered']
    
    all_ok = True
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        
        if dir_path.exists():
            print(f"  ✓ {dir_name}/ exists")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ {dir_name}/ created")
            except Exception as e:
                print(f"  ✗ {dir_name}/ - Cannot create: {e}")
                all_ok = False
    
    return all_ok

def test_internet_connection():
    """Test basic internet connectivity."""
    print("\nTesting internet connection...")
    
    try:
        import requests
        response = requests.head('https://www.google.com', timeout=5)
        print(f"  ✓ Internet connection available")
        return True
    except Exception as e:
        print(f"  ✗ Internet connection issue: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("ENVIRONMENT SETUP TEST")
    print("=" * 60)
    
    results = []
    
    results.append(("Python Version", test_python_version()))
    results.append(("Required Packages", test_packages()))
    results.append(("Directory Structure", test_directory_structure()))
    results.append(("Internet Connection", test_internet_connection()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✓ All tests passed! You're ready to run the scripts.")
        print("\nNext step: python download_filter_community_notes.py")
    else:
        print("✗ Some tests failed. Please address the issues above.")
        print("\nFor package installation issues:")
        print("  pip install -r requirements.txt")
        print("\nFor more help, see SETUP_GUIDE.md")
    
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

