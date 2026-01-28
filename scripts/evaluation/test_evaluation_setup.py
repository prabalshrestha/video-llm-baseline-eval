#!/usr/bin/env python3
"""
Test script to verify evaluation setup.
Checks if all dependencies are installed and API keys are configured.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test if all required packages are installed."""
    print("\n" + "=" * 70)
    print("TESTING PACKAGE IMPORTS")
    print("=" * 70)

    packages = [
        ("google.generativeai", "Gemini API"),
        ("openai", "OpenAI API"),
        ("rouge_score", "ROUGE metrics"),
        ("nltk", "NLTK"),
        ("sentence_transformers", "Sentence Transformers"),
        ("tqdm", "Progress bars"),
    ]

    all_installed = True
    for package, name in packages:
        try:
            __import__(package)
            print(f"✓ {name:25} installed")
        except ImportError:
            print(f"✗ {name:25} NOT installed")
            all_installed = False

    return all_installed


def test_api_keys():
    """Test if API keys are configured."""
    print("\n" + "=" * 70)
    print("TESTING API KEYS")
    print("=" * 70)

    import os
    from dotenv import load_dotenv

    load_dotenv()

    keys = [
        ("GEMINI_API_KEY", "Gemini 1.5 Pro"),
        ("OPENAI_API_KEY", "GPT-4o"),
        ("TWITTER_BEARER_TOKEN", "Twitter API (Optional)"),
    ]

    available_keys = 0
    for key_name, description in keys:
        value = os.getenv(key_name)
        if value:
            print(f"✓ {description:30} configured")
            available_keys += 1
        else:
            print(f"✗ {description:30} NOT configured")

    if available_keys == 0:
        print("\n⚠ No API keys configured!")
        print("  Create a .env file with at least one of:")
        print("    GEMINI_API_KEY=your_key")
        print("    OPENAI_API_KEY=your_key")
        return False

    return available_keys > 0


def test_dataset():
    """Test if dataset exists."""
    print("\n" + "=" * 70)
    print("TESTING DATASET")
    print("=" * 70)

    dataset_path = Path("data/evaluation/latest/dataset.json")
    if dataset_path.exists():
        import json

        with open(dataset_path) as f:
            data = json.load(f)
        total_samples = data.get("dataset_info", {}).get("total_samples", 0)
        print(f"✓ Dataset found: {total_samples} samples (latest)")
        return True
    else:
        print("✗ Latest dataset not found")
        print("  Run: python main.py dataset")
        return False


def test_videos():
    """Test if videos exist."""
    print("\n" + "=" * 70)
    print("TESTING VIDEOS")
    print("=" * 70)

    videos_dir = Path("data/videos")
    if videos_dir.exists():
        videos = list(videos_dir.glob("*.mp4"))
        print(f"✓ Found {len(videos)} video files")
        return len(videos) > 0
    else:
        print("✗ Videos directory not found")
        return False


def test_services():
    """Test if services can be initialized."""
    print("\n" + "=" * 70)
    print("TESTING LLM SERVICES")
    print("=" * 70)

    try:
        from scripts.evaluation.llms import GeminiService, GPT4oService

        gemini = GeminiService()
        gpt4o = GPT4oService()

        if gemini.is_available():
            print("✓ Gemini service available")
        else:
            print("✗ Gemini service not available (no API key)")

        if gpt4o.is_available():
            print("✓ GPT-4o service available")
        else:
            print("✗ GPT-4o service not available (no API key)")

        return gemini.is_available() or gpt4o.is_available()

    except Exception as e:
        print(f"✗ Error initializing services: {e}")
        return False


def test_prompt_generation():
    """Test if prompts can be generated."""
    print("\n" + "=" * 70)
    print("TESTING PROMPT GENERATION")
    print("=" * 70)

    try:
        from scripts.evaluation.prompts import create_prompt

        prompt = create_prompt(
            tweet_text="Test tweet",
            author_name="Test Author",
            author_username="testuser",
        )

        if prompt and len(prompt) > 100:
            print("✓ Prompt generation works")
            print(f"  Generated {len(prompt)} character prompt")
            return True
        else:
            print("✗ Prompt generation failed")
            return False

    except Exception as e:
        print(f"✗ Error generating prompt: {e}")
        return False


def test_metrics():
    """Test if metrics can be calculated."""
    print("\n" + "=" * 70)
    print("TESTING METRICS")
    print("=" * 70)

    try:
        from scripts.evaluation.metrics import EvaluationMetrics

        metrics = EvaluationMetrics()

        # Test ROUGE
        text1 = "This is a test sentence."
        text2 = "This is another test sentence."
        rouge = metrics.calculate_rouge_scores(text1, text2)

        if rouge and "rouge1" in rouge:
            print(f"✓ ROUGE calculation works (score: {rouge['rouge1']:.3f})")
        else:
            print("✗ ROUGE calculation failed")
            return False

        # Test semantic similarity
        similarity = metrics.calculate_semantic_similarity(text1, text2)
        if similarity is not None:
            print(f"✓ Semantic similarity works (score: {similarity:.3f})")
        else:
            print("✗ Semantic similarity failed")
            return False

        return True

    except Exception as e:
        print(f"✗ Error testing metrics: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("VIDEO LLM EVALUATION SETUP TEST")
    print("=" * 70)

    tests = [
        ("Package Imports", test_imports),
        ("API Keys", test_api_keys),
        ("Dataset", test_dataset),
        ("Videos", test_videos),
        ("Prompt Generation", test_prompt_generation),
        ("LLM Services", test_services),
        ("Metrics", test_metrics),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Ready to run evaluation.")
        print("\nNext steps:")
        print("  python main.py evaluate --models gemini --limit 2")
        return 0
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")

        # Provide specific guidance
        if not any(r for n, r in results if n == "Package Imports"):
            print("\nInstall missing packages:")
            print("  pip install -r requirements.txt")

        if not any(r for n, r in results if n == "API Keys"):
            print("\nConfigure API keys:")
            print("  Create .env file with your API keys")

        if not any(r for n, r in results if n == "Dataset"):
            print("\nCreate dataset:")
            print("  python main.py dataset")

        return 1


if __name__ == "__main__":
    sys.exit(main())
