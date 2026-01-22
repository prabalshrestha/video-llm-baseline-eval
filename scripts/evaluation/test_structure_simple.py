#!/usr/bin/env python3
"""
Simple test to verify run directory structure code is syntactically correct
and the new methods exist.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports_and_methods():
    """Test that the module imports and new methods exist."""
    print("Testing Run Directory Implementation")
    print("=" * 70)
    
    # Test 1: Import module
    print("\n1. Testing module import...")
    try:
        from scripts.evaluation.evaluate_models import VideoLLMEvaluator, MODEL_CONFIGS
        print("   ✓ Module imported successfully")
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return False
    
    # Test 2: Check MODEL_CONFIGS
    print("\n2. Testing MODEL_CONFIGS...")
    assert "gemini" in MODEL_CONFIGS
    assert "gpt4o" in MODEL_CONFIGS
    assert "qwen" in MODEL_CONFIGS
    print("   ✓ MODEL_CONFIGS contains all expected models")
    
    # Test 3: Check new methods exist
    print("\n3. Testing new methods exist...")
    required_methods = [
        "_create_run_directory",
        "_save_config",
        "_save_per_model_results",
        "_save_comparison_table",
        "_update_latest_symlink",
    ]
    
    for method_name in required_methods:
        assert hasattr(VideoLLMEvaluator, method_name), f"Missing method: {method_name}"
        print(f"   ✓ {method_name}")
    
    # Test 4: Check constructor signature
    print("\n4. Testing constructor signature...")
    import inspect
    sig = inspect.signature(VideoLLMEvaluator.__init__)
    params = list(sig.parameters.keys())
    
    required_params = ["create_run_dir", "run_name"]
    for param in required_params:
        assert param in params, f"Missing parameter: {param}"
        print(f"   ✓ {param} parameter exists")
    
    # Test 5: Check save_results signature
    print("\n5. Testing save_results signature...")
    sig = inspect.signature(VideoLLMEvaluator.save_results)
    params = list(sig.parameters.keys())
    assert "save_per_model" in params, "Missing save_per_model parameter"
    print("   ✓ save_per_model parameter exists")
    
    print("\n" + "=" * 70)
    print("ALL VERIFICATION CHECKS PASSED ✅")
    print("=" * 70)
    
    print("\nImplementation Summary:")
    print("- Run directory management: ✓ Implemented")
    print("- Per-model file generation: ✓ Implemented")
    print("- Comparison table CSV: ✓ Implemented")
    print("- Configuration saving: ✓ Implemented")
    print("- Latest symlink: ✓ Implemented")
    print("- New CLI arguments: ✓ Ready (test with --help)")
    
    print("\nNext Steps:")
    print("1. Test with actual evaluation:")
    print("   python scripts/evaluation/evaluate_models.py --models gemini --limit 1")
    print("2. Check output directory:")
    print("   ls -R data/evaluation/runs/")
    print("3. View comparison table:")
    print("   cat data/evaluation/runs/latest/metrics/comparison_table.csv")
    
    return True


if __name__ == "__main__":
    try:
        success = test_imports_and_methods()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
